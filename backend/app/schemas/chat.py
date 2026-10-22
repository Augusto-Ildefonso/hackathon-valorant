"""Chat: POST /api/chat (additive, Stream G). The chat only triggers the existing engines and presents their output as typed blocks."""
from __future__ import annotations

from typing import Literal

from .common import Insight, Model
from .plan import PlanRequest

Intent = Literal["player", "team", "map", "match", "plan", "tournament", "leaderboard", "help", "unknown"]


class ChatContext(Model):
    """Entities resolved in the previous answer, sent back by the client so follow-ups work without server memory."""

    player_puuid: str | None = None
    team: str | None = None
    team_b: str | None = None
    map: str | None = None
    tournament: str | None = None


class ChatRequest(Model):
    message: str
    context: ChatContext | None = None


class StatItem(Model):
    label: str
    value: str  # already formatted (pt-BR)
    sample_size: int | None = None
    low_sample: bool = False


class TextBlock(Model):
    type: Literal["text"] = "text"
    text: str


class WarningBlock(Model):
    type: Literal["warning"] = "warning"
    text: str


class StatsBlock(Model):
    type: Literal["stats"] = "stats"
    title: str | None = None
    items: list[StatItem]


class InsightsBlock(Model):
    type: Literal["insights"] = "insights"
    title: str
    items: list[Insight]


class TableBlock(Model):
    type: Literal["table"] = "table"
    title: str | None = None
    columns: list[str]
    rows: list[list[str]]


class ChoiceOption(Model):
    label: str
    send: str  # text sent as the next message when the option is clicked


class ChoicesBlock(Model):
    type: Literal["choices"] = "choices"
    prompt: str
    options: list[ChoiceOption]


class PlanRoundSummary(Model):
    number: int
    side: str
    round_type: str
    summary_pt: str
    buy_pt: str


class PlanSummaryBlock(Model):
    type: Literal["plan_summary"] = "plan_summary"
    title: str
    rounds: list[PlanRoundSummary]
    weak_points: list[Insight]
    pdf_request: PlanRequest  # the client posts this to /api/plan/report for the printable dossier


Block = TextBlock | WarningBlock | StatsBlock | InsightsBlock | TableBlock | ChoicesBlock | PlanSummaryBlock


class DashboardLink(Model):
    label: str = "Ver no dashboard"
    path: str  # app route with the query already filled in


class ChatResponse(Model):
    intent: Intent
    source: Literal["llm", "rules"] = "rules"  # who understood the question
    context: ChatContext
    blocks: list[Block]
    dashboard: DashboardLink | None = None
    suggestions: list[str] | None = None  # optional follow-up shortcuts
    note: str | None = None
