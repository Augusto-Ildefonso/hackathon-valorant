"""LLM insight mode (Stream D): fact packets, validation against the facts, evidence from facts, caps and fallbacks."""
import json

import pytest
from fastapi.testclient import TestClient

from app.analytics.matches import match_report
from app.analytics.players import player_profile
from app.analytics.teams import team_profile
from app.insights import engine, insight_facts as IF, llm, llm_insights
from app.insights.baselines import get_baselines
from app.main import app
from app.metrics import player_table, team_table

client = TestClient(app)


class Resp:
    status_code = 200

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": self.text}]}}]}


class Fake:
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def post(self, url, headers=None, json=None):  # noqa: A002
        self.calls += 1
        return Resp(self.answer(json) if callable(self.answer) else self.answer)


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.delenv("VAVAGYM_LLM_MODEL", raising=False)
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")


@pytest.fixture(scope="module")
def base(full_store):
    return get_baselines(full_store)


@pytest.fixture(scope="module")
def prof(full_store):
    pt = player_table(full_store)
    return player_profile(full_store, pt[pt.rounds >= 300].index[0], full_store)


def _facts(prof, base):
    return {f.id: f for f in IF.player_facts(prof, base)}


def _answer(*items):
    return json.dumps({"insights": list(items)})


def test_fact_packet_has_ids_values_and_bands(prof, base):
    f = _facts(prof, base)
    assert {"kd", "adr", "opening", "first_death", "rounds"} <= set(f)
    assert f["kd"].value == round(prof.stats.kd.value, 2) or abs(f["kd"].value - prof.stats.kd.value) < 0.01
    assert f["kd"].band in ("entre os 20% melhores", "entre os 20% piores", "faixa intermediária")
    assert f["kd"].baseline == base.players["kd"].median
    assert all(x.n >= 0 for x in f.values())


def test_valid_insight_gets_its_evidence_from_the_fact(prof, base):
    f = _facts(prof, base)
    text = f"K/D de {f['kd'].value:.2f} em {f['kd'].n} rounds.".replace(".", ",", 1)
    run = llm_insights.for_player(prof, base, client=Fake(_answer({"kind": "tip", "fact_ids": ["kd"], "text_pt": text})))
    assert len(run.insights) == 1 and not run.rejected
    ev = run.insights[0].evidence
    assert ev.value == round(f["kd"].value, 2) and ev.sample_size == f["kd"].n and ev.baseline == round(f["kd"].baseline, 2)
    assert run.insights[0].kind == "tip" and run.cited == [["kd"]]


def test_invented_numbers_unknown_ids_and_bad_kinds_are_rejected(prof, base):
    answer = _answer(
        {"kind": "strength", "fact_ids": ["kd"], "text_pt": "K/D de 9,99 absurdo."},
        {"kind": "weakness", "fact_ids": ["nao_existe"], "text_pt": "Fato inexistente."},
        {"kind": "magia", "fact_ids": ["kd"], "text_pt": "Tipo inválido."},
        {"kind": "tip", "fact_ids": [], "text_pt": "Sem fatos."},
        {"kind": "tip", "fact_ids": ["kd"], "text_pt": "x" * 400},
    )
    run = llm_insights.for_player(prof, base, client=Fake(answer))
    assert run.insights == [] and len(run.rejected) == 5
    reasons = " ".join(why for _, why in run.rejected)
    assert "números fora dos fatos" in reasons and "inexistentes" in reasons and "tipo inválido" in reasons


def test_numbers_must_come_from_the_cited_facts_not_from_others(prof, base):
    f = _facts(prof, base)
    other = f"{f['adr'].value:.0f}"
    run = llm_insights.for_player(prof, base, client=Fake(_answer(
        {"kind": "strength", "fact_ids": ["kd"], "text_pt": f"Causa {other} de dano por round."})))
    assert run.insights == []  # the ADR value is real but fact `adr` was not cited


