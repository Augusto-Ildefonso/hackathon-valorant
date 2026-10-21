"""Player endpoint. Owner: Stream B."""
from fastapi import APIRouter

from ..deps import fixture
from ..schemas import PlayerProfile

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/players/{puuid}", response_model=PlayerProfile)
def player(puuid: str, tournament: str | None = None, map: str | None = None):
    return fixture("player")
