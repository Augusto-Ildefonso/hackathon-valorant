"""Frozen API contract. Every router returns one of these models; every contract fixture validates against one."""
from .common import *  # noqa: F401,F403
from .map import HeatmapResponse, MapListResponse, MapProfile
from .match import KillsResponse, MatchListResponse, MatchReport
from .meta import LeaderboardsResponse, MetaResponse, SearchResponse
from .plan import PlanRequest, PlanResponse
from .player import PlayerProfile
from .team import TeamListResponse, TeamProfile

# endpoint -> response model. Used by the contract test and by `contract/openapi.md`.
ENDPOINTS = {
    "meta": MetaResponse,
    "search": SearchResponse,
    "leaderboards": LeaderboardsResponse,
    "matches": MatchListResponse,
    "player": PlayerProfile,
    "teams": TeamListResponse,
    "team": TeamProfile,
    "maps": MapListResponse,
    "map": MapProfile,
    "map_heatmap": HeatmapResponse,
    "match": MatchReport,
    "match_kills": KillsResponse,
    "plan": PlanResponse,
}
