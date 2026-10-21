"""Home screen: /api/meta, /api/search, /api/leaderboards."""
from __future__ import annotations

from typing import Literal

from .common import MapRef, Model, PlayerRef, TeamRef


class Kpis(Model):
    matches: int
    rounds: int
    kills: int
    players: int
    teams: int
    tournaments: int


class TournamentInfo(Model):
    id: str  # e.g. "RUSH2"
    name: str  # e.g. "Rush Series Esquenta 2"
    phases: list[str] = []  # e.g. ["Classificatória 1"]
    matches: int


class MetaResponse(Model):
    kpis: Kpis
    date_from: str  # ISO date
    date_to: str
    tournaments: list[TournamentInfo]
    maps: list[MapRef]


class PlayerHit(Model):
    player: PlayerRef
    team: TeamRef | None = None
    matches: int


class TeamHit(Model):
    team: TeamRef
    matches: int


class MapHit(Model):
    map: MapRef


class SearchResponse(Model):
    query: str
    players: list[PlayerHit]
    teams: list[TeamHit]
    maps: list[MapHit]


class PlayerLeaderRow(Model):
    rank: int
    player: PlayerRef
    team: TeamRef | None = None
    value: float
    matches: int
    rounds: int
    low_sample: bool = False
    # the other columns shown next to the ranked metric (additive in Stream E)
    kd: float | None = None
    adr: float | None = None
    hs_pct: float | None = None
    first_kills: int | None = None


class TeamLeaderRow(Model):
    rank: int
    team: TeamRef
    value: float
    matches: int
    rounds: int
    low_sample: bool = False
    wins: int | None = None
    losses: int | None = None


PlayerMetric = Literal["kd", "adr", "hs_pct", "first_kills"]
TeamMetric = Literal["win_rate", "round_win_rate"]


class LeaderboardsResponse(Model):
    players: dict[PlayerMetric, list[PlayerLeaderRow]]
    teams: dict[TeamMetric, list[TeamLeaderRow]]
