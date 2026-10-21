"""Player endpoint. Owner: Stream B."""
from fastapi import APIRouter, HTTPException

from ..analytics.players import player_exists, player_profile
from ..deps import get_store
from ..insights import engine
from ..schemas import PlayerProfile

router = APIRouter(prefix="/api", tags=["players"])


@router.get("/players/{puuid}", response_model=PlayerProfile)
def player(puuid: str, tournament: str | None = None, map: str | None = None):
    full = get_store()
    if not player_exists(full, puuid):
        raise HTTPException(404, f"Unknown player {puuid}")
    store = full.where(tournament=tournament or None, map_name=map or None)
    if not player_exists(store, puuid):
        raise HTTPException(404, "Player has no matches for these filters")
    profile = player_profile(store, puuid, full_store=full)
    profile.insights = engine.for_player(profile)
    return profile
