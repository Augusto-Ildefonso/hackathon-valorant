"""Map rules: MapProfile (+ the store it was built from) -> side bias, site tendencies and blind spots. Owner: Stream D."""
from __future__ import annotations

import numpy as np

from ..analytics.heatmaps import heatmap, kill_events_with_positions
from ..data.store import Store
from ..schemas.common import Insight
from ..schemas.map import MapProfile, PlantPoint
from . import thresholds as T
from .core import Scored, f_pct, make_insight, select
from .zones import Zone, find_zones

_EVENTS_CACHE: dict[tuple, object] = {}


def _events_and_layers(store: Store, map_name: str):
    key = (map_name, len(store.matches), hash(tuple(sorted(store.matches.match_id))))
    if key not in _EVENTS_CACHE:
        if len(_EVENTS_CACHE) > 8:
            _EVENTS_CACHE.clear()
        _EVENTS_CACHE[key] = (kill_events_with_positions(store, map_name), heatmap(store, map_name, "both", 64))
    return _EVENTS_CACHE[key]


def zone_name(z: Zone, plants: list[PlantPoint]) -> str:
    """'perto do site A' when a plant point is close, else a coarse region of the minimap."""
    cx, cy = z.center
    if plants:
        near = min(plants, key=lambda p: (p.point.x - cx) ** 2 + (p.point.y - cy) ** 2)
        if ((near.point.x - cx) ** 2 + (near.point.y - cy) ** 2) ** 0.5 <= T.ZONE_NEAR_SITE:
            return f"perto do site {near.site}"
    if abs(cx - 0.5) < 0.2 and abs(cy - 0.5) < 0.2:
        return "no meio do mapa"
    vert = "de cima" if cy < 0.4 else "de baixo" if cy > 0.6 else ""
    horiz = "da esquerda" if cx < 0.4 else "da direita" if cx > 0.6 else ""
    return "no lado " + " ".join(x for x in (vert, horiz) if x) if (vert or horiz) else "no meio do mapa"


def for_map(stats: MapProfile, store: Store | None = None) -> list[Insight]:
    out: list[Scored] = []
    n_rounds = stats.rounds
    att, dfn = stats.attack_win_rate.value, stats.defense_win_rate.value
    if att is not None and stats.classification != "balanced":
        fav = "defesa" if stats.classification == "defense" else "ataque"
        win = dfn if stats.classification == "defense" else att
        gap = abs(att - dfn) * 100
        out.append(Scored(make_insight(
            "map-side-bias", "strategy",
            f"{stats.map.name} favorece a {fav}: ela vence {f_pct(win * 100)} dos rounds ({gap:.0f} p.p. a mais que o outro lado).",
            f"vitórias da {fav}", win * 100, n_rounds, 50, "%"), gap / 10))

    sites = [s for s in stats.sites if s.plants >= T.MIN_TEAM_EVENTS]
    if sites:
        top = max(sites, key=lambda s: s.plants)
        total = sum(s.plants for s in stats.sites)
        share = top.plants / total * 100 if total else 0
        out.append(Scored(make_insight(
            "map-site-popular", "strategy",
            f"O site {top.site} recebe {f_pct(share)} dos plantes de {stats.map.name} e os defensores desarmam a spike em {f_pct((top.defuse_rate.value or 0) * 100)} deles.",
            f"plantes no site {top.site}", share, total, None, "%", "events"), 0.5))
    rated = [s for s in sites if s.defuse_rate.value is not None]
    if len(rated) >= 2:
        easy, hard = max(rated, key=lambda s: s.defuse_rate.value), min(rated, key=lambda s: s.defuse_rate.value)
        gap = (easy.defuse_rate.value - hard.defuse_rate.value) * 100
        if gap >= 10:
            out.append(Scored(make_insight(
                "map-site-retake", "tip",
                f"Retake mais fácil no site {easy.site} ({f_pct(easy.defuse_rate.value * 100)} de desarmes) do que no {hard.site} ({f_pct(hard.defuse_rate.value * 100)}): plantar no {hard.site} rende mais.",
                f"desarmes no site {easy.site}", easy.defuse_rate.value * 100, easy.plants, hard.defuse_rate.value * 100, "%", "events"),
                gap / 20))

    if store is not None and stats.map.has_minimap:
        out.extend(_blind_spots(stats, store))
    return select(out)


def _blind_spots(stats: MapProfile, store: Store) -> list[Scored]:
    try:
        e, heat = _events_and_layers(store, stats.map.name)
    except Exception:  # a heatmap failure must never break the map page
        return []
    if not heat.has_data or len(e) == 0:
        return []
    out: list[Scored] = []
    vu, vv, ku, kv = (e[c].to_numpy(float) for c in ("vu", "vv", "ku", "kv"))
    zones = find_zones(heat.danger)[:1] if heat.danger else []
    for z in zones:
        deaths = int(np.sum((vu >= z.x0) & (vu <= z.x1) & (vv >= z.y0) & (vv <= z.y1)))
        kills = int(np.sum((ku >= z.x0) & (ku <= z.x1) & (kv >= z.y0) & (kv <= z.y1)))
        if deaths < T.ZONE_DEATH_RATIO * kills:
            continue  # the area is only a hot spot, not a place where players lose the duel
        where = zone_name(z, stats.plants)
        out.append(Scored(make_insight(
            "map-blind-danger", "weakness",
            f"Zona perigosa {where}: {deaths} mortes contra {kills} abates nessa área. Quem passa por ali costuma perder o duelo.",
            "mortes na zona", deaths, deaths + kills, kills, None, "events"), 1.0))
        out.append(Scored(make_insight(
            "map-blind-danger-tip", "tip",
            f"Evite o duelo individual {where}: entre em dupla e use utilitário para trocar o primeiro contato.",
            "mortes na zona", deaths, deaths + kills, kills, None, "events"), 0.7))
    zones = find_zones(heat.uncovered)[:1] if heat.uncovered else []
    for z in zones:
        inside = (ku >= z.x0) & (ku <= z.x1) & (kv >= z.y0) & (kv <= z.y1)
        unc = int(np.sum(inside & ~e.covered.to_numpy(bool) & e.has_opp.to_numpy(bool)))
        total = int(np.sum(inside))
        where = zone_name(z, stats.plants)
        out.append(Scored(make_insight(
            "map-blind-uncovered", "tip",
            f"Zona descoberta {where}: {unc} de {total} abates dos adversários saíram dali sem ninguém olhando. Posicione alguém para cobri-la.",
            "abates sem cobertura", unc, total, None, None, "events"), 0.9))
    return out
