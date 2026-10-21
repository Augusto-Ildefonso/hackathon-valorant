"""Map endpoints. Owner: Stream C."""
from typing import Literal

from fastapi import APIRouter

from ..deps import fixture
from ..schemas import HeatmapResponse, MapListResponse, MapProfile

router = APIRouter(prefix="/api", tags=["maps"])


@router.get("/maps", response_model=MapListResponse)
def maps(tournament: str | None = None):
    return fixture("maps")


@router.get("/maps/{name}", response_model=MapProfile)
def map_profile(name: str, tournament: str | None = None):
    return fixture("map")


@router.get("/maps/{name}/heatmap", response_model=HeatmapResponse)
def heatmap(name: str, side: Literal["attack", "defense", "both"] = "both", grid_size: int = 64,
            tournament: str | None = None):
    return fixture("map_heatmap")
