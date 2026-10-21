"""Team Profile: GET /api/teams and GET /api/teams/{name}."""
from __future__ import annotations

from .common import (Insight, MapRef, MatchListItem, Model, PlayerRef, RoleName,
                     RoleScore, RoundType, Site, Stat, TeamRef)


class TeamListItem(Model):
    team: TeamRef
    matches: int
    win_rate: Stat
    round_win_rate: Stat
    last_match_date: str


class TeamListResponse(Model):
    items: list[TeamListItem]


class RosterMember(Model):
    player: PlayerRef
    matches: int
    top_role: RoleScore | None = None


class TeamRecord(Model):
    matches: int
    series: int
    wins: int
    losses: int
    round_win_rate: Stat
    attack_win_rate: Stat
    defense_win_rate: Stat


class TrendPoint(Model):
    match_id: str
    date: str
    round_diff: int  # rounds won - rounds lost in that map


class TeamMapPerformance(Model):
    map: MapRef
    matches: int
    win_rate: Stat
    attack_win_rate: Stat
    defense_win_rate: Stat


class TeamEconomy(Model):
    win_rate_by_round_type: dict[RoundType, Stat]
    pistol_win_rate: Stat
    plant_site_preference: dict[Site, Stat]  # share of plants per site
    avg_time_to_plant_ms: Stat
    post_plant_win_rate: Stat
    retake_success_rate: Stat


class RoleCount(Model):
    role: RoleName
    count: int


class TeamProfile(Model):
    team: TeamRef
    roster: list[RosterMember]
    record: TeamRecord
    matches: list[MatchListItem]
    trend: list[TrendPoint]
    by_map: list[TeamMapPerformance]
    economy: TeamEconomy
    role_composition: list[RoleCount]
    insights: list[Insight]
