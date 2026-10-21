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


# ---- mode-aware wrappers used by the routers -------------------------------------------------------------------------
# `mode="llm"` asks the LLM insight mode (llm_insights); when it is off, fails or returns nothing, the rule-based
# insights are returned instead and the source says "rules", so the UI and the notes never claim AI text that is not there.
def _llm_on(mode: str) -> bool:
    from . import llm

    return mode == "llm" and llm.enabled()


def player_insights(stats: PlayerProfile, mode: str = "rules") -> tuple[list[Insight], str]:
    if _llm_on(mode):
        from . import llm_insights

        run = llm_insights.for_player(stats)
        if run.insights:
            return run.insights, "llm"
    return for_player(stats), "rules"


def team_insights(stats: TeamProfile, mode: str = "rules") -> tuple[list[Insight], str]:
    if _llm_on(mode):
        from . import llm_insights

        run = llm_insights.for_team(stats)
        if run.insights:
            return run.insights, "llm"
    return for_team(stats), "rules"


def map_insights(stats: MapProfile, store: Store | None = None, mode: str = "rules") -> tuple[list[Insight], str]:
    if _llm_on(mode):
        from . import llm_insights

        run = llm_insights.for_map(stats, store)
        if run.insights:
            return run.insights, "llm"
    return for_map(stats, store), "rules"


def match_insights(report: MatchReport, mode: str = "rules") -> tuple[list[Insight], list[Insight], str]:
    if _llm_on(mode):
        from . import llm_insights

        run = llm_insights.for_match(report)
        if run.ok:
            return run.by_team.get("a", []), run.by_team.get("b", []), "llm"
    a, b = for_match(report)
    return a, b, "rules"