def test_caps_duplicates_and_order(prof, base):
    items = [{"kind": "tip", "fact_ids": [fid], "text_pt": f"Dica sobre {fid}."} for fid in ("kd", "adr", "hs", "opening", "first_death", "rounds")]
    items += [{"kind": "strength", "fact_ids": ["adr"], "text_pt": "Bom dano."}, {"kind": "strength", "fact_ids": ["adr"], "text_pt": "Bom dano de novo."}]
    run = llm_insights.for_player(prof, base, client=Fake(_answer(*items)), strict=False)  # the guard has its own tests
    kinds = [i.kind for i in run.insights]
    assert kinds == ["strength", "tip", "tip", "tip"]  # strengths first, the repeated fact set dropped, at most 3 tips


def _fact_where(prof, base, pred):
    return next((f for f in IF.player_facts(prof, base) if pred(f)), None)


def test_guard_rejects_strength_on_a_middling_fact_but_reports_it_when_not_enforced(prof, base):
    mid = _fact_where(prof, base, lambda f: f.band == "faixa intermediária" and not f.low_sample)
    assert mid is not None
    item = {"kind": "strength", "fact_ids": [mid.id], "text_pt": f"Ponto forte em {mid.id}."}
    strict = llm_insights.for_player(prof, base, client=Fake(_answer(item)))
    assert strict.insights == [] and any("guarda de coerência" in why for _, why in strict.rejected)
    loose = llm_insights.for_player(prof, base, client=Fake(_answer(item)), strict=False)
    assert len(loose.insights) == 1 and loose.violations  # served only when not enforced, and flagged


def test_guard_accepts_strength_only_when_the_band_says_so(prof, base, monkeypatch, tmp_path):
    top = _fact_where(prof, base, lambda f: f.band == "entre os 20% melhores" and not f.low_sample)
    worst = _fact_where(prof, base, lambda f: f.band == "entre os 20% piores" and not f.low_sample)
    if top is not None:
        ok = {"kind": "strength", "fact_ids": [top.id], "text_pt": f"Entre os melhores em {top.id}."}
        bad = {"kind": "weakness", "fact_ids": [top.id], "text_pt": f"Fraqueza em {top.id}."}
        run = llm_insights.for_player(prof, base, client=Fake(_answer(ok, bad)))
        assert [i.kind for i in run.insights] == ["strength"]
    if worst is not None:
        monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "second")  # same facts => same cache key: start with an empty cache
        run = llm_insights.for_player(prof, base, client=Fake(_answer({"kind": "weakness", "fact_ids": [worst.id], "text_pt": f"Entre os piores em {worst.id}."})))
        assert [i.kind for i in run.insights] == ["weakness"]


def test_guard_low_sample_cannot_be_strength_and_needs_a_warning_in_tips(prof, base):
    low = _fact_where(prof, base, lambda f: f.low_sample and f.id.startswith("map:"))
    if low is None:
        pytest.skip("no low-sample map fact for this player")
    strength = {"kind": "strength", "fact_ids": [low.id], "text_pt": f"Domínio em {low.label}."}
    silent_tip = {"kind": "tip", "fact_ids": [low.id], "text_pt": f"Treine {low.label}."}
    warned_tip = {"kind": "tip", "fact_ids": [low.id], "text_pt": f"Hipótese: revise {low.label}, a amostra é pequena."}
    run = llm_insights.for_player(prof, base, client=Fake(_answer(strength, silent_tip, warned_tip)))
    assert [i.kind for i in run.insights] == ["tip"] and "Hipótese" in run.insights[0].text_pt and run.insights[0].low_sample


def test_the_band_number_may_be_echoed(prof, base):
    top = _fact_where(prof, base, lambda f: f.band == "entre os 20% melhores" and not f.low_sample)
    if top is None:
        pytest.skip("no top-band fact")
    run = llm_insights.for_player(prof, base, client=Fake(_answer({"kind": "strength", "fact_ids": [top.id], "text_pt": f"{top.label}: entre os 20% melhores."})))
    assert len(run.insights) == 1


