"""Behavioral role scores (Entry, Lurker, Suporte, Anchor, Flex) from play, never from the agent alone. Owner: Stream B.

Every raw signal is turned into a percentile among players with enough rounds (`REFERENCE_ROUNDS`), and a role score is a
weighted mean of its signal percentiles (0..1). Confidence grows with the player's sample size and with the margin
between the role and the runner-up. IGL is intentionally NOT produced: the data cannot show who calls the game.
Positions come from `kills.player_locations`, so spatial signals are snapshots at kill moments only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.store import Store
from ..metrics import kill_events
from ..schemas.common import RoleName, RoleScore, Signal

REFERENCE_ROUNDS = 100  # players below this still get scores, with low confidence
FULL_CONFIDENCE_ROUNDS = 300
SITE_RADIUS = 1500  # game units around a bombsite centre that count as "holding the site"
EARLY_MS, LATE_MS = 30_000, 60_000
ROLES: tuple[RoleName, ...] = ("entry", "lurker", "support", "anchor", "flex")

# role -> [(signal column, weight, invert)]
WEIGHTS: dict[str, list[tuple[str, float, bool]]] = {
    "entry": [("first_duel_share", 0.6, False), ("early_kill_share", 0.4, False)],
    "lurker": [("isolation", 0.5, False), ("late_kill_share", 0.5, False)],
    "support": [("assists_per_round", 0.5, False), ("casts_per_round", 0.5, False)],
    "anchor": [("defense_site_presence", 0.7, False), ("first_duel_share", 0.3, True)],
}


def _locations(store: Store) -> pd.DataFrame:
    """One row per (kill event, alive player) with position, team colour and the round side."""
    k = store.kills[["match_id", "round_num", "kill_idx", "player_locations"]].explode("player_locations")
    k = k[k.player_locations.notna()]
    loc = pd.DataFrame(list(k.player_locations), index=k.index)
    loc = pd.concat([k[["match_id", "round_num", "kill_idx"]], loc], axis=1)
    loc = loc[(loc.x > -10_000) & loc.x.notna()]
    col = store.match_players[["match_id", "puuid", "team_color"]]
    side = store.round_player_stats[["match_id", "round_num", "puuid", "side"]]
    return loc.merge(col, on=["match_id", "puuid"]).merge(side, on=["match_id", "round_num", "puuid"])


def _isolation(loc: pd.DataFrame) -> pd.Series:
    """Mean distance to living teammates at kill moments, relative to the team's average at that moment."""
    key = ["match_id", "kill_idx", "team_color"]
    a = loc[key + ["puuid", "x", "y"]]
    p = a.merge(a, on=key, suffixes=("", "_o"))
    p = p[p.puuid != p.puuid_o]
    p["d"] = np.hypot(p.x - p.x_o, p.y - p.y_o)
    per = p.groupby(key + ["puuid"]).d.agg(["mean", "size"]).reset_index()
    per = per[per["size"] >= 2]  # at least 3 teammates alive in the snapshot
    per["rel"] = per["mean"] / per.groupby(key)["mean"].transform("mean")
    return per.groupby("puuid").rel.mean().rename("isolation")


def _site_presence(store: Store, loc: pd.DataFrame) -> pd.Series:
    r = store.rounds.merge(store.matches[["match_id", "map_name"]], on="match_id")
    r = r[r.planter.notna()]
    centres = r.groupby(["map_name", "plant_site"])[["plant_x", "plant_y"]].mean().reset_index()
    d = loc[loc.side == "defense"].merge(store.matches[["match_id", "map_name"]], on="match_id")
    d = d.merge(centres, on="map_name")
    d["near"] = np.hypot(d.x - d.plant_x, d.y - d.plant_y) <= SITE_RADIUS
    ev = d.groupby(["match_id", "kill_idx", "puuid"]).near.any()
    return ev.groupby("puuid").mean().rename("defense_site_presence")


