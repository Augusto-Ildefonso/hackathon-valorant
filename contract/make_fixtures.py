"""Regenerates `contract/fixtures/*.json` and validates each against its Pydantic response model.

Run from the repo root:  backend/.venv/bin/python contract/make_fixtures.py

Fixtures are *shape examples*: team names, map, score, date and agent/weapon/map IDs come from the real match
RUSH2_002 (Fatec PG 10 x 13 Panterão Gaming, Ascent) and from the catalog; player-level numbers are illustrative.
Streams may extend a fixture by hand, but the shape is frozen (see contract/openapi.md).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import ENDPOINTS  # noqa: E402

OUT = ROOT / "contract" / "fixtures"
catalog = json.loads((ROOT / "public_catalog" / "PublicContentCatalog.json").read_text())


def pick(items, name):
    return next(i for i in items if i["name"].get("en-US") == name)


ascent_id = pick(catalog["maps"], "Ascent")["id"]
jett_id = pick(catalog["characters"], "Jett")["id"]
sova_id = pick(catalog["characters"], "Sova")["id"]
vandal_id = pick(catalog["weapons"], "Vandal")["id"]
phantom_id = pick(catalog["weapons"], "Phantom")["id"]
classic_id = pick(catalog["weapons"], "Classic")["id"]

ASCENT = {"codename": "Ascent", "name": "Ascent", "has_minimap": True, "minimap_url": f"/assets/Maps/{ascent_id}.png"}
ABYSS = {"codename": "Infinity", "name": "Abyss", "has_minimap": False, "minimap_url": None}
JETT = {"id": jett_id, "name": "Jett", "name_inferred": False, "icon_url": f"/assets/Characters/{jett_id}_small.png"}
SOVA = {"id": sova_id, "name": "Sova", "name_inferred": False, "icon_url": f"/assets/Characters/{sova_id}_small.png"}
UNKNOWN_AGENT = {"id": "EFBA5359-0000-0000-0000-000000000000", "name": None, "name_inferred": False, "icon_url": None}
VANDAL = {"id": vandal_id, "name": "Vandal", "name_inferred": False, "icon_url": f"/assets/Weapons/{vandal_id}.png"}
PHANTOM = {"id": phantom_id, "name": "Phantom", "name_inferred": False, "icon_url": f"/assets/Weapons/{phantom_id}.png"}
CLASSIC = {"id": classic_id, "name": "Classic", "name_inferred": False, "icon_url": f"/assets/Weapons/{classic_id}.png"}
FATEC = {"name": "Fatec PG"}
PANTERAO = {"name": "Panterão Gaming"}
P1 = {"puuid": "puuid-0001", "riot_id": "Didado#BR1"}
P2 = {"puuid": "puuid-0002", "riot_id": "ESCkey#BR1"}
P3 = {"puuid": "puuid-0003", "riot_id": "Vani#BR1"}


def stat(value, n, low=False):
    return {"value": value, "sample_size": n, "low_sample": low}


def insight(i, kind, text, metric, value, base, n, unit=None, low=False):
    return {"id": i, "kind": kind, "text_pt": text, "low_sample": low,
            "evidence": {"metric": metric, "value": value, "baseline": base, "sample_size": n, "unit": unit}}


def grid(n, hot):
    g = [[0.0] * n for _ in range(n)]
    for (r, c, v) in hot:
        g[r][c] = v
    return {"grid": g, "max_count": 42}


MATCH_ITEM = {
    "match_id": "aaac8e08-a406-498d-bd39-342a6a2f9aeb", "tournament": "Rush Series Esquenta 2", "phase": None,
    "date": "2026-06-20", "map": ASCENT, "team_a": {"team": FATEC, "score": 10},
    "team_b": {"team": PANTERAO, "score": 13}, "winner": "b", "duration_ms": 2_461_000,
}
ROLE_ENTRY = {"role": "entry", "score": 0.74, "confidence": 0.68, "inferred": False,
              "signals": [{"name": "first_duel_share", "value": 0.31, "sample_size": 214},
                          {"name": "first_death_rate", "value": 0.19, "sample_size": 214}]}
RT = ["pistol", "eco", "semi_eco", "force", "full_buy"]

fixtures = {}

fixtures["meta"] = {
    "kpis": {"matches": 336, "rounds": 6618, "kills": 46753, "players": 413, "teams": 118, "tournaments": 4},
    "date_from": "2026-06-06", "date_to": "2026-09-27",
    "tournaments": [
        {"id": "RUSH1", "name": "Rush Series Esquenta", "phases": [], "matches": 29},
        {"id": "RUSH2", "name": "Rush Series Esquenta 2", "phases": [], "matches": 26},
        {"id": "RUSHI", "name": "Rush Series Inclusivo", "phases": [], "matches": 13},
        {"id": "UNIVAVA", "name": "Univavá", "phases": ["Classificatória 1", "Fase de Grupos"], "matches": 268},
    ],
    "maps": [ASCENT, ABYSS],
}

fixtures["search"] = {
    "query": "fa",
    "players": [{"player": P1, "team": FATEC, "matches": 9}],
    "teams": [{"team": FATEC, "matches": 12}],
    "maps": [{"map": {"codename": "Foxtrot", "name": "Breeze", "has_minimap": True, "minimap_url": "/assets/Maps/breeze.png"}}],
}

fixtures["leaderboards"] = {
    "players": {
        "kd": [{"rank": 1, "player": P1, "team": FATEC, "value": 1.52, "matches": 9, "rounds": 201,
                "kd": 1.52, "adr": 168.0, "hs_pct": 0.29, "first_kills": 61}],
        "adr": [{"rank": 1, "player": P2, "team": PANTERAO, "value": 181.4, "matches": 11, "rounds": 240}],
        "hs_pct": [{"rank": 1, "player": P3, "team": PANTERAO, "value": 0.34, "matches": 4, "rounds": 88, "low_sample": True}],
        "first_kills": [{"rank": 1, "player": P1, "team": FATEC, "value": 61, "matches": 9, "rounds": 201}],
    },
    "teams": {
        "win_rate": [{"rank": 1, "team": PANTERAO, "value": 0.71, "matches": 14, "rounds": 330, "wins": 10, "losses": 4}],
        "round_win_rate": [{"rank": 1, "team": PANTERAO, "value": 0.58, "matches": 14, "rounds": 330}],
    },
}

fixtures["matches"] = {"items": [MATCH_ITEM], "total": 336}

fixtures["player"] = {
    "player": P1, "teams": [FATEC], "favorite_agent": JETT,
    "roles": [ROLE_ENTRY,
              {"role": "flex", "score": 0.54, "confidence": 0.4, "inferred": False, "signals": [{"name": "agent_variety", "value": 0.42, "sample_size": 201}]},
              {"role": "support", "score": 0.31, "confidence": 0.2, "inferred": False, "signals": []},
              {"role": "lurker", "score": 0.22, "confidence": 0.2, "inferred": False, "signals": []},
              {"role": "anchor", "score": 0.12, "confidence": 0.2, "inferred": False, "signals": []}],
    "stats": {
        "matches": 9, "rounds": 201, "kills": 168, "deaths": 110, "assists": 41,
        "kd": stat(1.53, 201), "adr": stat(158.2, 201), "hs_pct": stat(0.27, 201),
        "first_kill_rate": stat(0.30, 201), "first_death_rate": stat(0.17, 201),
        "opening_duel_win_pct": stat(0.64, 95), "clutches": 6,
        "multikills": {"k2": 21, "k3": 6, "k4": 1, "k5": 0},
        "shots": 2870, "first_kills": 61, "first_deaths": 34, "traded_deaths": 38,
    },
    "weapons": [{"weapon": VANDAL, "buy_type": None, "rounds": 188, "round_win_rate": stat(0.58, 188),
                 "kills": 231, "kd": stat(1.62, 188), "hs_pct": stat(0.31, 188), "damage_per_round": stat(165.0, 188)},
                {"weapon": VANDAL, "buy_type": "full_buy", "rounds": 96, "round_win_rate": stat(0.55, 96),
                 "kills": 91, "kd": stat(1.6, 96), "hs_pct": stat(0.29, 96), "damage_per_round": stat(161.0, 96)}],
    "by_map": [{"map": ASCENT, "matches": 4, "kills": 77, "deaths": 52, "kd": stat(1.48, 4, True)}],
    "agents": [{"agent": JETT, "matches": 6, "kd": stat(1.6, 6), "adr": stat(163.0, 6), "win_rate": stat(0.5, 6)},
               {"agent": UNKNOWN_AGENT, "matches": 3, "kd": stat(1.4, 3, True), "adr": stat(150.0, 3, True),
                "win_rate": stat(0.33, 3, True)}],
    "insights": [
        insight("hs-low-full-buy", "weakness", "Percentual de headshots abaixo da média em full buy.", "hs_pct_full_buy", 0.22, 0.27, 96, "ratio"),
        insight("opening-strong", "strength", "Vence a maioria dos duelos de abertura.", "opening_duel_win_pct", 0.64, 0.5, 95, "ratio"),
        insight("tip-crosshair", "tip", "Treinar posicionamento de mira (crosshair placement) em ângulos de A longo.", "hs_pct_full_buy", 0.22, 0.27, 96, "ratio", True),
    ],
}

fixtures["teams"] = {"items": [
    {"team": PANTERAO, "matches": 14, "win_rate": stat(0.71, 14), "round_win_rate": stat(0.58, 330), "last_match_date": "2026-06-21"},
    {"team": FATEC, "matches": 12, "win_rate": stat(0.41, 12), "round_win_rate": stat(0.47, 270), "last_match_date": "2026-06-21"},
]}

fixtures["team"] = {
    "team": FATEC,
    "roster": [{"player": P1, "matches": 9, "top_role": ROLE_ENTRY}, {"player": P2, "matches": 12, "top_role": None}],
    "record": {"matches": 12, "series": 8, "wins": 5, "losses": 7, "round_win_rate": stat(0.47, 270),
               "attack_win_rate": stat(0.44, 135), "defense_win_rate": stat(0.51, 135)},
    "matches": [MATCH_ITEM],
    "trend": [{"match_id": MATCH_ITEM["match_id"], "date": "2026-06-20", "round_diff": -3}],
    "by_map": [{"map": ASCENT, "matches": 5, "win_rate": stat(0.4, 5), "attack_win_rate": stat(0.42, 60), "defense_win_rate": stat(0.5, 60)}],
    "economy": {
        "win_rate_by_round_type": {t: stat(0.3 + 0.1 * i, 40 - 6 * i, i == 0) for i, t in enumerate(RT)},
        "pistol_win_rate": stat(0.5, 24), "plant_site_preference": {"A": stat(0.55, 80), "B": stat(0.45, 80)},
        "avg_time_to_plant_ms": stat(48_200, 80), "post_plant_win_rate": stat(0.61, 80), "retake_success_rate": stat(0.33, 52),
    },
    "role_composition": [{"role": "entry", "count": 1}, {"role": "support", "count": 2}, {"role": "flex", "count": 2}],
    "insights": [insight("eco-weak", "weakness", "Rounds eco quase nunca são convertidos.", "eco_win_rate", 0.08, 0.15, 40, "ratio")],
}

fixtures["maps"] = {"items": [
    {"map": ASCENT, "matches": 86, "rounds": 1730, "attack_win_rate": stat(0.47, 1730)},
    {"map": ABYSS, "matches": 13, "rounds": 260, "attack_win_rate": stat(0.52, 260)},
]}

fixtures["map"] = {
    "map": ASCENT, "matches": 86, "rounds": 1730, "attack_win_rate": stat(0.47, 1730), "defense_win_rate": stat(0.53, 1730),
    "classification": "defense",
    "top_agents": [{"id": jett_id, "name": "Jett", "icon_url": JETT["icon_url"], "picks": 160, "share": 0.19}],
    "top_weapons": [{"id": vandal_id, "name": "Vandal", "icon_url": VANDAL["icon_url"], "picks": 5100, "share": 0.41}],
    "sites": [{"site": "A", "plants": 600, "plant_rate": stat(0.52, 1150), "defuse_rate": stat(0.27, 600), "retake_rate": stat(0.31, 600)},
              {"site": "B", "plants": 550, "plant_rate": stat(0.48, 1150), "defuse_rate": stat(0.24, 550), "retake_rate": stat(0.28, 550)}],
    "plants": [{"site": "A", "point": {"x": 0.68, "y": 0.31}}, {"site": "B", "point": {"x": 0.27, "y": 0.62}}],
    "insights": [insight("map-defense", "strategy", "Mapa favorece a defesa.", "defense_win_rate", 0.53, 0.5, 1730, "ratio")],
}

fixtures["map_heatmap"] = {
    "map": ASCENT, "side": "both", "grid_size": 8, "has_data": True,
    "kills": grid(8, [(2, 5, 1.0), (3, 5, 0.6)]), "deaths": grid(8, [(2, 5, 0.9), (5, 2, 0.7)]),
    "danger": grid(8, [(5, 2, 0.8)]), "uncovered": grid(8, [(4, 6, 0.5)]),
    "plants": [{"site": "A", "point": {"x": 0.68, "y": 0.31}}], "agents_used": [JETT, SOVA], "weapons_used": [VANDAL, PHANTOM],
}


def rnd(n, half, winner, a_side, result, ceo, site, planted, defused, a_t, b_t, a_l, b_l):
    return {"number": n, "half": half, "winner": winner, "team_a_side": a_side, "result": result, "ceremony": ceo,
            "plant_site": site, "planted": planted, "defused": defused,
            "economy": {"team_a_type": a_t, "team_b_type": b_t, "team_a_loadout": a_l, "team_b_loadout": b_l}}


fixtures["match"] = {
    **{k: MATCH_ITEM[k] for k in ("match_id", "tournament", "phase", "date", "map", "team_a", "team_b", "winner", "duration_ms")},
    "mvp": P2,
    "rounds": [rnd(1, 1, "b", "attack", "defused", "Clutch", "A", True, True, "pistol", "pistol", 900, 900),
               rnd(2, 1, "b", "attack", "eliminated", None, None, False, False, "eco", "full_buy", 1200, 4300),
               rnd(13, 2, "a", "defense", "detonated", "Flawless", "B", True, False, "pistol", "pistol", 900, 900)],
    "scoreboard": [{"player": P1, "team": "a", "agent": JETT, "kills": 18, "deaths": 14, "assists": 3, "adr": stat(171.2, 23),
                    "hs_pct": stat(0.28, 23), "first_kills": 5, "score": 4120}],
    "insights_a": [insight("m-eco", "weakness", "Perdeu todos os rounds eco nesta partida.", "eco_rounds_won", 0, 0.15, 5, "count", True)],
    "insights_b": [insight("m-def", "strength", "Defesa sólida no site A.", "site_a_defense_win", 0.8, 0.5, 10, "ratio")],
}


def replay_player(puuid, name, team, agent, x, y, view):
    return {"puuid": puuid, "riot_id": name, "team": team, "agent": agent,
            "pos": {"x": x, "y": y} if x is not None else None, "view_radians": view}


fixtures["match_kills"] = {
    "match_id": MATCH_ITEM["match_id"], "map": ASCENT, "has_minimap": True,
    "teams": {"a": FATEC, "b": PANTERAO},
    "kills": [{
        "id": "1-0", "round": 1, "time_ms": 29_484,
        "killer": replay_player("puuid-0002", "ESCkey#BR1", "b", SOVA, 0.61, 0.33, 3.29),
        "victim": replay_player("puuid-0001", "Didado#BR1", "a", JETT, 0.42, 0.30, 1.1),
        "assistants": [], "weapon": VANDAL, "damage_type": "weapon", "headshot": None,
        "others_alive": [replay_player("puuid-0003", "Vani#BR1", "b", UNKNOWN_AGENT, 0.55, 0.40, 0.3),
                         replay_player("puuid-0099", "Out#BR1", "a", None, None, None, None)],
    }],
}

PLAN_BUY = [{"role": "entry", "weapon": VANDAL, "armor": "heavy", "reason_pt": "Full buy: melhor taxa de vitória com Vandal."},
            {"role": "support", "weapon": PHANTOM, "armor": "heavy", "reason_pt": "Phantom para spray em retomadas."}]
OUTCOME_W = {"round_type": "full_buy", "summary_pt": "Se vencer o round anterior, full buy."}
OUTCOME_L = {"round_type": "force", "summary_pt": "Se perder, force buy parcial."}


def plan_round(n, half, side, rtype, res):
    return {
        "number": n, "half": half, "side": side, "round_type": rtype, "base_scenario_result": res,
        "win_probability": stat(0.46, 38, False),
        "projected_economy": {"team_credits": 4300, "enemy_credits": 3900, "reasoning_pt": "Perdeu 2 rounds; time costuma forçar."},
        "buy": PLAN_BUY,
        "strategy": {"summary_pt": "Executar no site A com fumaça de ambos os lados.", "site": "A", "timing": "default",
                     "steps_pt": ["Fumaça em CT", "Entrada com o entry"]},
        "enemy_weak_points": [insight("w1", "weakness", "Perde o meio cedo.", "mid_first_death_rate", 0.34, 0.2, 55, "ratio")],
        "enemy_probable_strategy": {"summary_pt": "Costuma defender o site B com 3.", "site": "B",
                                   "route": [{"x": 0.3, "y": 0.6}, {"x": 0.4, "y": 0.5}], "evidence": stat(0.6, 30)},
        "contingency": {"if_previous_won": OUTCOME_W, "if_previous_lost": OUTCOME_L},
        "insights": [],
    }


fixtures["plan"] = {
    "team_a": FATEC, "team_b": PANTERAO, "perspective": "a", "map": ASCENT, "rounds_per_half": 2, "starting_side": "attack",
    "agents": [{"agent": JETT, "role": "duelist", "reason_pt": "Mais usada pelo time no mapa.", "evidence": stat(0.5, 6)}],
    "opponent": {"team": PANTERAO, "matches_on_map": 6, "preferred_site": "B", "avg_time_to_plant_ms": stat(51_000, 40),
                 "attack_win_rate": stat(0.55, 70), "defense_win_rate": stat(0.6, 70), "pistol_win_rate": stat(0.6, 12, True),
                 "eco_win_rate": stat(0.22, 18),
                 "insights": [insight("o1", "weakness", "Rounds eco convertem 22%.", "eco_win_rate", 0.22, 0.15, 18, "ratio")]},
    "rounds": [plan_round(1, 1, "attack", "pistol", "loss"), plan_round(2, 1, "attack", "eco", "loss"),
               plan_round(3, 2, "defense", "pistol", "win"), plan_round(4, 2, "defense", "full_buy", "win")],
    "narrative_pt": None,
}

OUT.mkdir(parents=True, exist_ok=True)
missing = set(ENDPOINTS) - set(fixtures)
assert not missing, f"missing fixtures: {missing}"
for name, model in ENDPOINTS.items():
    model.model_validate(fixtures[name])  # raises on contract violation
    (OUT / f"{name}.json").write_text(json.dumps(fixtures[name], ensure_ascii=False, indent=2) + "\n")
print(f"wrote {len(fixtures)} fixtures to {OUT}")
