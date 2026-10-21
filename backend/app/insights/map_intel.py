"""Site and route facts for one matchup on one map (Action Plan, layer 1). Owner: Stream D.

* `site_views`: for every site, how each team performs there (plants, post-plant outcome), shrunk towards the map level.
* `enemy_route`: where the enemy team's players stand 0-30 / 30-60 / 60+ s into their rounds (snapshots exist at kill
  moments only, so the route is a coarse centroid path, not a trajectory). Returns the number of snapshots behind it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.coords import to_minimap, to_minimap_arrays
from ..data.store import Store
from ..metrics.objective import attack_rounds
from ..schemas.common import Point

SHRINK_K = 5
BUCKETS_MS = ((0, 30_000), (30_000, 60_000), (60_000, 10**9))


def shrink(wins: float, n: int, prior: float, k: int = SHRINK_K) -> float:
    return (wins + k * prior) / (n + k)


@dataclass
class SiteView:
    site: str
    map_plants: int = 0
    map_win: float | None = None  # attackers' round win rate after planting here (all teams on the map)
    my_plants: int = 0
    my_attack_rounds: int = 0
    my_win: float | None = None  # attackers = me
    vs_plants: int = 0  # attackers (anyone) planting here against the enemy defense
    vs_attack_rounds: int = 0
    vs_win: float | None = None
    enemy_plants: int = 0  # the enemy attacking
    enemy_attack_rounds: int = 0
    my_def_retakes: int = 0  # me defending: plants suffered here and how many were defused
    my_def_plants: int = 0

    @property
    def my_share(self) -> float | None:
        return self.my_plants / self.my_attack_rounds if self.my_attack_rounds else None

    @property
    def vs_share(self) -> float | None:
        return self.vs_plants / self.vs_attack_rounds if self.vs_attack_rounds else None

    @property
    def enemy_share(self) -> float | None:
        return self.enemy_plants / self.enemy_attack_rounds if self.enemy_attack_rounds else None


def _won_after_plant(df: pd.DataFrame, site: str) -> tuple[int, float | None]:
    d = df[(df.plant_site == site) & df.planted]
    return len(d), (float(d.attacker_won.mean()) if len(d) else None)


def site_views(full: Store, me: str, enemy: str, map_name: str) -> dict[str, SiteView]:
    r = attack_rounds(full, map_name=map_name)
    sites = sorted(r.plant_site.dropna().unique())
    mine = r[r.attacker_team == me]
    vs = r[r.defender_team == enemy]
    theirs = r[r.attacker_team == enemy]
    me_def = r[r.defender_team == me]
    views: dict[str, SiteView] = {}
    for s in sites:
        v = SiteView(site=s)
        v.map_plants, v.map_win = _won_after_plant(r, s)
        n, w = _won_after_plant(mine, s)
        v.my_plants, v.my_win, v.my_attack_rounds = n, w, len(mine)
        n, w = _won_after_plant(vs, s)
        v.vs_plants, v.vs_win, v.vs_attack_rounds = n, w, len(vs)
        n, _ = _won_after_plant(theirs, s)
        v.enemy_plants, v.enemy_attack_rounds = n, len(theirs)
        d = me_def[(me_def.plant_site == s) & me_def.planted]
        v.my_def_plants, v.my_def_retakes = len(d), int(d.defused.sum())
        views[s] = v
    return views


def avg_plant_ms(full: Store, team: str, map_name: str) -> tuple[float | None, int]:
    r = attack_rounds(full, team=team, map_name=map_name)
    p = r[r.planted]
    return (float(p.plant_time_ms.mean()) if len(p) else None), len(p)


def enemy_route(full: Store, enemy: str, map_name: str, side: str, site: str | None = None) -> tuple[list[Point], int]:
    """Centroid path of the enemy team's player positions by time bucket. `side` is the ENEMY's side."""
    m = full.matches[full.matches.map_name == map_name]
    if m.empty:
        return [], 0
    rounds = full.rounds[full.rounds.match_id.isin(m.match_id)]
    col = "attacker_team" if side == "attack" else "defender_team"
    rounds = rounds[rounds[col] == enemy]
    if side == "attack" and site:
        rounds = rounds[rounds.plant_site == site]
    if rounds.empty:
        return [], 0
    k = full.kills.merge(rounds[["match_id", "round_num"]], on=["match_id", "round_num"])
    if k.empty:
        return [], 0
    team_of = dict(zip(zip(full.match_players.match_id, full.match_players.puuid), full.match_players.team_name))
    rows = []
    for mid, t, locs in zip(k.match_id, k.time_in_round_ms, k.player_locations):
        for p in locs:
            if team_of.get((mid, p["puuid"])) == enemy:
                rows.append((t, p["x"], p["y"]))
    if not rows:
        return [], 0
    a = np.array(rows, dtype=float)
    u, v = to_minimap_arrays(map_name, a[:, 1], a[:, 2])
    ok = np.isfinite(u) & np.isfinite(v)
    pts: list[Point] = []
    total = 0
    for lo, hi in BUCKETS_MS:
        sel = ok & (a[:, 0] >= lo) & (a[:, 0] < hi)
        if sel.sum() >= 5:
            pts.append(Point(x=float(np.clip(u[sel].mean(), 0, 1)), y=float(np.clip(v[sel].mean(), 0, 1))))
            total += int(sel.sum())
    if side == "attack" and site:
        planted = full.rounds[full.rounds.match_id.isin(m.match_id) & (full.rounds.plant_site == site) & full.rounds.planter.notna()]
        if len(planted):
            p = to_minimap(map_name, float(planted.plant_x.mean()), float(planted.plant_y.mean()))
            if p is not None and pts:
                pts.append(Point(x=p[0], y=p[1]))
    return (pts if len(pts) >= 2 else []), total
