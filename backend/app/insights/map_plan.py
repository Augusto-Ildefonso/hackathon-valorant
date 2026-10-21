"""Minimap drawing of a round's plan: player arrows, holds, retakes, enemy route and zones. Owner: Stream D.

Everything is a typical path computed from real position snapshots (`kills.player_locations`: every living player at
each kill moment), so a path is a coarse centroid trace per time bucket (0-20 / 20-40 / 40+ s), never a prescription
or a per-second trajectory. Attack arrows use the team's own rounds on the map that planted on the target site (all of
its attack rounds on the map when those are too few, and the note says so). Evidence carries the snapshot count.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.coords import to_minimap, to_minimap_arrays
from ..data.store import Store
from ..schemas.common import Point, Stat
from ..schemas.map import HeatLayer, PlantPoint
from ..schemas.plan import MapPlan, PlanMarker, PlanRoute, PlanZone
from .core import f_pct
from .rules_map import _events_and_layers, zone_name
from .scouting import PlayerScout
from .zones import find_zones

BUCKETS_S = ((0, 20), (20, 40), (40, 1000))
MIN_BUCKET_SNAPS = 3
MIN_ROUNDS = 5
HOLD_WINDOW_S = 25
LOW_SNAPS = 20


def plant_points(full: Store, map_name: str) -> dict[str, tuple[float, float]]:
    r = full.rounds.merge(full.matches[["match_id", "map_name"]], on="match_id")
    r = r[(r.map_name == map_name) & r.planter.notna()]
    out = {}
    for site, g in r.groupby("plant_site"):
        p = to_minimap(map_name, float(g.plant_x.mean()), float(g.plant_y.mean()))
        if p is not None:
            out[str(site)] = p
    return out


def _snaps(full: Store, map_name: str, keys: pd.DataFrame, puuids: set[str]) -> pd.DataFrame:
    """Positions of `puuids` at every kill moment of the given (match_id, round_num) rounds: puuid, t (s), u, v."""
    k = full.kills.merge(keys[["match_id", "round_num"]].drop_duplicates(), on=["match_id", "round_num"])
    rows = [(loc["puuid"], t / 1000, loc["x"], loc["y"]) for t, locs in zip(k.time_in_round_ms, k.player_locations)
            for loc in locs if loc["puuid"] in puuids]
    if not rows:
        return pd.DataFrame(columns=["puuid", "t", "u", "v"])
    d = pd.DataFrame(rows, columns=["puuid", "t", "x", "y"])
    u, v = to_minimap_arrays(map_name, d.x.to_numpy(float), d.y.to_numpy(float))
    d["u"], d["v"] = u, v
    return d.dropna(subset=["u", "v"])[["puuid", "t", "u", "v"]]


def _map_rounds(full: Store, map_name: str) -> pd.DataFrame:
    r = full.rounds.merge(full.matches[["match_id", "map_name"]], on="match_id")
    return r[r.map_name == map_name]


def _stat(n: int) -> Stat:
    return Stat(value=None, sample_size=int(n), low_sample=n < LOW_SNAPS)


def _path(d: pd.DataFrame) -> tuple[list[tuple[float, float]], int, int | None, int | None]:
    """Bucket centroids of one player's snapshots -> (points, snapshots used, t0, t1)."""
    pts, used, t_first, t_last = [], 0, None, None
    for lo, hi in BUCKETS_S:
        s = d[(d.t >= lo) & (d.t < hi)]
        if len(s) >= MIN_BUCKET_SNAPS:
            pts.append((float(s.u.mean()), float(s.v.mean())))
            used += len(s)
            t_first = lo if t_first is None else t_first
            t_last = int(min(hi, s.t.max())) if hi < 1000 else int(s.t.mean())
    return pts, used, t_first, t_last