def role_signals(store: Store) -> pd.DataFrame:
    """Raw behavioral signals per player (index puuid) plus the sample sizes behind them."""
    mp = store.match_players
    g = mp.groupby("puuid").agg(rounds=("rounds_played", "sum"), matches=("match_id", "nunique"),
                                assists=("assists", "sum"),
                                casts=("grenade_casts", "sum"))
    g["casts"] += mp.groupby("puuid").ability1_casts.sum() + mp.groupby("puuid").ability2_casts.sum()
    g["assists_per_round"] = g.assists / g.rounds.clip(lower=1)
    g["casts_per_round"] = g.casts / g.rounds.clip(lower=1)

    ke = kill_events(store)
    own = ke[ke.killer_color.notna() & ~ke.teamkill]
    fk = own[own.is_first].groupby("killer").size()
    fd = ke[ke.is_first].groupby("victim").size()
    g["first_duels"] = fk.reindex(g.index).fillna(0) + fd.reindex(g.index).fillna(0)
    g["first_duel_share"] = g.first_duels / g.rounds.clip(lower=1)
    kills = own.groupby("killer").size().reindex(g.index).fillna(0)
    g["kills"] = kills
    early = own[own.time_in_round_ms <= EARLY_MS].groupby("killer").size().reindex(g.index).fillna(0)
    late = own[own.time_in_round_ms >= LATE_MS].groupby("killer").size().reindex(g.index).fillna(0)
    g["early_kill_share"] = early / kills.where(kills > 0)
    g["late_kill_share"] = late / kills.where(kills > 0)

    loc = _locations(store)
    g = g.join(_isolation(loc)).join(_site_presence(store, loc))
    counts = mp.groupby(["puuid", "agent_id"]).size().unstack(fill_value=0)
    p = counts.div(counts.sum(axis=1), axis=0)
    ent = -(p * np.log(p.where(p > 0))).sum(axis=1)
    g["agent_variety"] = (ent / np.log(max(counts.shape[1], 2))).reindex(g.index)
    return g


@dataclass
class RoleModel:
    signals: pd.DataFrame  # raw signals per player
    scores: pd.DataFrame  # role scores per player, 0..1 (columns = ROLES)
    confidence: pd.DataFrame

    def roles_for(self, puuid: str, top: int = 2) -> list[RoleScore]:
        if puuid not in self.scores.index:
            return []
        s, conf, raw = self.scores.loc[puuid], self.confidence.loc[puuid], self.signals.loc[puuid]
        out = []
        for role in s.sort_values(ascending=False).index[:top]:
            names = [c for c, _, _ in WEIGHTS.get(role, [])] or ["agent_variety"]
            sigs = [Signal(name=n, value=round(float(raw[n]), 4), sample_size=int(raw.rounds))
                    for n in names if n in raw and raw[n] == raw[n]]
            out.append(RoleScore(role=role, score=round(float(s[role]), 3), confidence=round(float(conf[role]), 3),
                                 inferred=False, signals=sigs))
        return out


def build_role_model(store: Store) -> RoleModel:
    sig = role_signals(store)
    ref = sig[sig.rounds >= REFERENCE_ROUNDS]

    def pct(col: str) -> pd.Series:
        vals = np.sort(ref[col].dropna().to_numpy())
        if len(vals) == 0:
            return pd.Series(0.5, index=sig.index)
        pos = np.searchsorted(vals, sig[col].fillna(vals.mean()).to_numpy(), side="right") / len(vals)
        return pd.Series(pos, index=sig.index)

    scores = pd.DataFrame(index=sig.index)
    for role, parts in WEIGHTS.items():
        scores[role] = sum(w * ((1 - pct(c)) if inv else pct(c)) for c, w, inv in parts)
    spread = scores.max(axis=1) - scores.mean(axis=1)
    scores["flex"] = 0.6 * pct("agent_variety") + 0.4 * (1 - spread)
    scores = scores[list(ROLES)]

    sample = (sig.rounds / FULL_CONFIDENCE_ROUNDS).clip(upper=1)
    srt = np.sort(scores.to_numpy(), axis=1)
    margin = pd.Series(srt[:, -1] - srt[:, -2], index=scores.index)
    conf = pd.DataFrame({r: sample * (0.4 + 0.6 * ((scores[r] - scores.drop(columns=r).max(axis=1)).clip(lower=0) * 4).clip(upper=1))
                         for r in ROLES})
    del margin
    return RoleModel(sig, scores, conf)


_CACHE: dict[int, RoleModel] = {}


def role_model(store: Store) -> RoleModel:
    """Role model for the FULL store (percentiles are always relative to the whole dataset), cached per store."""
    key = id(store)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = build_role_model(store)
    return _CACHE[key]
