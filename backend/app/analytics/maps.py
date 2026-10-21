"""Map list and Map Profile builders. Owner: Stream C. Uses only `Store` + `app.metrics` + the catalog."""
from __future__ import annotations

import pandas as pd

from ..data.catalog import MAP_NAMES, get_catalog
from ..data.coords import to_minimap
from ..data.store import Store
from ..metrics import make_stat, site_summary
from ..schemas.common import Point
from ..schemas.map import MapListItem, MapProfile, PlantPoint, SiteStats, UsageRow

CLASSIFICATION_GAP = 0.03  # attack/defense win rates closer than 3 p.p. are "balanced"
TOP_N = 8
PUBLIC_NAMES = {n.lower(): n for n in MAP_NAMES.values()}


def canonical_map_name(name: str) -> str | None:
    """Case-insensitive public map name ("lotus" -> "Lotus"); None if it is not a known map."""
    return PUBLIC_NAMES.get(name.strip().lower())


def _rounds_with_map(store: Store) -> pd.DataFrame:
    r = store.rounds.merge(store.matches[["match_id", "map_name"]], on="match_id")
    return r.assign(attacker_won=r.winning_team == r.attacker_team)


def map_exists(store: Store, name: str) -> bool:
    return bool((store.matches.map_name == name).any())


def map_list(store: Store) -> list[MapListItem]:
    cat = get_catalog()
    r = _rounds_with_map(store)
    g = r.groupby("map_name").agg(rounds=("round_num", "size"), att=("attacker_won", "mean"))
    n = store.matches.groupby("map_name").size()
    return [MapListItem(map=cat.map_ref(name), matches=int(n[name]), rounds=int(row.rounds),
                        attack_win_rate=make_stat(row.att, int(row.rounds)))
            for name, row in g.sort_values("rounds", ascending=False).iterrows()]


def _usage(counts: pd.Series, total: int, name_of, icon_of) -> list[UsageRow]:
    rows = []
    for key, n in counts.head(TOP_N).items():
        rows.append(UsageRow(id=str(key), name=name_of(key), icon_url=icon_of(key), picks=int(n), share=float(n / total)))
    return rows


def map_profile(store: Store, name: str) -> MapProfile:
    """Profile of one map over `store` (already filtered by the caller). Raises KeyError if the map has no matches."""
    cat = get_catalog()
    s = store.where(map_name=name)
    if s.matches.empty:
        raise KeyError(name)
    r = _rounds_with_map(s)
    n_rounds = len(r)
    att = float(r.attacker_won.mean())
    gap = (1 - att) - att  # defense minus attack
    classification = "defense" if gap >= CLASSIFICATION_GAP else "attack" if gap <= -CLASSIFICATION_GAP else "balanced"

    mp = s.match_players
    agents = mp[mp.agent_id.notna()].agent_id.value_counts()
    rps = s.round_player_stats
    weapons = rps[rps.weapon_id.notna()].weapon_id.value_counts()
    top_agents = _usage(agents, len(mp), lambda k: cat.agent_name(k), lambda k: (cat.agent(k).icon_url if cat.agent(k) else None))
    top_weapons = _usage(weapons, int(weapons.sum()), lambda k: cat.weapon_name(k), lambda k: (cat.weapon(k).icon_url if cat.weapon(k) else None))

    sites = [SiteStats(site=x["site"], plants=x["plants"], plant_rate=x["plant_rate"], defuse_rate=x["defuse_rate"],
                       retake_rate=x["retake_rate"]) for x in site_summary(s, name)]
    plants: list[PlantPoint] = []
    planted = s.rounds[s.rounds.planter.notna()]
    for site, g in planted.groupby("plant_site"):
        p = to_minimap(name, float(g.plant_x.mean()), float(g.plant_y.mean()))
        if p is not None:
            plants.append(PlantPoint(site=site, point=Point(x=p[0], y=p[1])))

    return MapProfile(
        map=cat.map_ref(name), matches=len(s.matches), rounds=n_rounds, attack_win_rate=make_stat(att, n_rounds),
        defense_win_rate=make_stat(1 - att, n_rounds), classification=classification, top_agents=top_agents,
        top_weapons=top_weapons, sites=sites, plants=plants, insights=[])