def attack_routes(full: Store, team: str, assigned: list[tuple[PlayerScout, str]], map_name: str, site: str,
                  plants: dict[str, tuple[float, float]]) -> tuple[list[PlanRoute], str | None]:
    r = _map_rounds(full, map_name)
    mine = r[r.attacker_team == team]
    on_site = mine[mine.plant_site == site]
    note = None
    if len(on_site) < MIN_ROUNDS:
        on_site, note = mine, f"Poucos rounds do time plantando no site {site}: os caminhos usam todos os rounds de ataque do time em {map_name}."
    if len(on_site) < MIN_ROUNDS:
        return [], f"O time tem poucos rounds de ataque em {map_name}: sem caminhos por jogador."
    snaps = _snaps(full, map_name, on_site, {p.puuid for p, _ in assigned})
    routes: list[PlanRoute] = []
    for p, role in assigned:
        pts, used, t0, t1 = _path(snaps[snaps.puuid == p.puuid])
        if len(pts) < 1:
            continue
        if site in plants and len(pts) >= 1:
            pts.append(plants[site])
        if len(pts) < 2:
            continue
        routes.append(PlanRoute(
            kind="attack", label=f"{p.name} · {role}", role=role, agent=p.agent, handle=p.name,
            points=[Point(x=min(max(a, 0), 1), y=min(max(b, 0), 1)) for a, b in pts], t0_s=t0, t1_s=t1, evidence=_stat(used)))
    return routes, note


def defense_layout(full: Store, team: str, assigned: list[tuple[PlayerScout, str]], map_name: str, site: str,
                   plants: dict[str, tuple[float, float]]) -> tuple[list[PlanMarker], list[PlanRoute], str | None]:
    r = _map_rounds(full, map_name)
    mine = r[r.defender_team == team]
    if len(mine) < MIN_ROUNDS:
        return [], [], f"O time tem poucos rounds de defesa em {map_name}: sem posições por jogador."
    snaps = _snaps(full, map_name, mine, {p.puuid for p, _ in assigned})
    snaps = snaps[snaps.t < HOLD_WINDOW_S]
    markers, routes = [], []
    for p, role in assigned:
        s = snaps[snaps.puuid == p.puuid]
        if len(s) < MIN_BUCKET_SNAPS + 1:
            continue
        hold = (float(s.u.mean()), float(s.v.mean()))
        markers.append(PlanMarker(point=Point(x=hold[0], y=hold[1]), kind="hold", label=f"{p.name} · {role}", handle=p.name, agent=p.agent))
        if role in ("anchor", "support") and site in plants:
            routes.append(PlanRoute(
                kind="retake", label=f"{p.name} · retake {site}", role=role, agent=p.agent, handle=p.name,
                points=[Point(x=hold[0], y=hold[1]), Point(x=plants[site][0], y=plants[site][1])], t0_s=0, t1_s=None, evidence=_stat(len(s))))
    return markers, routes, None


def enemy_weak_zone(full: Store, enemy: str, map_name: str, enemy_side: str, plants_pts: dict[str, tuple[float, float]]) -> PlanZone | None:
    """Where the enemy loses the opening duel of its rounds on `enemy_side`: the densest blob of its first deaths."""
    r = _map_rounds(full, map_name)
    col = "attacker_team" if enemy_side == "attack" else "defender_team"
    keys = r[r[col] == enemy][["match_id", "round_num"]]
    if keys.empty:
        return None
    k = full.kills.merge(keys, on=["match_id", "round_num"]).sort_values(["match_id", "round_num", "time_in_round_ms", "kill_idx"])
    first = k.groupby(["match_id", "round_num"]).head(1)
    team_of = dict(zip(zip(full.match_players.match_id, full.match_players.puuid), full.match_players.team_name))
    first = first[[team_of.get((m, v)) == enemy for m, v in zip(first.match_id, first.victim)]]
    if len(first) < 8:
        return None
    u, v = to_minimap_arrays(map_name, first.victim_x.to_numpy(float), first.victim_y.to_numpy(float))
    ok = np.isfinite(u) & np.isfinite(v)
    if ok.sum() < 8:
        return None
    n = 24
    grid = np.histogram2d(v[ok], u[ok], bins=n, range=[[0, 1], [0, 1]])[0]
    p = np.pad(grid, 1)
    sm = sum(p[i:i + n, j:j + n] for i in range(3) for j in range(3))
    zones = find_zones(HeatLayer(grid=(sm / sm.max()).tolist(), max_count=int(grid.max())), threshold=0.6, min_cells=2, top=1)
    if not zones:
        return None
    z = zones[0]
    inside = int(np.sum((u[ok] >= z.x0) & (u[ok] <= z.x1) & (v[ok] >= z.y0) & (v[ok] <= z.y1)))
    share = inside / int(ok.sum())
    where = zone_name(z, [PlantPoint(site=s, point=Point(x=a, y=b)) for s, (a, b) in plants_pts.items()])
    return PlanZone(box=[z.x0, z.y0, z.x1, z.y1], kind="enemy_weak",
                    label=f"{enemy} perde {f_pct(share * 100)} das aberturas {where}",
                    evidence=Stat(value=share, sample_size=int(ok.sum()), low_sample=int(ok.sum()) < 10))


