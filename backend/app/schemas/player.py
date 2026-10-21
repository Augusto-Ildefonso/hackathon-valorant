"""Player Profile: GET /api/players/{puuid}."""
from __future__ import annotations

from .common import (AgentRef, Insight, MapRef, Model, PlayerRef, RoleScore,
                     RoundType, Stat, TeamRef, WeaponRef)


class Multikills(Model):
    k2: int
    k3: int
    k4: int
    k5: int


class PlayerStats(Model):
    matches: int
    rounds: int
    kills: int
    deaths: int
    assists: int
    kd: Stat
    adr: Stat
    hs_pct: Stat
    first_kill_rate: Stat  # first kills / rounds played
    first_death_rate: Stat
    opening_duel_win_pct: Stat
    clutches: int
    multikills: Multikills


class WeaponPerformance(Model):
    weapon: WeaponRef
    buy_type: RoundType | None = None  # None => aggregated over all buy types
    rounds: int
    round_win_rate: Stat
    kills: int
    kd: Stat
    hs_pct: Stat
    damage_per_round: Stat


class MapPerformance(Model):
    map: MapRef
    matches: int
    kills: int
    deaths: int
    kd: Stat


class AgentPerformance(Model):
    agent: AgentRef
    matches: int
    kd: Stat
    adr: Stat
    win_rate: Stat


class PlayerProfile(Model):
    player: PlayerRef
    teams: list[TeamRef]
    favorite_agent: AgentRef | None = None
    roles: list[RoleScore]  # top-2, most confident first
    stats: PlayerStats
    weapons: list[WeaponPerformance]
    by_map: list[MapPerformance]
    agents: list[AgentPerformance]
    insights: list[Insight]  # strengths / weaknesses / tips, split by `kind`
