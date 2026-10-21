"""Team endpoints. Owner: Stream B."""
from fastapi import APIRouter

from ..deps import fixture
from ..schemas import TeamListResponse, TeamProfile

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams", response_model=TeamListResponse)
def teams(tournament: str | None = None):
    return fixture("teams")


@router.get("/teams/{name}", response_model=TeamProfile)
def team(name: str, tournament: str | None = None, map: str | None = None):
    return fixture("team")
