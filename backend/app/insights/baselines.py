"""Dataset-wide reference distributions for the insight rules. Owner: Stream D.

Every distribution is computed from the full store, over the *qualified* population only (players with enough rounds,
teams with enough matches/rounds), so a value is judged against comparable players/teams. `Dist` carries the
percentile cuts the rules compare with (`p_weak`, `median`, `p_strong`) and the population size.
Units: rates are percentages (0..100) and K/D, ADR are plain numbers, matching the `Evidence` shown in the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data.store import Store
from ..metrics import player_table, team_rounds, team_table
from ..metrics.objective import attack_rounds
from . import thresholds as T


@dataclass(frozen=True)
class Dist:
    p_weak: float
    median: float
    p_strong: float
    n: int


@dataclass
class Baselines:
    players: dict[str, Dist] = field(default_factory=dict)
    teams: dict[str, Dist] = field(default_factory=dict)
    rates: dict[str, float] = field(default_factory=dict)  # global rates (0..1), e.g. attack win rate


def _dist(values: pd.Series, scale: float = 1.0) -> Dist | None:
    v = values.dropna().to_numpy(float) * scale
    if len(v) < 5:
        return None
    return Dist(float(np.quantile(v, T.WEAK_PCT)), float(np.median(v)), float(np.quantile(v, T.STRONG_PCT)), len(v))


def compute_baselines(store: Store) -> Baselines:
    b = Baselines()
    p = player_table(store)
    q = p[p.rounds >= T.QUALIFY_PLAYER_ROUNDS].copy()
    q["first_death_rate"] = q.first_deaths / q.rounds
    q["first_kill_rate"] = q.first_kills / q.rounds
    q["trade_share"] = q.traded_deaths / q.deaths.clip(lower=1)
    for name, col, scale in (("kd", "kd", 1), ("adr", "adr", 1), ("hs_pct", "hs_pct", 100), ("opening_win_pct", "opening_win_pct", 100),
                             ("first_death_rate", "first_death_rate", 100), ("first_kill_rate", "first_kill_rate", 100),
                             ("trade_share", "trade_share", 100)):
        d = _dist(q[col], scale)
        if d:
            b.players[name] = d

    t = team_table(store)
    t = t[t.matches >= T.QUALIFY_TEAM_MATCHES]
    for name, col in (("round_win_rate", "round_win_rate"), ("attack_win_rate", "attack_win_rate"),
                      ("defense_win_rate", "defense_win_rate"), ("win_rate", "win_rate")):
        d = _dist(t[col], 100)
        if d:
            b.teams[name] = d

    tr = team_rounds(store)
    per = tr.groupby(["team_name", "round_type"]).won.agg(["mean", "size"]).reset_index()
    for rt in ("pistol", "eco", "semi_eco", "force", "full_buy"):
        d = _dist(per[(per.round_type == rt) & (per["size"] >= T.QUALIFY_TEAM_ROUNDS)]["mean"], 100)
        if d:
            b.teams[f"{rt}_win_rate"] = d
    for side in ("attack", "defense"):
        b.rates[f"{side}_win_rate"] = float(tr[tr.side == side].won.mean())
    for rt, g in tr.groupby("round_type"):
        b.rates[f"{rt}_win_rate"] = float(g.won.mean())

    r = attack_rounds(store)
    planted = r[r.planted]
    pp = planted.groupby("attacker_team").attacker_won.agg(["mean", "size"])
    d = _dist(pp[pp["size"] >= T.QUALIFY_TEAM_EVENTS]["mean"], 100)
    if d:
        b.teams["post_plant_win_rate"] = d
    rt_ = planted.groupby("defender_team").defused.agg(["mean", "size"])
    d = _dist(rt_[rt_["size"] >= T.QUALIFY_TEAM_EVENTS]["mean"], 100)
    if d:
        b.teams["retake_rate"] = d
    b.rates["post_plant_win_rate"] = float(planted.attacker_won.mean()) if len(planted) else 0.5
    b.rates["retake_rate"] = float(planted.defused.mean()) if len(planted) else 0.3
    return b


_CACHE: dict[int, Baselines] = {}


def get_baselines(store: Store | None = None) -> Baselines:
    """Baselines of the FULL dataset (cached per store object). Without an argument it uses the app's store."""
    if store is None:
        from ..deps import get_store

        store = get_store()
    key = id(store)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = compute_baselines(store)
    return _CACHE[key]
