"""Team-round table, round types, round-type transitions, projected economy and round win probability.

Owner: Stream A (definitions in SPEC.md). These feed the Action Plan (Stream D) and team economy stats (Stream B).
"""
from __future__ import annotations

import pandas as pd

from ..data.store import Store
from ..schemas.common import RoundType
from .config import ECONOMY, MIN_TRANSITIONS, WIN_PROB_K, classify_round, make_stat

ROUND_TYPES: list[RoundType] = ["pistol", "eco", "semi_eco", "force", "full_buy"]
KEY = ["match_id", "round_num"]


def team_rounds(store: Store) -> pd.DataFrame:
    """One row per (match, round, team): side, result, round type, economy and the previous-round state.

    Columns: match_id, round_num, half, team_name, opp_team, side, won, loadout_mean, credits_start (mean per player,
    spent + remaining), spent_mean, remaining_mean, kills, round_type, enemy_type, prev_type, prev_won, loss_streak
    (consecutive losses before this round, reset at rounds 0 and 12), planted.
    """
    rps = store.round_player_stats
    g = rps.groupby(KEY + ["team_name"]).agg(
        side=("side", "first"), loadout_mean=("loadout_value", "mean"), spent_mean=("spent", "mean"),
        remaining_mean=("remaining", "mean"), kills=("kills_n", "sum")).reset_index()
    g["credits_start"] = g.spent_mean + g.remaining_mean
    r = store.rounds[KEY + ["half", "winning_team", "planter"]]
    g = g.merge(r, on=KEY)
    g["won"] = g.team_name == g.winning_team
    g["planted"] = g.planter.notna()
    g["round_type"] = [classify_round(n, v) for n, v in zip(g.round_num, g.loadout_mean)]
    opp = g[KEY + ["team_name", "round_type"]].rename(columns={"team_name": "opp_team", "round_type": "enemy_type"})
    g = g.merge(opp, on=KEY)
    g = g[g.team_name != g.opp_team].drop(columns=["winning_team", "planter"])

    g = g.sort_values(["match_id", "team_name", "round_num"]).reset_index(drop=True)
    prev_type, prev_won, streak = [], [], []
    cur_streak, last = 0, None  # `last` = previous row of the same team within the match
    prev_key = None
    for row in g.itertuples():
        key = (row.match_id, row.team_name)
        if key != prev_key or row.round_num in (0, 12):
            cur_streak, last = 0, None
        prev_type.append(last.round_type if last is not None else None)
        prev_won.append(last.won if last is not None else None)
        streak.append(cur_streak)
        cur_streak = 0 if row.won else cur_streak + 1
        last, prev_key = row, key
    g["prev_type"], g["prev_won"], g["loss_streak"] = prev_type, prev_won, streak
    return g


# ---- round-type transitions ------------------------------------------------------------------------------------------
def next_type_distribution(tr: pd.DataFrame, prev_type: RoundType, prev_won: bool, loss_streak: int,
                           team: str | None = None) -> dict:
    """P(next round type | prev type, prev result, loss streak) for `team`, falling back to the whole dataset when the
    team has fewer than MIN_TRANSITIONS matching rounds. Returns {probs, sample_size, source, low_sample}."""
    streak = min(loss_streak, 3)

    def sel(df: pd.DataFrame) -> pd.DataFrame:
        d = df[(df.prev_type == prev_type) & (df.prev_won == prev_won) & (df.loss_streak.clip(upper=3) == streak)]
        return d

    source, d = "global", sel(tr)
    if team is not None:
        td = sel(tr[tr.team_name == team])
        if len(td) >= MIN_TRANSITIONS:
            source, d = "team", td
    counts = d.round_type.value_counts()
    n = int(counts.sum())
    probs = {t: float(counts.get(t, 0) / n) if n else 0.0 for t in ROUND_TYPES}
    return {"probs": probs, "sample_size": n, "source": source, "low_sample": n < MIN_TRANSITIONS}


# ---- projected economy -----------------------------------------------------------------------------------------------
def income_per_player(won: bool, loss_streak_after: int, planted_and_lost: bool = False, kills: float = 0.0) -> float:
    """Credits earned by one player at the end of a round. `loss_streak_after` counts this round when lost (>=1)."""
    e = ECONOMY
    if won:
        base = e["win"]
    else:
        base = e["loss"][min(max(loss_streak_after, 1), len(e["loss"])) - 1]
        base += e["plant_bonus"] if planted_and_lost else 0
    return base + e["kill"] * kills


def project_next_credits(remaining_mean: float, won: bool, loss_streak_before: int, planted_and_lost: bool = False,
                         kills_mean: float = 0.0, next_round_num: int | None = None) -> float:
    """Expected mean credits per player at the start of the next round. Pistol rounds start at 800."""
    if next_round_num in (0, 12):
        return float(ECONOMY["start"])
    streak_after = 0 if won else loss_streak_before + 1
    inc = income_per_player(won, streak_after, planted_and_lost, kills_mean)
    return float(min(ECONOMY["cap"], remaining_mean + inc))


def projected_economy(prev_remaining_mean: float, prev_won: bool, loss_streak_before: int, planted_and_lost: bool,
                      kills_mean: float, next_round_num: int, players: int = 5) -> dict:
    """Team-level projection: {per_player, team_total}."""
    pp = project_next_credits(prev_remaining_mean, prev_won, loss_streak_before, planted_and_lost, kills_mean, next_round_num)
    return {"per_player": pp, "team_total": pp * players}


def typical_loadout_by_type(tr: pd.DataFrame, team: str | None = None) -> dict[RoundType, float]:
    """Mean team loadout value by round type (team-specific when `team` is given and has data)."""
    d = tr if team is None else tr[tr.team_name == team]
    d = d if len(d) else tr
    return {t: float(v) for t, v in d.groupby("round_type").loadout_mean.mean().items()}


# ---- round win probability -------------------------------------------------------------------------------------------
def round_win_probability(tr: pd.DataFrame, team: str, side: str, round_type: RoundType, enemy_type: RoundType | None = None,
                          map_match_ids: set | None = None, k: int = WIN_PROB_K) -> dict:
    """Shrunk win probability of `team` in a round of `round_type` on `side`.
    p = (wins + k * p_global) / (n + k), where p_global is the dataset-wide win rate for (side, round_type[, enemy_type]).
    Pass `map_match_ids` to restrict the team's own sample to one map. Returns {value, sample_size, low_sample, p_global}."""
    base = tr[(tr.side == side) & (tr.round_type == round_type)]
    if enemy_type is not None and len(base[base.enemy_type == enemy_type]) >= 30:
        base = base[base.enemy_type == enemy_type]
    p_global = float(base.won.mean()) if len(base) else 0.5
    own = tr[(tr.team_name == team) & (tr.side == side) & (tr.round_type == round_type)]
    if enemy_type is not None:
        own_e = own[own.enemy_type == enemy_type]
        own = own_e if len(own_e) >= 5 else own
    if map_match_ids is not None:
        own = own[own.match_id.isin(map_match_ids)]
    n, wins = len(own), int(own.won.sum())
    p = (wins + k * p_global) / (n + k)
    st = make_stat(p, n, "rounds")
    return {"value": st.value, "sample_size": n, "low_sample": st.low_sample, "p_global": p_global}
