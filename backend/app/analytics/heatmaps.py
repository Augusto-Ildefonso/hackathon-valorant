"""Kill/death heatmaps and the two blind-spot layers of the Map Profile. Owner: Stream C. Method documented in
`metrics/SPEC.md` ("Heatmaps and blind spots").

* kills / deaths: where kills were scored (killer's own position at the kill) and where players died, per side.
* danger (blind spot a): cells where deaths far exceed kills, with at least `MIN_CELL_EVENTS` events in the 3x3
  neighbourhood.
* uncovered (blind spot b): kills scored from a position that NO living opponent covered at that moment (not within
  `NEAR` of anybody and not inside anybody's 90-degree view cone of length `FAR`). Cells where at least
  `UNCOVERED_MIN_SHARE` of the nearby kills (>= `MIN_CELL_EVENTS`) come from such positions are places the victims'
  team does not watch; score = uncovered kills x share. Uses the verified view direction (sin t, -cos t).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.catalog import get_catalog
from ..data.coords import to_minimap, to_minimap_arrays
from ..data.store import Store
from ..metrics.config import MIN_CELL_EVENTS
from ..schemas.common import Point
from ..schemas.map import HeatLayer, HeatmapResponse, PlantPoint

NEAR = 0.05  # minimap units: a living opponent this close "covers" a position
FAR = 0.35  # view cone length
HALF_CONE = np.pi / 4
UNCOVERED_MIN_SHARE = 0.4  # the dataset average is ~24%: only cells clearly above it count as blind spots


def _box3(a: np.ndarray) -> np.ndarray:
    p = np.pad(a, 1)
    n = a.shape[0]
    return sum(p[i:i + n, j:j + n] for i in range(3) for j in range(3))


def _layer(raw: np.ndarray, smooth: bool = True) -> HeatLayer:
    a = _box3(raw) if smooth else raw
    m = a.max()
    return HeatLayer(grid=(a / m if m > 0 else a).round(4).tolist(), max_count=int(raw.max()))


def _hist(u: np.ndarray, v: np.ndarray, mask: np.ndarray, n: int) -> np.ndarray:
    ok = mask & np.isfinite(u) & np.isfinite(v)
    return np.histogram2d(v[ok], u[ok], bins=n, range=[[0, 1], [0, 1]])[0]


def kill_events_with_positions(store: Store, map_name: str) -> pd.DataFrame:
    """One row per player-vs-player kill on `map_name`: minimap positions of killer and victim (NaN when outside the
    map), the sides of both, and `covered` = a living opponent could see the killer's position."""
    m = store.matches[store.matches.map_name == map_name]
    k = store.kills[store.kills.match_id.isin(m.match_id)]
    k = k[k.killer_color.notna() & (k.killer_color != k.victim_color)].reset_index(drop=True)
    if k.empty:
        return k.assign(ku=[], kv=[], vu=[], vv=[], killer_side=[], victim_side=[], covered=[], has_opp=[])
    sides = store.round_player_stats[["match_id", "round_num", "puuid", "side"]]
    key = ["match_id", "round_num"]
    k = k.merge(sides.rename(columns={"puuid": "victim", "side": "victim_side"}), on=key + ["victim"], how="left")
    k = k.merge(sides.rename(columns={"puuid": "killer", "side": "killer_side"}), on=key + ["killer"], how="left")
    mp = store.match_players
    color = dict(zip(zip(mp.match_id, mp.puuid), mp.team_color))

    kx = np.full(len(k), np.nan); ky = np.full(len(k), np.nan)
    ev, ox, oy, oview = [], [], [], []
    for i, (mid, locs, killer, kcolor) in enumerate(zip(k.match_id, k.player_locations, k.killer, k.killer_color)):
        for p in locs:
            if p["puuid"] == killer:
                kx[i], ky[i] = p["x"], p["y"]
            elif color.get((mid, p["puuid"])) not in (None, kcolor):
                ev.append(i); ox.append(p["x"]); oy.append(p["y"]); oview.append(p["view_radians"])
    ku, kv = to_minimap_arrays(map_name, kx, ky)
    vu, vv = to_minimap_arrays(map_name, k.victim_x.to_numpy(float), k.victim_y.to_numpy(float))

    covered = np.zeros(len(k), bool)
    has_opp = np.zeros(len(k), bool)
    if ev:
        ev_a = np.array(ev)
        ou, ov = to_minimap_arrays(map_name, np.array(ox), np.array(oy))
        dx, dy = ku[ev_a] - ou, kv[ev_a] - ov
        dist = np.hypot(dx, dy)
        diff = np.abs((np.arctan2(dy, dx) - np.arctan2(-np.cos(oview), np.sin(oview)) + np.pi) % (2 * np.pi) - np.pi)
        valid = np.isfinite(dist)
        see = valid & ((dist <= NEAR) | ((dist <= FAR) & (diff <= HALF_CONE)))
        np.logical_or.at(covered, ev_a[see], True)
        has_opp[ev_a[valid]] = True
    return k.assign(ku=ku, kv=kv, vu=vu, vv=vv, covered=covered, has_opp=has_opp)[
        ["match_id", "round_num", "ku", "kv", "vu", "vv", "killer_side", "victim_side", "covered", "has_opp"]]


