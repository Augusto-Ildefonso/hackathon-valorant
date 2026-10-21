"""In-memory store: the normalized tables and the lookups analytics code is allowed to use.

Column names and dtypes are documented in `SCHEMA.md` (the source of truth). Stream A fills this from `data/`
(`loader.py`); until then `tests/fixtures/mini_store.py` builds a small store from 3 real files.
Analytics modules (B, C, D) must depend only on this class, never on the raw JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

Side = str  # "attack" | "defense"


@dataclass
class Store:
    matches: pd.DataFrame
    match_players: pd.DataFrame
    rounds: pd.DataFrame
    round_player_stats: pd.DataFrame
    kills: pd.DataFrame
    damage: pd.DataFrame
    skipped: list[dict] = field(default_factory=list)  # files the loader could not map to teams (logged, never fatal)

    # ---- filtering ---------------------------------------------------------------------------------------------
    def subset(self, match_ids) -> "Store":
        ids = set(match_ids)
        return Store(
            *(getattr(self, t)[getattr(self, t).match_id.isin(ids)] for t in
              ("matches", "match_players", "rounds", "round_player_stats", "kills", "damage")),
            skipped=self.skipped,
        )

    def where(self, tournament: str | None = None, map_name: str | None = None, date_from: str | None = None,
              date_to: str | None = None, team: str | None = None) -> "Store":
        """Global filters (tournament code or folder name, public map name, ISO dates, team name). No-op if all None."""
        m = self.matches
        if tournament:
            m = m[(m.tournament_code == tournament) | (m.tournament == tournament)]
        if map_name:
            m = m[m.map_name == map_name]
        if date_from:
            m = m[m.date >= date_from]
        if date_to:
            m = m[m.date <= date_to]
        if team:
            m = m[(m.team_a == team) | (m.team_b == team)]
        return self if len(m) == len(self.matches) else self.subset(m.match_id)

    # ---- lookups -----------------------------------------------------------------------------------------------
    def team_of(self, match_id: str, puuid: str) -> str | None:
        """Team name of a player in a match (None for unknown/observer)."""
        mp = self.match_players
        row = mp[(mp.match_id == match_id) & (mp.puuid == puuid)]
        return None if row.empty else row.iloc[0].team_name

    def color_of(self, match_id: str, team_name: str) -> str | None:
        """'Red' or 'Blue' for a team name in a match."""
        m = self.matches[self.matches.match_id == match_id]
        if m.empty:
            return None
        m = m.iloc[0]
        return "Red" if m.red_team == team_name else "Blue" if m.blue_team == team_name else None

    def side(self, match_id: str, round_num: int, team_name: str) -> Side | None:
        """'attack' or 'defense' for a team in a round (0-based `round_num`). Halftime/overtime already resolved."""
        r = self.rounds[(self.rounds.match_id == match_id) & (self.rounds.round_num == round_num)]
        if r.empty:
            return None
        r = r.iloc[0]
        if team_name == r.attacker_team:
            return "attack"
        if team_name == r.defender_team:
            return "defense"
        return None

    def players_of(self, match_id: str, team_name: str) -> pd.DataFrame:
        mp = self.match_players
        return mp[(mp.match_id == match_id) & (mp.team_name == team_name)]

    def matches_of_team(self, team_name: str) -> pd.DataFrame:
        m = self.matches
        return m[(m.team_a == team_name) | (m.team_b == team_name)]

    def matches_of_player(self, puuid: str) -> pd.DataFrame:
        ids = self.match_players.loc[self.match_players.puuid == puuid, "match_id"]
        return self.matches[self.matches.match_id.isin(ids)]
