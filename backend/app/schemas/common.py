"""Shared contract types. FROZEN after Phase 0: change only through a PR touching `contract/` + `schemas/`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Side = Literal["attack", "defense"]
InsightKind = Literal["strength", "weakness", "tip", "strategy"]
RoundType = Literal["pistol", "eco", "semi_eco", "force", "full_buy"]
RoleName = Literal["entry", "lurker", "igl", "support", "anchor", "flex"]
Site = Literal["A", "B", "C"]


class Model(BaseModel):
    """Base for every response model: unknown fields are a contract error."""

    model_config = ConfigDict(extra="forbid")


class Point(Model):
    """Position already normalized to the minimap, 0..1 (x right, y down)."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class Stat(Model):
    """A number that always travels with its sample size (see "sample-size honesty")."""

    value: float | None
    sample_size: int
    low_sample: bool = False


class Evidence(Model):
    metric: str
    value: float
    baseline: float | None = None
    sample_size: int
    unit: str | None = None


class Insight(Model):
    id: str
    kind: InsightKind
    text_pt: str
    evidence: Evidence
    low_sample: bool = False


class AgentRef(Model):
    id: str
    name: str | None = None  # None => unknown agent ("Agente desconhecido")
    name_inferred: bool = False
    icon_url: str | None = None


class WeaponRef(Model):
    id: str
    name: str | None = None  # None => unknown weapon ("Arma desconhecida")
    name_inferred: bool = False
    icon_url: str | None = None


class MapRef(Model):
    codename: str  # e.g. "Jam"
    name: str  # public name, e.g. "Lotus"
    has_minimap: bool
    minimap_url: str | None = None
    thumb_url: str | None = None  # small wide banner for lists (None => no image in the catalog)


class TeamRef(Model):
    name: str


class PlayerRef(Model):
    puuid: str
    riot_id: str  # "gameName#tagLine"


class MatchSide(Model):
    team: TeamRef
    score: int


class MatchListItem(Model):
    match_id: str
    tournament: str
    phase: str | None = None
    date: str  # ISO date (YYYY-MM-DD)
    map: MapRef
    team_a: MatchSide
    team_b: MatchSide
    winner: Literal["a", "b"]
    duration_ms: int


class Signal(Model):
    name: str
    value: float
    sample_size: int


class RoleScore(Model):
    role: RoleName
    score: float  # 0..1
    confidence: float  # 0..1
    inferred: bool = False  # True for IGL
    signals: list[Signal] = []
