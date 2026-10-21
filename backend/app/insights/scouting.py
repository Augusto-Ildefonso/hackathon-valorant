"""Scouting report: facts about the two rosters, used to pick plays and to assign roles to named players. Owner: Stream D.

Layer 1 of the Action Plan (see the plan, "three layers"). Everything here is deterministic and comes from the Store:
per-player profiles (on the plan's map when the player has enough rounds there, otherwise overall), role scores and the
most played agent. Players are judged against the dataset distributions in `baselines.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..analytics.roles import role_model
from ..data.catalog import get_catalog
from ..data.store import Store
from ..metrics import player_table
from ..schemas.common import AgentRef
from . import thresholds as T
from .agents_meta import agent_class
from .baselines import Baselines, get_baselines
from .core import f_num, f_pct, judge


@dataclass
class PlayerScout:
    puuid: str
    riot_id: str
    scope: str  # "map" when the stats come from this map, "overall" otherwise
    rounds: int
    agent: AgentRef | None
    agent_class: str | None
    kd: float | None
    adr: float | None
    hs_pct: float | None  # 0..100
    opening_win: float | None  # 0..100
    opening_n: int
    first_death_rate: float | None  # 0..100
    trade_share: float | None  # 0..100
    deaths: int
    role_scores: dict[str, float] = field(default_factory=dict)
    flags: dict[str, str] = field(default_factory=dict)  # metric -> "strong" | "weak" (vs the qualified population)

    @property
    def name(self) -> str:
        return self.riot_id.split("#")[0]


_PT_CACHE: dict[int, pd.DataFrame] = {}


def overall_player_table(full: Store) -> pd.DataFrame:
    key = id(full)
    if key not in _PT_CACHE:
        _PT_CACHE.clear()
        _PT_CACHE[key] = player_table(full)
    return _PT_CACHE[key]


def roster_of(full: Store, team: str, size: int = 5) -> list[str]:
    """Players of the team's most recent match (the lineup a coach would prepare for)."""
    mp = full.match_players[full.match_players.team_name == team].merge(
        full.matches[["match_id", "game_start_ms"]], on="match_id")
    if mp.empty:
        return []
    last = mp.sort_values("game_start_ms").match_id.iloc[-1]
    return list(mp[mp.match_id == last].puuid)[:size]


def _agent_of(full: Store, team: str, puuid: str, map_name: str | None) -> AgentRef | None:
    mp = full.match_players[(full.match_players.puuid == puuid) & (full.match_players.team_name == team)
                            & full.match_players.agent_id.notna()]
    on_map = mp.merge(full.matches[["match_id", "map_name"]], on="match_id")
    on_map = on_map[on_map.map_name == map_name] if map_name else on_map.iloc[0:0]
    pool = on_map if len(on_map) else mp
    if pool.empty:
        return None
    return get_catalog().agent(pool.agent_id.value_counts().index[0])


def scout_team(full: Store, team: str, map_name: str, base: Baselines | None = None) -> list[PlayerScout]:
    base = base or get_baselines(full)
    roster = roster_of(full, team)
    if not roster:
        return []
    team_map = full.matches[((full.matches.team_a == team) | (full.matches.team_b == team)) & (full.matches.map_name == map_name)]
    on_map = player_table(full.subset(team_map.match_id)) if len(team_map) else None
    overall = overall_player_table(full)
    model = role_model(full)
    out: list[PlayerScout] = []
    for puuid in roster:
        row, scope = None, "overall"
        if on_map is not None and puuid in on_map.index and on_map.loc[puuid, "rounds"] >= T.MIN_PLAYER_ROUNDS:
            row, scope = on_map.loc[puuid], "map"
        elif puuid in overall.index:
            row = overall.loc[puuid]
        if row is None:
            continue
        rounds = int(row.rounds)
        duels = int(row.first_kills + row.first_deaths)
        agent = _agent_of(full, team, puuid, map_name)
        s = PlayerScout(
            puuid=puuid, riot_id=str(row.riot_id), scope=scope, rounds=rounds, agent=agent,
            agent_class=agent_class(agent.name if agent else None),
            kd=float(row.kd), adr=float(row.adr), hs_pct=None if pd.isna(row.hs_pct) else float(row.hs_pct) * 100,
            opening_win=None if pd.isna(row.opening_win_pct) or duels < T.MIN_OPENING_DUELS else float(row.opening_win_pct) * 100,
            opening_n=duels, first_death_rate=float(row.first_deaths) / max(rounds, 1) * 100,
            trade_share=float(row.traded_deaths) / row.deaths * 100 if row.deaths >= 20 else None, deaths=int(row.deaths),
            role_scores=({r: float(model.scores.loc[puuid, r]) for r in model.scores.columns} if puuid in model.scores.index else {}))
        pl = base.players
        for key, val, better in (("kd", s.kd, True), ("adr", s.adr, True), ("hs_pct", s.hs_pct, True),
                                 ("opening_win_pct", s.opening_win, True), ("first_death_rate", s.first_death_rate, False),
                                 ("trade_share", s.trade_share, True)):
            j = judge(val, pl.get(key), better)
            if j:
                s.flags[key] = j
        out.append(s)
    return out


def assign_roles(players: list[PlayerScout], side: str, base: Baselines | None = None) -> list[tuple[PlayerScout, str, str]]:
    """(player, role, reason) for every roster slot. The role goes to the player whose own numbers fit it best:
    attack = entry (best opening win %), support (best trader), lurker (role score); defense = anchors (role score),
    support (best trader); the rest are flex. Reasons quote the numbers that made the choice."""
    left = list(players)
    out: list[tuple[PlayerScout, str, str]] = []

    def take(pred_key, role: str, reason) -> None:
        cands = [p for p in left if pred_key(p) is not None]
        if not cands:
            return
        best = max(cands, key=pred_key)
        left.remove(best)
        out.append((best, role, reason(best)))

    pl = (base or get_baselines()).players

    def med(key: str) -> str:
        d = pl.get(key)
        return f" (mediana {f_pct(d.median)})" if d else ""

    if side == "attack":
        take(lambda p: p.opening_win if p.opening_win is not None else None, "entry",
             lambda p: f"{p.name} abre o ataque: vence {f_pct(p.opening_win)} dos duelos de abertura{med('opening_win_pct')}, n = {p.opening_n}.")
        take(lambda p: p.trade_share, "support",
             lambda p: f"{p.name} segue o entry e troca o primeiro abate: {f_pct(p.trade_share)} das suas mortes foram trocadas{med('trade_share')}.")
        take(lambda p: p.role_scores.get("lurker"), "lurker",
             lambda p: f"{p.name} joga de lurker, o perfil mais forte do elenco nessa função (pontuação {f_num(p.role_scores['lurker'])}).")
    else:
        take(lambda p: p.role_scores.get("anchor"), "anchor",
             lambda p: f"{p.name} ancora o site, o melhor perfil de anchor do elenco (pontuação {f_num(p.role_scores['anchor'])}).")
        take(lambda p: p.trade_share, "support",
             lambda p: f"{p.name} cobre o anchor e troca o primeiro contato: {f_pct(p.trade_share)} das suas mortes foram trocadas{med('trade_share')}.")
        take(lambda p: p.role_scores.get("anchor"), "anchor",
             lambda p: f"{p.name} é o segundo perfil de anchor do elenco (pontuação {f_num(p.role_scores['anchor'])}).")
    for p in left:
        out.append((p, "flex", f"{p.name} completa o time como flex (sem destaque claro nas funções do round)."))
    return out
