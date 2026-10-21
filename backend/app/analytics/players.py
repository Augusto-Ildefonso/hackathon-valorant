"""Player Profile builder. Owner: Stream B. Uses only `Store` + `app.metrics` (never raw JSON)."""
from __future__ import annotations

import pandas as pd

from ..data.catalog import get_catalog
from ..data.store import Store
from ..metrics import make_stat, player_table, team_rounds
from ..schemas.common import AgentRef, PlayerRef, TeamRef
from ..schemas.player import (AgentPerformance, MapPerformance, Multikills, PlayerProfile, PlayerStats,
                              WeaponPerformance)
from .roles import role_model

KEY = ["match_id", "round_num"]
MIN_WEAPON_ROUNDS = 5
MAX_WEAPON_ROWS = 20


def _agents(store: Store, puuid: str) -> list[AgentPerformance]:
    cat = get_catalog()
    mp = store.match_players[store.match_players.puuid == puuid].merge(
        store.matches[["match_id", "winner_team"]], on="match_id")
    rps = store.round_player_stats[store.round_player_stats.puuid == puuid]
    dmg = rps.groupby("match_id").agg(damage=("damage_dealt", "sum"), rounds=("round_num", "size"))
    mp = mp.join(dmg, on="match_id")
    mp["won"] = mp.team_name == mp.winner_team
    out = []
    for aid, g in mp.groupby("agent_id", dropna=False):
        n = len(g)
        out.append((n, AgentPerformance(
            agent=cat.agent(aid) or AgentRef(id="unknown"), matches=n,
            kd=make_stat(g.kills.sum() / max(g.deaths.sum(), 1), int(g.rounds.sum()), "rounds"),
            adr=make_stat(g.damage.sum() / max(g.rounds.sum(), 1), int(g.rounds.sum()), "rounds"),
            win_rate=make_stat(g.won.mean(), n, "matches"))))
    return [a for _, a in sorted(out, key=lambda t: -t[0])]


def _weapons(store: Store, puuid: str) -> list[WeaponPerformance]:
    """Performance per (weapon bought, buy type). `kills`/`kd` count kills and deaths in rounds with that purchase."""
    cat = get_catalog()
    tr = team_rounds(store)[KEY + ["team_name", "round_type", "won"]]
    rps = store.round_player_stats[store.round_player_stats.puuid == puuid]
    rps = rps[rps.weapon_id.notna()].merge(tr, on=KEY + ["team_name"])
    deaths = store.kills[store.kills.victim == puuid][KEY].assign(died=1).drop_duplicates()
    rps = rps.merge(deaths, on=KEY, how="left").fillna({"died": 0})
    out = []
    for (wid, rtype), g in rps.groupby(["weapon_id", "round_type"]):
        n = len(g)
        if n < MIN_WEAPON_ROUNDS:
            continue
        shots = g[["headshots", "bodyshots", "legshots"]].sum().sum()
        out.append(WeaponPerformance(
            weapon=cat.weapon(wid), buy_type=rtype, rounds=n, round_win_rate=make_stat(g.won.mean(), n),
            kills=int(g.kills_n.sum()), kd=make_stat(g.kills_n.sum() / max(g.died.sum(), 1), n),
            hs_pct=make_stat(g.headshots.sum() / shots if shots else None, int(shots), "rounds"),
            damage_per_round=make_stat(g.damage_dealt.mean(), n)))
    return sorted(out, key=lambda w: -w.rounds)[:MAX_WEAPON_ROWS]


def _by_map(store: Store, puuid: str) -> list[MapPerformance]:
    cat = get_catalog()
    mp = store.match_players[store.match_players.puuid == puuid].merge(store.matches[["match_id", "map_name"]], on="match_id")
    out = []
    for name, g in mp.groupby("map_name"):
        out.append(MapPerformance(map=cat.map_ref(name), matches=len(g), kills=int(g.kills.sum()), deaths=int(g.deaths.sum()),
                                  kd=make_stat(g.kills.sum() / max(g.deaths.sum(), 1), len(g), "matches")))
    return sorted(out, key=lambda m: -m.matches)


def player_exists(store: Store, puuid: str) -> bool:
    return bool((store.match_players.puuid == puuid).any())


def player_profile(store: Store, puuid: str, full_store: Store | None = None) -> PlayerProfile:
    """Profile of `puuid` over `store` (already filtered by the caller). Roles use the whole dataset (`full_store`)."""
    mp = store.match_players[store.match_players.puuid == puuid]
    sub = store.subset(mp.match_id)
    row = player_table(sub).loc[puuid]
    n_rounds = int(row.rounds)
    stats = PlayerStats(
        matches=int(row.matches), rounds=n_rounds, kills=int(row.kills), deaths=int(row.deaths), assists=int(row.assists),
        kd=make_stat(row.kd, n_rounds), adr=make_stat(row.adr, n_rounds),
        hs_pct=make_stat(row.hs_pct, n_rounds), first_kill_rate=make_stat(row.first_kills / max(n_rounds, 1), n_rounds),
        first_death_rate=make_stat(row.first_deaths / max(n_rounds, 1), n_rounds),
        opening_duel_win_pct=make_stat(row.opening_win_pct, int(row.first_kills + row.first_deaths), "events"),
        clutches=int(row.clutches), multikills=Multikills(k2=int(row.k2), k3=int(row.k3), k4=int(row.k4), k5=int(row.k5)))
    agents = _agents(sub, puuid)
    teams = (mp.merge(store.matches[["match_id", "game_start_ms"]], on="match_id")
             .sort_values("game_start_ms", ascending=False).team_name.drop_duplicates())
    riot_id = mp.sort_values("match_id").riot_id.iloc[-1]
    return PlayerProfile(
        player=PlayerRef(puuid=puuid, riot_id=riot_id), teams=[TeamRef(name=t) for t in teams],
        favorite_agent=agents[0].agent if agents else None,  # most played (may be an unknown, newer agent)
        roles=role_model(full_store or store).roles_for(puuid), stats=stats, weapons=_weapons(sub, puuid),
        by_map=_by_map(sub, puuid), agents=agents, insights=[])
