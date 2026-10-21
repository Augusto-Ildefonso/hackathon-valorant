"""Insight engine entry points. Signatures are FROZEN since Phase 0; Stream D owns the implementation.

Routers call these with the stats object their own analytics produced (the matching `schemas` model); the engine
never reads raw JSON. Thresholds come from `thresholds.py`, reference distributions from `baselines.py` (computed once
from the whole dataset), and the rules live in `rules_*.py`. Every insight carries its evidence and a low-sample flag.
`for_map` takes an optional `store` (the one the profile was built from) to find the blind-spot zones.
"""
from __future__ import annotations

from ..data.store import Store
from ..schemas.common import Insight
from ..schemas.map import MapProfile
from ..schemas.match import MatchReport
from ..schemas.player import PlayerProfile
from ..schemas.team import TeamProfile
from . import rules_map, rules_match, rules_player, rules_team
from .baselines import Baselines, get_baselines


def for_player(stats: PlayerProfile, base: Baselines | None = None) -> list[Insight]:
    """Strengths, weaknesses and training tips for one player."""
    return rules_player.for_player(stats, base or get_baselines())


def for_team(stats: TeamProfile, base: Baselines | None = None) -> list[Insight]:
    """Strengths, weaknesses and improvement suggestions for one team."""
    return rules_team.for_team(stats, base or get_baselines())


def for_match(report: MatchReport) -> tuple[list[Insight], list[Insight]]:
    """(insights for team A, insights for team B), evidence taken from this match only."""
    return rules_match.for_match(report)


def for_map(stats: MapProfile, store: Store | None = None) -> list[Insight]:
    """Map-level strategy insights (side bias, site tendencies, blind spots)."""
    return rules_map.for_map(stats, store)
