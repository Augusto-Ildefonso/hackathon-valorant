"""Match Report: GET /api/matches, /api/matches/{id}, /api/matches/{id}/kills."""
from __future__ import annotations

from typing import Literal

from .common import (AgentRef, Insight, MapRef, MatchListItem, MatchSide, Model,
                     Point, PlayerRef, RoundType, Side, Site, Stat, TeamRef, WeaponRef)


class MatchListResponse(Model):
    items: list[MatchListItem]
    total: int


class RoundEconomy(Model):
    team_a_type: RoundType
    team_b_type: RoundType
    team_a_loadout: int
    team_b_loadout: int


class RoundSummary(Model):
    number: int  # 1-based for display
    half: Literal[1, 2, "ot"]
    winner: Literal["a", "b"]
    team_a_side: Side
    result: Literal["eliminated", "defused", "detonated", "timer"]
    ceremony: str | None = None  # Ace, Clutch, Flawless, Thrifty, TeamAce, Closer
    plant_site: Site | None = None
    planted: bool
    defused: bool
    economy: RoundEconomy


class ScoreboardRow(Model):
    player: PlayerRef
    team: Literal["a", "b"]
    agent: AgentRef
    kills: int
    deaths: int
    assists: int
    adr: Stat
    hs_pct: Stat
    first_kills: int
    score: int


class MatchReport(Model):
    match_id: str
    tournament: str
    phase: str | None = None
    date: str
    map: MapRef
    duration_ms: int
    team_a: MatchSide
    team_b: MatchSide
    winner: Literal["a", "b"]
    mvp: PlayerRef | None = None
    rounds: list[RoundSummary]
    scoreboard: list[ScoreboardRow]
    insights_a: list[Insight]
    insights_b: list[Insight]
    insights_source: Literal["rules", "llm"] = "rules"  # additive (Stream D)


class ReplayPlayer(Model):
    puuid: str
    riot_id: str
    team: Literal["a", "b"]
    agent: AgentRef | None = None
    pos: Point | None = None  # None when the position is outside the playable area
    view_radians: float | None = None


class KillEvent(Model):
    id: str  # "<round>-<index>"
    round: int  # 1-based
    time_ms: int  # since round start
    killer: ReplayPlayer
    victim: ReplayPlayer
    assistants: list[PlayerRef] = []
    weapon: WeaponRef | None = None
    damage_type: Literal["weapon", "ability", "bomb", "fall", "melee", "crush", "unknown"]
    headshot: bool | None = None  # None when not derivable
    others_alive: list[ReplayPlayer]  # everyone else alive at that moment


class KillsResponse(Model):
    match_id: str
    map: MapRef
    has_minimap: bool
    kills: list[KillEvent]
    teams: dict[Literal["a", "b"], TeamRef]
