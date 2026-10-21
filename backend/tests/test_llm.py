"""LLM narrator (Stream D): off by default, number check, per-field fallback, disk cache, never raises."""
import json
from collections import Counter

import pytest

from app.insights import llm
from app.insights.action_plan import build_plan
from app.schemas import PlanRequest


@pytest.fixture(scope="module")
def plan(full_store):
    m = full_store.matches[full_store.matches.map_name == "Ascent"]
    (a, _), (b, _) = Counter(list(m.team_a) + list(m.team_b)).most_common(2)
    return build_plan(full_store, PlanRequest(team_a=a, team_b=b, map="Ascent", rounds_per_half=2))


class FakeResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"content": [{"type": "text", "text": self._text}]}


class FakeClient:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def post(self, url, headers=None, json=None):  # noqa: A002 - mirrors httpx
        self.calls += 1
        return FakeResponse(self.answer(json) if callable(self.answer) else self.answer)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")


def test_disabled_without_flag_or_key(monkeypatch):
    monkeypatch.delenv("VAVAGYM_LLM")
    assert not llm.enabled()
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert not llm.enabled()


def test_number_check_is_format_tolerant():
    assert llm.valid("Vence 61% dos rounds (n = 40).", {"61", "40"}, 12)
    assert llm.valid("Vence 61,0% dos rounds.", {"61"}, 12)
    assert not llm.valid("Vence 73% dos rounds.", {"61", "40"}, 12)
    assert llm.valid("Depois do R3, volte ao básico.", set(), 12)
    assert not llm.valid("Depois do R30, volte ao básico.", set(), 12)


def _answer_for(plan, **overrides):
    r = plan.rounds[0]
    item = {"number": 1, "strategy_summary": r.strategy.summary_pt + " Jogue junto.", "strategy_steps": r.strategy.steps_pt,
            "enemy_summary": r.enemy_probable_strategy.summary_pt, "contingency_won": r.contingency.if_previous_won.summary_pt,
            "contingency_lost": r.contingency.if_previous_lost.summary_pt}
    item.update(overrides)
    return json.dumps({"rounds": [item], "narrative": "Plano de jogo equilibrado, com foco em trocas."})


def test_valid_rewrite_is_applied_and_marked(plan):
    client = FakeClient(_answer_for(plan))
    out = llm.narrate(plan, client=client)
    assert out.text_source == "llm" and out.narrative_pt
    assert out.rounds[0].strategy.summary_pt.endswith("Jogue junto.")
    assert out.rounds[1].strategy.summary_pt == plan.rounds[1].strategy.summary_pt  # no answer for round 2: untouched


def test_invented_number_keeps_the_template_text(plan):
    client = FakeClient(_answer_for(plan, strategy_summary="Vitória garantida: 99% de chance.", strategy_steps=["O inimigo perde 87% das aberturas."]))
    out = llm.narrate(plan, client=client)
    assert out.rounds[0].strategy.summary_pt == plan.rounds[0].strategy.summary_pt
    assert out.rounds[0].strategy.steps_pt == plan.rounds[0].strategy.steps_pt


def test_invented_number_in_the_narrative_drops_only_the_narrative(plan):
    answer = json.loads(_answer_for(plan))
    answer["narrative"] = "O time vence 7,77% dos rounds."
    out = llm.narrate(plan, client=FakeClient(json.dumps(answer)))
    assert out.narrative_pt is None and out.rounds[0].strategy.summary_pt.endswith("Jogue junto.")


def test_cache_avoids_a_second_call(plan):
    client = FakeClient(_answer_for(plan))
    llm.narrate(plan, client=client)
    first = client.calls
    assert first >= 1
    llm.narrate(plan, client=client)
    assert client.calls == first


@pytest.mark.parametrize("answer", ["not json", "[]", "{}", ""])
def test_bad_answers_leave_the_plan_untouched(plan, answer):
    out = llm.narrate(plan, client=FakeClient(answer))
    assert out.model_dump() == plan.model_dump()


def test_network_failure_never_raises(plan):
    class Boom:
        def post(self, *a, **k):
            raise RuntimeError("network down")

    assert llm.narrate(plan, client=Boom()).model_dump() == plan.model_dump()