def test_malformed_json_moves_on_to_the_next_model(prof, base, monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    good = _answer({"kind": "tip", "fact_ids": ["rounds"], "text_pt": "Mais rounds ajudam a confirmar a leitura."})
    tried = []

    class Picky:
        def post(self, url, headers=None, json=None):  # noqa: A002
            tried.append(url.split("/models/")[1].split(":")[0])
            return Resp("{ isto nao e json" if len(tried) == 1 else good)

    run = llm_insights.for_player(prof, base, client=Picky())
    assert len(tried) == 2 and tried[0] != tried[1] and len(run.insights) == 1 and run.error is None


def test_disabled_or_failed_llm_leaves_nothing(prof, base, monkeypatch):
    monkeypatch.setenv("VAVAGYM_LLM", "0")
    assert not llm_insights.for_player(prof, base, client=Fake("{}")).ok
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    run = llm_insights.for_player(prof, base, client=Fake("não é json"))
    assert not run.ok and run.error


def test_match_insights_are_per_team_and_cannot_cite_the_other_team(full_store):
    mid = full_store.matches.match_id.iloc[0]
    rep = match_report(full_store, mid)
    facts = {f.id: f for f in IF.match_facts(rep)}
    assert any(i.startswith("a:") for i in facts) and any(i.startswith("b:") for i in facts)
    ok = {"kind": "strength", "time": "a", "fact_ids": ["a:rounds_won"], "text_pt": f"Venceu {facts['a:rounds_won'].value:.0f} rounds."}
    wrong_team = {"kind": "weakness", "time": "a", "fact_ids": ["b:rounds_won"], "text_pt": "Cita o outro time."}
    no_team = {"kind": "tip", "fact_ids": ["a:rounds_won"], "text_pt": "Sem time."}
    run = llm_insights.for_match(rep, client=Fake(_answer(ok, wrong_team, no_team)))
    assert len(run.by_team["a"]) == 1 and run.by_team["b"] == [] and len(run.rejected) == 2


def test_blind_spot_facts_are_percentages_where_higher_is_worse(full_store):
    from app.analytics.maps import map_profile

    sm = full_store.where(map_name="Ascent")
    zones = [f for f in IF.map_facts(map_profile(sm, "Ascent"), sm) if f.id.startswith("zone:")]
    assert zones and all(f.unit == "%" and 0 <= f.value <= 100 and f.better is False and f.baseline is not None for f in zones)
    assert all(isinstance(f.as_dict()["n"], int) for f in zones)
    assert IF.Fact("x", "x", 13.0, 5).as_dict()["valor"] == 13  # a whole count is not shown as 13.0


def test_team_and_map_fact_packets(full_store, base):
    t = team_table(full_store).sort_values("matches").index[-1]
    facts = IF.team_facts(team_profile(full_store, t, full_store), base)
    ids = {f.id for f in facts}
    assert {"attack_wr", "defense_wr", "win_rate"} <= ids and len(ids) == len(facts)


def test_engine_wrapper_falls_back_to_rules_when_the_llm_returns_nothing(prof, monkeypatch):
    monkeypatch.setattr(llm_insights, "for_player", lambda *a, **k: llm_insights.Run())
    ins, source = engine.player_insights(prof, "llm")
    assert source == "rules" and ins == engine.for_player(prof)
    ins, source = engine.player_insights(prof, "rules")
    assert source == "rules"


def test_engine_wrapper_reports_llm_when_it_answers(prof, monkeypatch):
    fake = llm_insights.Run(insights=engine.for_player(prof)[:1] or [])
    monkeypatch.setattr(llm_insights, "for_player", lambda *a, **k: fake)
    if fake.insights:
        assert engine.player_insights(prof, "llm")[1] == "llm"


def test_endpoint_accepts_the_insights_param_and_reports_the_source(full_store, monkeypatch):
    pt = player_table(full_store)
    pid = pt[pt.rounds >= 300].index[0]
    r = client.get(f"/api/players/{pid}?insights=rules").json()
    assert r["insights_source"] == "rules"
    monkeypatch.setenv("VAVAGYM_LLM", "0")
    r = client.get(f"/api/players/{pid}?insights=llm").json()
    assert r["insights_source"] == "rules"  # LLM off: honest fallback
    assert client.get(f"/api/players/{pid}?insights=bogus").status_code == 422
