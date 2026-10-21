"""Kill-derived events: first kills/deaths, trades, multi-kills, clutches. Owner: Stream A (see SPEC.md)."""
from __future__ import annotations

import pandas as pd

from ..data.store import Store
from .config import TRADE_WINDOW_MS

KEY = ["match_id", "round_num"]


def kill_events(store: Store, trade_window_ms: int = TRADE_WINDOW_MS) -> pd.DataFrame:
    """One row per kill, ordered within the round, with:
    `is_first` (opening kill of the round), `teamkill`, `is_trade` (this kill avenged a teammate that this kill's
    victim had killed <= window earlier) and `death_traded` (this kill's victim was avenged by a teammate)."""
    cols = KEY + ["kill_idx", "time_in_round_ms", "killer", "victim", "killer_color", "victim_color"]
    k = store.kills[cols + ["damage_type", "damage_item"]].sort_values(KEY + ["time_in_round_ms", "kill_idx"]).reset_index(drop=True)
    k["order"] = k.groupby(KEY).cumcount()
    k["is_first"] = k.order == 0
    k["teamkill"] = k.killer_color.notna() & (k.killer_color == k.victim_color)

    a = k[cols + ["order"]]
    j = a.merge(a, on=KEY, suffixes=("_k", "_p"))  # k = the possible trade kill, p = the earlier kill it avenges
    dt = j.time_in_round_ms_k - j.time_in_round_ms_p
    hit = j[(j.order_p < j.order_k) & (j.killer_p == j.victim_k) & j.killer_color_k.notna()
            & (j.victim_color_p == j.killer_color_k) & (dt >= 0) & (dt <= trade_window_ms)]
    key = pd.MultiIndex.from_frame(k[["match_id", "kill_idx"]])
    k["is_trade"] = key.isin(pd.MultiIndex.from_frame(hit[["match_id", "kill_idx_k"]]))
    k["death_traded"] = key.isin(pd.MultiIndex.from_frame(hit[["match_id", "kill_idx_p"]]))
    return k


def multikills(store: Store) -> pd.DataFrame:
    """Per (match, round, player): number of kills; only >= 2. Teamkills and non-player killers excluded."""
    k = store.kills
    k = k[k.killer_color.notna() & (k.killer_color != k.victim_color)]
    n = k.groupby(KEY + ["killer"]).size().rename("kills").reset_index()
    return n[n.kills >= 2].rename(columns={"killer": "puuid"})


def clutch_events(store: Store) -> pd.DataFrame:
    """Every 1vX situation (X >= 1): the last alive player of a team vs `vs` living enemies.
    Columns: match_id, round_num, puuid, team_color, vs, won (that team won the round)."""
    rps = store.round_player_stats[KEY + ["puuid", "team_color"]]
    rosters = {key: g for key, g in rps.groupby(KEY)}
    winners = store.rounds.set_index(KEY).winning_color
    out = []
    kills = store.kills.sort_values(KEY + ["time_in_round_ms", "kill_idx"])
    for key, g in kills.groupby(KEY):
        roster = rosters.get(key)
        if roster is None:
            continue
        alive = {c: set(sub.puuid) for c, sub in roster.groupby("team_color")}
        flagged = set()
        for victim, vcolor in zip(g.victim, g.victim_color):
            if vcolor not in alive:
                continue
            alive[vcolor].discard(victim)
            other = "Blue" if vcolor == "Red" else "Red"
            if len(alive[vcolor]) == 1 and len(alive.get(other, ())) >= 1 and vcolor not in flagged:
                flagged.add(vcolor)
                (survivor,) = alive[vcolor]
                out.append(dict(match_id=key[0], round_num=key[1], puuid=survivor, team_color=vcolor,
                                vs=len(alive[other]), won=winners.get(key) == vcolor))
    return pd.DataFrame(out, columns=KEY + ["puuid", "team_color", "vs", "won"])
