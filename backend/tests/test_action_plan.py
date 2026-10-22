"""Action Plan (Stream D): structure of the base scenario, validation, determinism and low-history fallbacks."""
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.insights.action_plan import build_plan
from app.main import app
from app.schemas import PlanRequest, PlanResponse

client = TestClient(app)


@pytest.fixture(scope="module")
def pair(full_store):
    m = full_store.matches[full_store.matches.map_name == "Ascent"]
    (a, _), (b, _) = Counter(list(m.team_a) + list(m.team_b)).most_common(2)
    return a, b


@pytest.fixture(scope="module")
def plan(full_store, pair):
    return build_plan(full_store, PlanRequest(team_a=pair[0], team_b=pair[1], map="Ascent", rounds_per_half=6))


def test_structure_of_the_base_scenario(plan):
    assert len(plan.rounds) == 12
    assert [r.number for r in plan.rounds] == list(range(1, 13))
    assert {r.half for r in plan.rounds[:6]} == {1} and {r.half for r in plan.rounds[6:]} == {2}
    assert all(r.side == plan.starting_side for r in plan.rounds[:6])
    assert all(r.side != plan.starting_side for r in plan.rounds[6:])
    assert [r.number for r in plan.rounds if r.round_type == "pistol"] == [1, 7]


def test_economy_is_within_game_limits(plan):
    for r in plan.rounds:
        e = r.projected_economy
        assert 0 < e.team_credits <= 9000 * 5 and 0 < e.enemy_credits <= 9000 * 5
        assert (e.team_credits == 4000) == (r.round_type == "pistol")  # 800 x 5 only on pistols
        assert 0 <= r.win_probability.value <= 1 and r.win_probability.sample_size >= 0


def test_every_round_is_filled(plan):
    for r in plan.rounds:
        assert 1 <= len(r.buy) <= 5 and r.strategy.summary_pt and r.enemy_probable_strategy.summary_pt
        assert r.base_scenario_result in ("win", "loss")
        assert r.contingency.if_previous_won.summary_pt and r.contingency.if_previous_lost.summary_pt
    after_pistol = plan.rounds[1]
    assert "R1" in after_pistol.contingency.if_previous_won.summary_pt


def test_people_are_named_and_numbers_cite_samples(plan):
    first = plan.rounds[0]
    text = " ".join(first.strategy.steps_pt)
    assert "n = " in text  # every claim carries its sample size
    assert any(b.role == "entry" for b in first.buy)
    assert plan.agents and plan.agents[0].agent.id and plan.opponent.team.name == plan.team_b.name
    assert any("lineups" in n for n in plan.notes_pt)


def _inside(p):
    return 0 <= p.x <= 1 and 0 <= p.y <= 1


def test_map_plan_attack_round_has_player_arrows(plan):
    mp = plan.rounds[0].map_plan
    assert mp is not None and {m.label for m in mp.markers if m.kind == "site"} >= {"A", "B"}
    arrows = [r for r in mp.routes if r.kind == "attack"]
    assert arrows and all(len(r.points) >= 2 and all(_inside(p) for p in r.points) and r.evidence.sample_size > 0 for r in arrows)
    assert all(r.handle and r.role for r in arrows)  # every arrow belongs to a named player and role
    assert any(r.kind == "enemy" for r in mp.routes)


def test_map_plan_defense_round_has_holds_and_retakes(plan):
    mp = next(r.map_plan for r in plan.rounds if r.side == "defense")
    assert any(m.kind == "hold" and m.handle for m in mp.markers)
    assert any(r.kind == "retake" and len(r.points) == 2 for r in mp.routes)
    for z in mp.zones:
        x0, y0, x1, y1 = z.box
        assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and z.evidence.sample_size > 0


def test_base_scenario_mixes_results_and_rotates_sites(plan):
    assert {r.base_scenario_result for r in plan.rounds} == {"win", "loss"}
    attack_sites = {r.strategy.site for r in plan.rounds if r.side == "attack" and r.round_type == "full_buy"}
    texts = " ".join(" ".join(r.strategy.steps_pt) for r in plan.rounds)
    assert "Sequência de" in texts or "Trocar de site" in texts or len(attack_sites) > 1  # momentum or rotation is spelled out
    assert len({r.strategy.summary_pt for r in plan.rounds}) > 3  # not the same sentence every round


def test_deterministic(full_store, pair, plan):
    again = build_plan(full_store, PlanRequest(team_a=pair[0], team_b=pair[1], map="Ascent", rounds_per_half=6))
    assert again.model_dump() == plan.model_dump()


def test_perspective_b_plans_for_the_other_team(full_store, pair):
    p = build_plan(full_store, PlanRequest(team_a=pair[0], team_b=pair[1], map="Ascent", perspective="b", rounds_per_half=3, starting_side="defense"))
    assert p.opponent.team.name == pair[0]
    assert p.rounds[0].side == "defense" and p.rounds[3].side == "attack"
    PlanResponse.model_validate(p.model_dump())


def test_team_with_little_history_falls_back_and_says_so(full_store, pair):
    m = full_store.matches
    counts = Counter(list(m[m.map_name == "Sunset"].team_a) + list(m[m.map_name == "Sunset"].team_b))
    rare = next(t for t in set(m.team_a) | set(m.team_b) if counts[t] == 0)
    p = build_plan(full_store, PlanRequest(team_a=rare, team_b=pair[1], map="Sunset", rounds_per_half=3))
    assert len(p.rounds) == 6 and any("partida" in n for n in p.notes_pt)


def test_endpoint_validation(pair):
    ok = {"team_a": pair[0], "team_b": pair[1], "map": "Ascent", "rounds_per_half": 2}
    assert client.post("/api/plan", json=ok).status_code == 200
    assert client.post("/api/plan", json={**ok, "team_b": pair[0]}).status_code == 422
    assert client.post("/api/plan", json={**ok, "team_b": "Time Inexistente"}).status_code == 404
    assert client.post("/api/plan", json={**ok, "map": "Atlantis"}).status_code == 404
    assert client.post("/api/plan", json={**ok, "rounds_per_half": 0}).status_code == 422
    assert client.post("/api/plan", json={**ok, "rounds_per_half": 16}).status_code == 422


def test_capabilities_off_with_opt_out(monkeypatch):
    monkeypatch.setenv("VAVAGYM_LLM", "0")
    assert client.get("/api/plan/capabilities").json() == {"llm": False, "model": None}