def heatmap(store: Store, map_name: str, side: str = "both", grid_size: int = 64) -> HeatmapResponse:
    """Heatmap layers for one map over `store` (already filtered by the caller)."""
    cat = get_catalog()
    ref = cat.map_ref(map_name)
    s = store.where(map_name=map_name)
    mp, rps = s.match_players, s.round_player_stats
    agents = [cat.agent(a) for a in mp[mp.agent_id.notna()].agent_id.value_counts().head(5).index]
    weapons = [cat.weapon(w) for w in rps[rps.weapon_id.notna()].weapon_id.value_counts().head(5).index]
    planted = s.rounds[s.rounds.planter.notna()]
    plants = []
    for site, g in planted.groupby("plant_site"):
        p = to_minimap(map_name, float(g.plant_x.mean()), float(g.plant_y.mean()))
        if p is not None:
            plants.append(PlantPoint(site=site, point=Point(x=p[0], y=p[1])))
    base = dict(map=ref, side=side, grid_size=grid_size, agents_used=agents, weapons_used=weapons)
    if not ref.has_minimap or s.matches.empty:
        return HeatmapResponse(has_data=False, plants=[], **base)

    e = kill_events_with_positions(s, map_name)
    if e.empty:
        return HeatmapResponse(has_data=False, plants=plants, **base)
    pick = (lambda col: np.ones(len(e), bool)) if side == "both" else (lambda col: (e[col] == side).to_numpy())
    n = grid_size
    deaths = _hist(e.vu.to_numpy(), e.vv.to_numpy(), pick("victim_side"), n)
    kills = _hist(e.ku.to_numpy(), e.kv.to_numpy(), pick("killer_side"), n)
    unc = _hist(e.ku.to_numpy(), e.kv.to_numpy(), pick("killer_side") & (~e.covered & e.has_opp).to_numpy(), n)

    d3, k3, u3, e3 = _box3(deaths), _box3(kills), _box3(unc), _box3(deaths + kills)
    danger = np.where(e3 >= MIN_CELL_EVENTS, np.maximum(d3 - k3, 0), 0.0)
    share = u3 / np.maximum(k3, 1)  # share of the neighbourhood's kills scored from unwatched positions
    uncovered = np.where((k3 >= MIN_CELL_EVENTS) & (share >= UNCOVERED_MIN_SHARE), u3 * share, 0.0)
    return HeatmapResponse(
        has_data=True, kills=_layer(kills), deaths=_layer(deaths), danger=_layer(danger, smooth=False),
        uncovered=_layer(uncovered, smooth=False), plants=plants, **base)
