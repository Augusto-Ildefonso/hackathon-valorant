"""Home endpoints. Owner: Stream A. Stubs return contract fixtures until the real Store lands."""
from fastapi import APIRouter

from ..deps import fixture
from ..schemas import LeaderboardsResponse, MatchListResponse, MetaResponse, SearchResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def meta():
    return fixture("meta")


@router.get("/search", response_model=SearchResponse)
def search(q: str = ""):
    return {**fixture("search"), "query": q}


@router.get("/leaderboards", response_model=LeaderboardsResponse)
def leaderboards(tournament: str | None = None):
    return fixture("leaderboards")


@router.get("/matches", response_model=MatchListResponse)
def list_matches(tournament: str | None = None, map: str | None = None, date_from: str | None = None,
                 date_to: str | None = None, team: str | None = None, limit: int = 20, offset: int = 0):
    return fixture("matches")
