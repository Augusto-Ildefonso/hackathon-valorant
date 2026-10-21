"""Map endpoints. Owner: Stream C."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ..analytics.heatmaps import heatmap as build_heatmap
from ..analytics.maps import canonical_map_name, map_exists, map_list, map_profile
from ..deps import get_store
from ..insights import engine
from ..schemas import HeatmapResponse, MapListResponse, MapProfile

router = APIRouter(prefix="/api", tags=["maps"])
_HEAT_CACHE: dict[tuple, HeatmapResponse] = {}  # data is static in-process; keyed by every input that changes the result


def _store(tournament: str | None, name: str):
    canon = canonical_map_name(name)
    if canon is None or not map_exists(get_store(), canon):
        raise HTTPException(404, f"Unknown map {name}")
    s = get_store().where(tournament=tournament or None)
    if not map_exists(s, canon):
        raise HTTPException(404, "Map has no matches for these filters")
    return canon, s


@router.get("/maps", response_model=MapListResponse)
def maps(tournament: str | None = None):
    return {"items": map_list(get_store().where(tournament=tournament or None))}


@router.get("/maps/{name}", response_model=MapProfile)
def map_profile_endpoint(name: str, tournament: str | None = None, insights: Literal["rules", "llm"] = "rules"):
    canon, s = _store(tournament, name)
    profile = map_profile(s, canon)
    profile.insights, profile.insights_source = engine.map_insights(profile, s.where(map_name=canon), insights)
    return profile


@router.get("/maps/{name}/heatmap", response_model=HeatmapResponse)
def heatmap(name: str, side: Literal["attack", "defense", "both"] = "both", grid_size: int = Query(64, ge=16, le=128),
            tournament: str | None = None):
    canon, s = _store(tournament, name)
    key = (tournament or "", canon, side, grid_size)
    if key not in _HEAT_CACHE:
        _HEAT_CACHE[key] = build_heatmap(s, canon, side, grid_size)
    return _HEAT_CACHE[key]
