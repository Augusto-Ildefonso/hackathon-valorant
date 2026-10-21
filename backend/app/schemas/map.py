"""Map Profile: GET /api/maps, /api/maps/{name}, /api/maps/{name}/heatmap."""
from __future__ import annotations

from typing import Literal

from .common import AgentRef, Insight, MapRef, Model, Point, Side, Site, Stat, WeaponRef


class MapListItem(Model):
    map: MapRef
    matches: int
    rounds: int
    attack_win_rate: Stat


class MapListResponse(Model):
    items: list[MapListItem]


class UsageRow(Model):
    id: str
    name: str | None = None
    icon_url: str | None = None
    picks: int
    share: float  # 0..1


class SiteStats(Model):
    site: Site
    plants: int
    plant_rate: Stat  # share of attack rounds with a plant on this site
    defuse_rate: Stat
    retake_rate: Stat


class PlantPoint(Model):
    site: Site
    point: Point


class MapProfile(Model):
    map: MapRef
    matches: int
    rounds: int
    attack_win_rate: Stat
    defense_win_rate: Stat
    classification: Literal["attack", "defense", "balanced"]
    top_agents: list[UsageRow]
    top_weapons: list[UsageRow]
    sites: list[SiteStats]
    plants: list[PlantPoint]  # empty when has_minimap is false
    insights: list[Insight] = []
    insights_source: Literal["rules", "llm"] = "rules"  # additive (Stream D)


class HeatLayer(Model):
    """Square grid, `grid[row][col]`, row 0 = top of the minimap. Values normalized 0..1."""

    grid: list[list[float]]
    max_count: int  # raw count behind the normalization (for tooltips)


class HeatmapResponse(Model):
    map: MapRef
    side: Side | Literal["both"]
    grid_size: int  # e.g. 64
    has_data: bool  # False when the map has no minimap
    kills: HeatLayer | None = None
    deaths: HeatLayer | None = None
    danger: HeatLayer | None = None  # blind spot (a): deaths far exceed kills
    uncovered: HeatLayer | None = None  # blind spot (b): little coverage, enemies still score from there
    plants: list[PlantPoint] = []
    agents_used: list[AgentRef] = []
    weapons_used: list[WeaponRef] = []
