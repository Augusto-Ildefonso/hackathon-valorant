"""Match Report builder. Owner: Stream C. Uses only `Store` + `app.metrics` + the catalog."""
from __future__ import annotations

import pandas as pd

from ..data.catalog import get_catalog
from ..data.store import Store
from ..metrics import kill_events, make_stat, team_rounds
from ..schemas.common import AgentRef, MatchSide, PlayerRef, TeamRef
from ..schemas.match import MatchReport, RoundEconomy, RoundSummary, ScoreboardRow

RESULT = {"Eliminated": "eliminated", "Bomb defused": "defused", "Bomb detonated": "detonated", "Round timer expired": "timer"}
HALF = {1: 1, 2: 2, 3: "ot"}


def match_exists(store: Store, match_id: str) -> bool:
    return bool((store.matches.match_id == match_id).any())


def _ceremony(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    name = raw.removeprefix("Ceremony")
    return None if name in ("", "Default") else name


def _rounds(s: Store, team_a: str) -> list[RoundSummary]:
    tr = team_rounds(s)
    out = []
    for r in s.rounds.sort_values("round_num").itertuples():
        t = tr[tr.round_num == r.round_num].set_index("team_name")
        a = t.loc[team_a]
        b = t.loc[a.opp_team]
        out.append(RoundSummary(
            number=int(r.round_num) + 1, half=HALF[int(r.half)], winner="a" if r.winning_team == team_a else "b",
            team_a_side="attack" if r.attacker_team == team_a else "defense", result=RESULT[r.result],
            ceremony=_ceremony(r.ceremony), plant_site=r.plant_site if isinstance(r.plant_site, str) else None,
            planted=isinstance(r.planter, str), defused=isinstance(r.defuser, str),
            economy=RoundEconomy(team_a_type=a.round_type, team_b_type=b.round_type,
                                 team_a_loadout=int(round(a.loadout_mean)), team_b_loadout=int(round(b.loadout_mean)))))
    return out


def _scoreboard(s: Store, team_a: str) -> list[ScoreboardRow]:
    cat = get_catalog()
    mp = s.match_players
    rps = s.round_player_stats.groupby("puuid").agg(
        rounds=("round_num", "size"), damage=("damage_dealt", "sum"), head_hits=("headshots", "sum"),
        body_hits=("bodyshots", "sum"), leg_hits=("legshots", "sum"))
    ke = kill_events(s)
    fk = ke[ke.is_first & ~ke.teamkill].groupby("killer").size()
    rows = []
    for p in mp.itertuples():
        g = rps.loc[p.puuid]
        shots = g.head_hits + g.body_hits + g.leg_hits
        rows.append(ScoreboardRow(
            player=PlayerRef(puuid=p.puuid, riot_id=p.riot_id), team="a" if p.team_name == team_a else "b",
            agent=cat.agent(p.agent_id) or AgentRef(id="unknown"), kills=int(p.kills), deaths=int(p.deaths),
            assists=int(p.assists), adr=make_stat(g.damage / max(g.rounds, 1), int(g.rounds)),
            hs_pct=make_stat(g.head_hits / shots if shots else None, int(g.rounds)), first_kills=int(fk.get(p.puuid, 0)),
            score=int(p.score)))
    return sorted(rows, key=lambda r: (r.team, -r.kills))


def match_report(store: Store, match_id: str) -> MatchReport:
    """Report for one match. Raises KeyError for an unknown id."""
    s = store.subset([match_id])
    if s.matches.empty:
        raise KeyError(match_id)
    m = s.matches.iloc[0]
    cat = get_catalog()
    winner = "a" if m.score_a > m.score_b else "b"
    board = _scoreboard(s, m.team_a)
    # MVP = highest game score on the winning team (the in-game definition)
    winners = [r for r in board if r.team == winner]
    mvp = max(winners, key=lambda r: r.score).player if winners else None
    return MatchReport(
        match_id=match_id, tournament=m.tournament, phase=m.phase if isinstance(m.phase, str) else None, date=m.date,
        map=cat.map_ref(m.map_name), duration_ms=int(m.duration_ms),
        team_a=MatchSide(team=TeamRef(name=m.team_a), score=int(m.score_a)),
        team_b=MatchSide(team=TeamRef(name=m.team_b), score=int(m.score_b)), winner=winner, mvp=mvp,
        rounds=_rounds(s, m.team_a), scoreboard=board, insights_a=[], insights_b=[])
