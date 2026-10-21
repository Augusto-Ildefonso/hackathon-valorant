"""Action Plan: POST /api/plan (round-by-round plan for the whole match)."""
from __future__ import annotations

from typing import Literal

from .common import AgentRef, Insight, MapRef, Model, Point, RoundType, Side, Site, Stat, TeamRef, WeaponRef


class PlanRequest(Model):
    team_a: str
    team_b: str
    map: str  # public map name, e.g. "Ascent"
    perspective: Literal["a", "b"] = "a"
    rounds_per_half: int = 12
    starting_side: Side = "attack"  # starting side of the PERSPECTIVE team
    use_llm: bool = False  # additive (Stream D): ask the optional LLM narrator to rewrite the plan text


class AgentRecommendation(Model):
    agent: AgentRef
    role: str | None = None
    reason_pt: str
    evidence: Stat


class OpponentSummary(Model):
    team: TeamRef
    matches_on_map: int
    preferred_site: Site | None = None
    avg_time_to_plant_ms: Stat
    attack_win_rate: Stat
    defense_win_rate: Stat
    pistol_win_rate: Stat
    eco_win_rate: Stat
    insights: list[Insight]


class ProjectedEconomy(Model):
    team_credits: int
    enemy_credits: int
    reasoning_pt: str


class BuyItem(Model):
    role: str  # entry / lurker / support / anchor / flex
    weapon: WeaponRef | None = None
    armor: Literal["none", "light", "heavy"]
    reason_pt: str


class RoundStrategy(Model):
    summary_pt: str
    site: Site | None = None  # target site (attack) or site focus (defense)
    timing: str | None = None  # e.g. "early", "default", "late"
    steps_pt: list[str] = []


class EnemyMove(Model):
    summary_pt: str
    site: Site | None = None
    route: list[Point] = []  # minimap-normalized path for the route map; empty if unknown
    evidence: Stat


class Contingency(Model):
    """What changes for this round depending on the outcome of the previous one."""

    if_previous_won: "ContingencyOutcome"
    if_previous_lost: "ContingencyOutcome"


class ContingencyOutcome(Model):
    round_type: RoundType
    summary_pt: str


class RoundPlan(Model):
    number: int  # 1-based
    half: Literal[1, 2]
    side: Side  # side of the perspective team in this round
    round_type: RoundType
    base_scenario_result: Literal["win", "loss"]  # most probable outcome used to project the next round
    win_probability: Stat
    projected_economy: ProjectedEconomy
    buy: list[BuyItem]
    strategy: RoundStrategy
    enemy_weak_points: list[Insight]
    enemy_probable_strategy: EnemyMove
    contingency: Contingency
    insights: list[Insight] = []


class PlanResponse(Model):
    team_a: TeamRef
    team_b: TeamRef
    perspective: Literal["a", "b"]
    map: MapRef
    rounds_per_half: int
    starting_side: Side
    agents: list[AgentRecommendation]
    opponent: OpponentSummary
    rounds: list[RoundPlan]
    narrative_pt: str | None = None  # optional LLM polish; None when disabled
    text_source: Literal["rules", "llm"] = "rules"  # additive (Stream D): who wrote the round texts
    notes_pt: list[str] = []  # additive (Stream D): data caveats shown with the plan (fallbacks, small samples)


class PlanCapabilities(Model):
    """GET /api/plan/capabilities (additive, Stream D)."""

    llm: bool  # True when the optional narrator is configured (env flag + API key)
    model: str | None = None


Contingency.model_rebuild()
