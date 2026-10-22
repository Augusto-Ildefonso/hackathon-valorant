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
    def __init__(self, text, status=200, gemini=True):
        self._text, self.status_code, self._gemini = text, status, gemini

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(f"{self.status_code}", request=None, response=self)  # type: ignore[arg-type]

    @property
    def text(self):
        return self._text

    def json(self):
        if self.status_code >= 400:
            return {"error": {"message": f"fake error {self.status_code}"}}
        if self._gemini:
            return {"candidates": [{"content": {"parts": [{"text": self._text}]}}]}
        return {"content": [{"type": "text", "text": self._text}]}


class FakeClient:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def post(self, url, headers=None, json=None):  # noqa: A002 - mirrors httpx
        self.calls += 1
        return FakeResponse(self.answer(json) if callable(self.answer) else self.answer)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    for k in ("GOOGLE_API_KEY", "VAVAGYM_LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)  # a developer's real .env must not leak into the tests
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")


def test_on_with_a_key_off_with_opt_out_or_without_key(monkeypatch):
    assert llm.enabled()
    monkeypatch.setenv("VAVAGYM_LLM", "0")
    assert not llm.enabled()
    monkeypatch.delenv("VAVAGYM_LLM")
    assert llm.enabled()  # no flag needed any more
    monkeypatch.delenv("GEMINI_API_KEY")
    assert not llm.enabled()


def test_google_api_key_name_also_works_and_default_model_is_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.setenv("GOOGLE_API_KEY", "g2")
    assert llm.enabled() and llm.model_name().startswith("gemini")


def test_gemini_request_and_response_shape(monkeypatch, plan):
    seen = {}

    class GeminiClient:
        def post(self, url, headers=None, json=None):  # noqa: A002
            seen.update(url=url, headers=headers, body=json)
            return FakeResponse(_answer_for(plan), gemini=True)

    out = llm.narrate(plan, client=GeminiClient())
    assert "generativelanguage.googleapis.com" in seen["url"] and seen["headers"]["x-goog-api-key"] == "g"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert out.text_source == "llm" and out.rounds[0].strategy.summary_pt.endswith("Jogue junto.")


def test_dotenv_is_read_without_overriding_real_env(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("# comment\nGEMINI_API_KEY='from-file'\nVAVAGYM_LLM_MODEL=gemini-x\n")
    monkeypatch.setattr(llm, "REPO_ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY")  # the fixture sets one; the file may only fill what is missing
    monkeypatch.setenv("VAVAGYM_LLM_MODEL", "kept")
    llm._load_dotenv()
    import os

    assert os.environ["GEMINI_API_KEY"] == "from-file" and os.environ["VAVAGYM_LLM_MODEL"] == "kept"
    monkeypatch.delenv("GEMINI_API_KEY")  # tidy: setdefault wrote it outside monkeypatch's tracking


def test_number_check_is_format_tolerant():
    assert llm.valid("O plante sai por volta de 49 s.", {"49", "40"}, 12)
    assert llm.valid("O plante sai por volta de 49,0 s.", {"49"}, 12)
    assert not llm.valid("O plante sai por volta de 73 s.", {"61", "40"}, 12)
    assert llm.valid("Depois do R3, volte ao básico.", set(), 12)
    assert not llm.valid("Depois do R30, volte ao básico.", set(), 12)


def test_coach_text_must_not_recite_statistics():
    assert not llm.valid("O adversário perde 61% das aberturas no site A.", {"61"}, 12)
    assert not llm.valid("Base de n = 40 rounds mostra fragilidade.", {"40"}, 12)
    assert not llm.valid("Acima da mediana do campeonato.", set(), 12)
    assert llm.valid("O adversário é frágil na abertura do site A: vale forçar cedo e plantar por volta de 49 s.", {"49"}, 12)


def test_prompt_asks_for_strategy_not_data():
    assert "NÃO escreva percentuais" in llm.SYSTEM and "quem abre o round" in llm.SYSTEM


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
    assert out.rounds == plan.rounds and out.text_source == "rules" and out.narrative_pt is None
    assert any(n.startswith("Narrativa por IA") for n in out.notes_pt) or answer in ("[]", "{}")  # unparseable answers say why


def test_network_failure_never_raises(plan):
    class Boom:
        def post(self, *a, **k):
            raise RuntimeError("network down")

    out = llm.narrate(plan, client=Boom())
    assert out.rounds == plan.rounds and out.text_source == "rules"
    assert any("network down" in n for n in out.notes_pt)  # the reason reaches the user, not only the log


def test_temporary_errors_are_retried_then_succeed(plan, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    answers = iter([FakeResponse("", 503, True), FakeResponse("", 503, True)])
    calls = []

    class Flaky:
        def post(self, url, headers=None, json=None):  # noqa: A002
            calls.append(url)
            return next(answers, None) or FakeResponse(_answer_for(plan), gemini=True)

    out = llm.narrate(plan, client=Flaky())
    assert out.text_source == "llm" and len(calls) >= 3


def test_gemini_falls_back_to_the_next_model_when_one_is_gone(plan, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    tried = []

    class Retired:
        def post(self, url, headers=None, json=None):  # noqa: A002
            tried.append(url.split("/models/")[1].split(":")[0])
            return FakeResponse("", 404, True) if len(tried) == 1 or tried[-1] == tried[0] else FakeResponse(_answer_for(plan), gemini=True)

    out = llm.narrate(plan, client=Retired())
    assert tried[0] == llm.GEMINI_FALLBACKS[0] and llm.GEMINI_FALLBACKS[1] in tried and out.text_source == "llm"


def test_a_forced_model_is_the_only_one_tried(monkeypatch):
    monkeypatch.setenv("VAVAGYM_LLM_MODEL", "gemini-x")
    assert llm.gemini_models() == ["gemini-x"]
