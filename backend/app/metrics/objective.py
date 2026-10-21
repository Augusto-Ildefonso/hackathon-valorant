"""Objective metrics: plant rate, site preference, time to plant, post-plant and retake rates. Owner: Stream A."""
from __future__ import annotations

import pandas as pd

from ..data.store import Store
from .config import make_stat


def attack_rounds(store: Store, team: str | None = None, map_name: str | None = None) -> pd.DataFrame:
    """Rounds enriched with map and a 'planted/defused/attacker_won' view, optionally for one attacking team/map."""
    r = store.rounds.merge(store.matches[["match_id", "map_name"]], on="match_id")
    if map_name:
        r = r[r.map_name == map_name]
    if team:
        r = r[r.attacker_team == team]
    r = r.assign(planted=r.planter.notna(), defused=r.defuser.notna(), attacker_won=r.winning_team == r.attacker_team)
    return r


def objective_summary(store: Store, team: str | None = None, map_name: str | None = None) -> dict:
    """Attack-side objective stats (as `Stat`s). `team` = the attacking team; None = every attacker."""
    r = attack_rounds(store, team, map_name)
    planted = r[r.planted]
    n_att, n_pl = len(r), len(planted)
    sites = {s: make_stat((planted.plant_site == s).mean() if n_pl else None, n_pl, "events") for s in ("A", "B", "C")}
    return {
        "plant_rate": make_stat(n_pl / n_att if n_att else None, n_att, "rounds"),
        "site_preference": sites,
        "avg_time_to_plant_ms": make_stat(planted.plant_time_ms.mean() if n_pl else None, n_pl, "events"),
        "post_plant_win_rate": make_stat(planted.attacker_won.mean() if n_pl else None, n_pl, "events"),
        "retake_rate": make_stat(planted.defused.mean() if n_pl else None, n_pl, "events"),
    }


def site_summary(store: Store, map_name: str, team: str | None = None) -> list[dict]:
    """Per-site plants, plant rate (share of attack rounds), defuse and retake rates for one map."""
    r = attack_rounds(store, team, map_name)
    n_att = len(r)
    out = []
    for s in sorted(r.plant_site.dropna().unique()):
        p = r[r.plant_site == s]
        out.append({
            "site": s, "plants": len(p),
            "plant_rate": make_stat(len(p) / n_att if n_att else None, n_att, "rounds"),
            "defuse_rate": make_stat(p.defused.mean(), len(p), "events"),
            "retake_rate": make_stat(p.defused.mean(), len(p), "events"),  # a defuse is the only retake outcome in the data
        })
    return out
