"""Team list and Team Profile builders. Owner: Stream B. Uses only `Store` + `app.metrics`."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from ..data.catalog import get_catalog
from ..data.store import Store
from ..metrics import make_stat, objective_summary, player_table, team_rounds, team_table
from ..metrics.objective import attack_rounds
from ..metrics.rounds import ROUND_TYPES
from ..schemas.common import PlayerRef, TeamRef
from ..schemas.team import (RoleCount, RosterMember, TeamEconomy, TeamListItem, TeamMapPerformance, TeamProfile,
                            TeamRecord, TrendPoint)
from .roles import role_model

ROSTER_LIMIT = 12


def team_exists(store: Store, name: str) -> bool:
    m = store.matches
    return bool(((m.team_a == name) | (m.team_b == name)).any())


def team_list(store: Store) -> list[TeamListItem]:
    tt = team_table(store).sort_values(["matches", "win_rate"], ascending=False)
    return [TeamListItem(team=TeamRef(name=n), matches=int(r.matches), win_rate=make_stat(r.win_rate, int(r.matches), "matches"),
                         round_win_rate=make_stat(r.round_win_rate, int(r.rounds)), last_match_date=r.last_match_date)
            for n, r in tt.iterrows()]


def _roster(store: Store, name: str, roles) -> tuple[list[RosterMember], list[RoleCount]]:
    mp = store.match_players[store.match_players.team_name == name]
    latest = (mp.merge(store.matches[["match_id", "game_start_ms"]], on="match_id")
              .sort_values("game_start_ms", ascending=False))
    ids = latest.groupby("puuid").agg(matches=("match_id", "nunique"), riot_id=("riot_id", "first")).sort_values(
        "matches", ascending=False)
    members = []
    stats = player_table(store)
    for puuid, r in ids.head(ROSTER_LIMIT).iterrows():
        top = roles.roles_for(puuid, top=1)
        members.append(RosterMember(player=PlayerRef(puuid=puuid, riot_id=r.riot_id), matches=int(r.matches),
                                    top_role=top[0] if top else None, kd=float(stats.loc[puuid, "kd"]),
                                    adr=float(stats.loc[puuid, "adr"])))
    last_match = latest.match_id.iloc[0]
    current = latest[latest.match_id == last_match].puuid
    counts = Counter(t[0].role for p in current if (t := roles.roles_for(p, top=1)))
    return members, [RoleCount(role=r, count=c) for r, c in counts.most_common()]


def _matches_and_trend(store: Store, name: str):
    from ..routers.meta import match_items  # lazy: the item builder lives with the list endpoint

    m = store.matches[(store.matches.team_a == name) | (store.matches.team_b == name)]
    m = m.sort_values(["game_start_ms", "match_id"], ascending=False)
    items = match_items(store, m)
    own = m.score_a.where(m.team_a == name, m.score_b)
    opp = m.score_b.where(m.team_a == name, m.score_a)
    trend = [TrendPoint(match_id=i, date=d, round_diff=int(o - p), map_name=mp)
             for i, d, o, p, mp in zip(m.match_id, m.date, own, opp, m.map_name)][::-1]  # oldest first
    return items, trend


def _economy(store: Store, name: str, tr: pd.DataFrame) -> TeamEconomy:
    mine = tr[tr.team_name == name]
    by_type = {t: make_stat(g.won.mean() if len(g) else None, len(g))
               for t in ROUND_TYPES for g in [mine[mine.round_type == t]]}
    obj = objective_summary(store, team=name)
    sites = {s: st for s, st in obj["site_preference"].items() if st.value}
    r = attack_rounds(store)
    defending = r[(r.defender_team == name) & r.planted]
    return TeamEconomy(
        win_rate_by_round_type=by_type, pistol_win_rate=by_type["pistol"], plant_site_preference=sites,
        avg_time_to_plant_ms=obj["avg_time_to_plant_ms"], post_plant_win_rate=obj["post_plant_win_rate"],
        retake_success_rate=make_stat(defending.defused.mean() if len(defending) else None, len(defending), "events"))


def _by_map(store: Store, name: str, tr: pd.DataFrame) -> list[TeamMapPerformance]:
    cat = get_catalog()
    m = store.matches[(store.matches.team_a == name) | (store.matches.team_b == name)]
    won = m.winner_team == name
    mine = tr[tr.team_name == name].merge(store.matches[["match_id", "map_name"]], on="match_id")
    out = []
    for map_name, g in m.groupby("map_name"):
        t = mine[mine.map_name == map_name]
        att, dfn = t[t.side == "attack"], t[t.side == "defense"]
        out.append(TeamMapPerformance(
            map=cat.map_ref(map_name), matches=len(g), win_rate=make_stat(won[g.index].mean(), len(g), "matches"),
            attack_win_rate=make_stat(att.won.mean() if len(att) else None, len(att)),
            defense_win_rate=make_stat(dfn.won.mean() if len(dfn) else None, len(dfn))))
    return sorted(out, key=lambda x: -x.matches)


def team_profile(store: Store, name: str, full_store: Store | None = None) -> TeamProfile:
    """Profile of team `name` over `store` (already filtered by the caller). Roles use the whole dataset."""
    sub = store.where(team=name)
    tt = team_table(sub).loc[name]
    tr = team_rounds(sub)
    record = TeamRecord(
        matches=int(tt.matches), series=int(tt.series), wins=int(tt.wins), losses=int(tt.losses),
        round_win_rate=make_stat(tt.round_win_rate, int(tt.rounds)),
        attack_win_rate=make_stat(tt.attack_win_rate, int(tt.attack_rounds)),
        defense_win_rate=make_stat(tt.defense_win_rate, int(tt.defense_rounds)))
    roster, composition = _roster(sub, name, role_model(full_store or store))
    items, trend = _matches_and_trend(sub, name)
    return TeamProfile(team=TeamRef(name=name), roster=roster, record=record, matches=items, trend=trend,
                       by_map=_by_map(sub, name, tr), economy=_economy(sub, name, tr), role_composition=composition,
                       insights=[])