def blind_zones(full: Store, map_name: str, plants_pts: dict[str, tuple[float, float]], kinds: tuple[str, ...]) -> list[PlanZone]:
    try:
        e, heat = _events_and_layers(full.where(map_name=map_name), map_name)
    except Exception:
        return []
    if not heat.has_data or len(e) == 0:
        return []
    pp = [PlantPoint(site=s, point=Point(x=a, y=b)) for s, (a, b) in plants_pts.items()]
    vu, vv, ku, kv = (e[c].to_numpy(float) for c in ("vu", "vv", "ku", "kv"))
    out: list[PlanZone] = []
    for kind in kinds:
        layer = heat.danger if kind == "danger" else heat.uncovered
        zs = find_zones(layer)[:1] if layer else []
        for z in zs:
            if kind == "danger":
                deaths = int(np.sum((vu >= z.x0) & (vu <= z.x1) & (vv >= z.y0) & (vv <= z.y1)))
                kills = int(np.sum((ku >= z.x0) & (ku <= z.x1) & (kv >= z.y0) & (kv <= z.y1)))
                if deaths < 1.2 * kills:
                    continue
                out.append(PlanZone(box=[z.x0, z.y0, z.x1, z.y1], kind="danger", label=f"Evite o duelo solo {zone_name(z, pp)}: {deaths} mortes × {kills} abates",
                                    evidence=Stat(value=None, sample_size=deaths + kills, low_sample=False)))
            else:
                inside = (ku >= z.x0) & (ku <= z.x1) & (kv >= z.y0) & (kv <= z.y1)
                unc = int(np.sum(inside & ~e.covered.to_numpy(bool) & e.has_opp.to_numpy(bool)))
                out.append(PlanZone(box=[z.x0, z.y0, z.x1, z.y1], kind="uncovered", label=f"Cubra a zona {zone_name(z, pp)}: {unc} de {int(inside.sum())} abates sem cobertura",
                                    evidence=Stat(value=None, sample_size=int(inside.sum()), low_sample=int(inside.sum()) < 10)))
    return out


def build_map_plan(full: Store, team: str, enemy: str, map_name: str, side: str, site: str | None,
                   assigned: list[tuple[PlayerScout, str]], enemy_route: list[Point], enemy_snaps: int,
                   cache: dict) -> MapPlan:
    """MapPlan of one round (side = the planned team's side). `cache` shares the heavy pieces between rounds."""
    key_pp = ("pp",)
    if key_pp not in cache:
        cache[key_pp] = plant_points(full, map_name)
    plants = cache[key_pp]
    if not plants:
        return MapPlan(note_pt=f"{map_name} não tem minimapa nem pontos de plante no catálogo: sem desenho.")
    markers = [PlanMarker(point=Point(x=a, y=b), kind="site", label=s) for s, (a, b) in plants.items()]
    routes: list[PlanRoute] = []
    zones: list[PlanZone] = []
    note = None
    side_en = "defense" if side == "attack" else "attack"
    if site:
        if side == "attack":
            ck = ("att", team, site, tuple(p.puuid for p, _ in assigned))
            if ck not in cache:
                cache[ck] = attack_routes(full, team, assigned, map_name, site, plants)
            routes, note = cache[ck]
        else:
            ck = ("def", team, site, tuple(p.puuid for p, _ in assigned))
            if ck not in cache:
                cache[ck] = defense_layout(full, team, assigned, map_name, site, plants)
            m, routes, note = cache[ck]
            markers += m
    if len(enemy_route) >= 2:
        routes = list(routes) + [PlanRoute(
            kind="enemy", label=f"{enemy} · {'ataque provável' if side_en == 'attack' else 'defesa provável'}", points=enemy_route,
            evidence=_stat(enemy_snaps))]
    zk = ("zone", enemy, side_en)
    if zk not in cache:
        cache[zk] = enemy_weak_zone(full, enemy, map_name, side_en, plants)
    if cache[zk] is not None:
        zones.append(cache[zk])
    bk = ("blind", side)
    if bk not in cache:
        cache[bk] = blind_zones(full, map_name, plants, ("danger",) if side == "attack" else ("uncovered",))
    zones += cache[bk]
    return MapPlan(routes=routes, zones=zones, markers=markers, note_pt=note)
