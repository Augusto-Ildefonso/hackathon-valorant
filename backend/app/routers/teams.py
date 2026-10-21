"""Team endpoints. Owner: Stream B."""
from typing import Literal

from fastapi import APIRouter, HTTPException

from ..analytics.teams import team_exists, team_list, team_profile
from ..deps import get_store
from ..insights import engine
from ..schemas import TeamListResponse, TeamProfile

router = APIRouter(prefix="/api", tags=["teams"])


@router.get("/teams", response_model=TeamListResponse)
def teams(tournament: str | None = None):
    return {"items": team_list(get_store().where(tournament=tournament or None))}


@router.get("/teams/{name}", response_model=TeamProfile)
def team(name: str, tournament: str | None = None, map: str | None = None, insights: Literal["rules", "llm"] = "rules"):
    full = get_store()
    if not team_exists(full, name):
        raise HTTPException(404, f"Unknown team {name}")
    store = full.where(tournament=tournament or None, map_name=map or None)
    if not team_exists(store, name):
        raise HTTPException(404, "Team has no matches for these filters")
    profile = team_profile(store, name, full_store=full)
    profile.insights, profile.insights_source = engine.team_insights(profile, insights)
    return profile
