"""Insight engine entry points. Signatures are FROZEN in Phase 0; Stream D owns the implementation.

Routers call these with the stats object their own analytics produced (the matching `schemas` model); the engine
never reads raw JSON. Until D ships real rules every function returns `[]`, so callers can already integrate.
"""
from __future__ import annotations

from ..schemas.common import Insight
from ..schemas.map import MapProfile
from ..schemas.match import MatchReport
from ..schemas.player import PlayerProfile
from ..schemas.team import TeamProfile


def for_player(stats: PlayerProfile) -> list[Insight]:
    """Strengths, weaknesses and training tips for one player."""
    return []


def for_team(stats: TeamProfile) -> list[Insight]:
    """Strengths, weaknesses and improvement suggestions for one team."""
    return []


def for_match(report: MatchReport) -> tuple[list[Insight], list[Insight]]:
    """(insights for team A, insights for team B), evidence taken from this match only."""
    return [], []


def for_map(stats: MapProfile) -> list[Insight]:
    """Map-level strategy insights (side bias, site tendencies)."""
    return []
