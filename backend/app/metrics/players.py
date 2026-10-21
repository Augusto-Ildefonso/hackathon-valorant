"""Per-player and per-team aggregates (one implementation, used by every screen). Owner: Stream A (see SPEC.md)."""
from __future__ import annotations

import pandas as pd

from ..data.store import Store
from .events import clutch_events, kill_events, multikills


def player_table(store: Store) -> pd.DataFrame:
    """One row per player (index `puuid`): riot_id, team (most recent), matches, rounds, kills, deaths, assists, kd,
    adr, hs_pct, shots (head+body+leg hits, sample size of hs_pct), first_kills, first_deaths, opening_win_pct,
    clutches (won 1vX), clutch_attempts, k2..k5 (multi-kill rounds)."""
    mp = store.match_players.merge(store.matches[["match_id", "game_start_ms"]], on="match_id")
    latest = mp.sort_values("game_start_ms").groupby("puuid").tail(1).set_index("puuid")[["riot_id", "team_name"]]
    t = mp.groupby("puuid").agg(matches=("match_id", "nunique"), kills=("kills", "sum"), deaths=("deaths", "sum"),
                                assists=("assists", "sum"), score=("score", "sum"))
    r = store.round_player_stats.groupby("puuid").agg(
        rounds=("round_num", "size"), damage=("damage_dealt", "sum"), head_hits=("headshots", "sum"),
        body_hits=("bodyshots", "sum"), leg_hits=("legshots", "sum"))
    t = t.join(r).join(latest).rename(columns={"team_name": "team"})
    t["kd"] = t.kills / t.deaths.clip(lower=1)
    t["adr"] = t.damage / t.rounds.clip(lower=1)
    t["shots"] = t.head_hits + t.body_hits + t.leg_hits
    t["hs_pct"] = t.head_hits / t.shots.where(t.shots > 0)

    ke = kill_events(store)
    fk = ke[ke.is_first & ke.killer_color.notna() & ~ke.teamkill].groupby("killer").size().rename("first_kills")
    fd = ke[ke.is_first].groupby("victim").size().rename("first_deaths")
    t = t.join(fk).join(fd)
    t[["first_kills", "first_deaths"]] = t[["first_kills", "first_deaths"]].fillna(0).astype(int)
    t["opening_win_pct"] = t.first_kills / (t.first_kills + t.first_deaths).where(lambda s: s > 0)
    t = t.join(ke[ke.death_traded].groupby("victim").size().rename("traded_deaths"))
    t["traded_deaths"] = t.traded_deaths.fillna(0).astype(int)

    c = clutch_events(store)
    t = t.join(c.groupby("puuid").size().rename("clutch_attempts")).join(c[c.won].groupby("puuid").size().rename("clutches"))
    mk = multikills(store)
    for n in (2, 3, 4, 5):
        t = t.join(mk[mk.kills == n].groupby("puuid").size().rename(f"k{n}"))
    cols = ["clutch_attempts", "clutches", "k2", "k3", "k4", "k5"]
    t[cols] = t[cols].fillna(0).astype(int)
    t.index.name = "puuid"
    return t


def team_table(store: Store) -> pd.DataFrame:
    """One row per team (index `team`): matches, series, wins, losses, win_rate, rounds, round_win_rate,
    attack_rounds/attack_win_rate, defense_rounds/defense_win_rate, last_match_date."""
    m = store.matches
    long = pd.concat([
        m.assign(team=m.team_a, own=m.score_a, opp=m.score_b),
        m.assign(team=m.team_b, own=m.score_b, opp=m.score_a),
    ])
    long["win"] = long.own > long.opp
    g = long.groupby("team").agg(matches=("match_id", "size"), wins=("win", "sum"), rounds_won=("own", "sum"),
                                 rounds_lost=("opp", "sum"), last_match_date=("date", "max"))
    g["series"] = long.groupby("team").apply(lambda d: d[["tournament_code", "phase", "series_no"]].drop_duplicates().shape[0],
                                             include_groups=False)
    g["losses"] = g.matches - g.wins
    g["win_rate"] = g.wins / g.matches
    g["rounds"] = g.rounds_won + g.rounds_lost
    g["round_win_rate"] = g.rounds_won / g.rounds
    r = store.rounds
    for side, col in (("attacker_team", "attack"), ("defender_team", "defense")):
        won = r[r.winning_team == r[side]].groupby(side).size()
        total = r.groupby(side).size()
        g[f"{col}_rounds"] = total
        g[f"{col}_win_rate"] = won.reindex(total.index).fillna(0) / total
    g["wins"] = g.wins.astype(int)
    g.index.name = "team"
    return g
