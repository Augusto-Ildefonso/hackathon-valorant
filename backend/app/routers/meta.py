"""Home endpoints: /api/meta, /api/search, /api/leaderboards, /api/matches (list). Owner: Stream A."""
from __future__ import annotations

import unicodedata
from functools import lru_cache

from fastapi import APIRouter

from ..data.catalog import get_catalog
from ..deps import get_store
from ..metrics import player_table, team_table
from ..metrics.config import LOW_SAMPLE
from ..schemas import LeaderboardsResponse, MatchListResponse, MetaResponse, SearchResponse
from ..schemas.common import MatchListItem, MatchSide, PlayerRef, TeamRef

router = APIRouter(prefix="/api", tags=["meta"])
LEADER_SIZE = 10
MIN_ROUNDS_FOR_RANKING = 100


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.casefold()) if unicodedata.category(c) != "Mn")


def match_items(store, df) -> list[MatchListItem]:
    cat = get_catalog()
    return [
        MatchListItem(
            match_id=m.match_id, tournament=m.tournament, phase=m.phase if isinstance(m.phase, str) else None, date=m.date,
            map=cat.map_ref(m.map_name),
            team_a=MatchSide(team=TeamRef(name=m.team_a), score=int(m.score_a)),
            team_b=MatchSide(team=TeamRef(name=m.team_b), score=int(m.score_b)),
            winner="a" if m.score_a > m.score_b else "b", duration_ms=int(m.duration_ms),
        )
        for m in df.itertuples()
    ]


@router.get("/meta", response_model=MetaResponse)
def meta():
    s, cat = get_store(), get_catalog()
    m = s.matches
    tournaments = []
    for code, g in m.groupby("tournament_code", sort=False):
        tournaments.append({"id": code, "name": g.tournament.iloc[0],
                            "phases": sorted(g.phase.dropna().unique()), "matches": len(g)})
    return {
        "kpis": {"matches": len(m), "rounds": len(s.rounds), "kills": len(s.kills),
                 "players": int(s.match_players.puuid.nunique()),
                 "teams": len(set(m.team_a) | set(m.team_b)), "tournaments": int(m.tournament_code.nunique())},
        "date_from": m.date.min(), "date_to": m.date.max(),
        "tournaments": sorted(tournaments, key=lambda t: t["name"]),
        "maps": [cat.map_ref(n) for n in sorted(m.map_name.unique())],
    }


@router.get("/search", response_model=SearchResponse)
def search(q: str = "", limit: int = 8):
    s, cat = get_store(), get_catalog()
    needle = _norm(q.strip())
    if not needle:
        return {"query": q, "players": [], "teams": [], "maps": []}
    pt, tt = _tables(None)
    hits = pt[pt.riot_id.map(lambda x: needle in _norm(x))].sort_values("matches", ascending=False).head(limit)
    thits = tt[[needle in _norm(n) for n in tt.index]].sort_values("matches", ascending=False).head(limit)
    maps = [n for n in sorted(s.matches.map_name.unique()) if needle in _norm(n)]
    return {
        "query": q,
        "players": [{"player": PlayerRef(puuid=i, riot_id=r.riot_id), "team": TeamRef(name=r.team), "matches": int(r.matches)}
                    for i, r in hits.iterrows()],
        "teams": [{"team": TeamRef(name=i), "matches": int(r.matches)} for i, r in thits.iterrows()],
        "maps": [{"map": cat.map_ref(n)} for n in maps],
    }


@lru_cache(maxsize=32)
def _tables(tournament: str | None):
    s = get_store().where(tournament=tournament)
    return player_table(s), team_table(s)


@router.get("/leaderboards", response_model=LeaderboardsResponse)
def leaderboards(tournament: str | None = None):
    pt, tt = _tables(tournament or None)
    pt = pt[pt.rounds >= MIN_ROUNDS_FOR_RANKING]  # ~5 matches: keeps tiny samples off the board
    tt = tt[tt.matches >= LOW_SAMPLE["matches"]]

    def players(col: str):
        top = pt.dropna(subset=[col]).sort_values(col, ascending=False).head(LEADER_SIZE)
        return [{"rank": n, "player": PlayerRef(puuid=i, riot_id=r.riot_id), "team": TeamRef(name=r.team),
                 "value": float(r[col]), "matches": int(r.matches), "rounds": int(r.rounds),
                 "low_sample": bool(r.matches < LOW_SAMPLE["matches"])} for n, (i, r) in enumerate(top.iterrows(), 1)]

    def teams(col: str):
        top = tt.sort_values(col, ascending=False).head(LEADER_SIZE)
        return [{"rank": n, "team": TeamRef(name=i), "value": float(r[col]), "matches": int(r.matches),
                 "rounds": int(r.rounds), "low_sample": bool(r.matches < LOW_SAMPLE["matches"])}
                for n, (i, r) in enumerate(top.iterrows(), 1)]

    return {"players": {c: players(c) for c in ("kd", "adr", "hs_pct", "first_kills")},
            "teams": {c: teams(c) for c in ("win_rate", "round_win_rate")}}


@router.get("/matches", response_model=MatchListResponse)
def list_matches(tournament: str | None = None, map: str | None = None, date_from: str | None = None,
                 date_to: str | None = None, team: str | None = None, limit: int = 20, offset: int = 0):
    s = get_store().where(tournament=tournament or None, map_name=map or None, date_from=date_from or None,
                          date_to=date_to or None, team=team or None)
    m = s.matches.sort_values(["game_start_ms", "match_id"], ascending=False)
    page = m.iloc[offset: offset + max(1, min(limit, 200))]
    return {"items": match_items(s, page), "total": len(m)}
