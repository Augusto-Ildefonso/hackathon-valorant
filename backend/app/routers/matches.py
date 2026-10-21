"""Match endpoints (detail + kills). The list endpoint lives in meta.py (Stream A). Owner: Stream C."""
from fastapi import APIRouter

from ..deps import fixture
from ..schemas import KillsResponse, MatchReport

router = APIRouter(prefix="/api", tags=["matches"])


@router.get("/matches/{match_id}", response_model=MatchReport)
def match(match_id: str):
    return fixture("match")


@router.get("/matches/{match_id}/kills", response_model=KillsResponse)
def match_kills(match_id: str, round: int | None = None, player: str | None = None, team: str | None = None):
    return fixture("match_kills")
