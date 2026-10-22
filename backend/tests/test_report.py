"""Printable plan (Stream D): document builders, LLM validation, image slots and the PDF endpoint."""
import json
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.insights import llm, report
from app.insights.action_plan import build_plan
from app.insights.report_images import ImageBank, Picture, Strip
from app.insights.report_pdf import render_pdf
from app.main import app
from app.schemas import PlanRequest

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
        self.answer = answer

    def post(self, url, headers=None, json=None):  # noqa: A002
        return Resp(self.answer)


@pytest.fixture
def llm_on(monkeypatch, tmp_path):
    monkeypatch.delenv("VAVAGYM_LLM_MODEL", raising=False)
    monkeypatch.setenv("VAVAGYM_LLM", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path / "llm")


@pytest.fixture(scope="module")
def pair(full_store):
    m = full_store.matches[full_store.matches.map_name == "Ascent"]
    (a, _), (b, _) = Counter(list(m.team_a) + list(m.team_b)).most_common(2)
    return a, b


@pytest.fixture(scope="module")
def plan(full_store, pair):
    return build_plan(full_store, PlanRequest(team_a=pair[0], team_b=pair[1], map="Ascent", rounds_per_half=6))


@pytest.fixture(scope="module")
def bank(plan, full_store):
    return ImageBank(plan, full_store)


def test_image_slots_exist_and_resolve(plan, bank):
    assert {"map:overview", "agents", "buy:1"} <= set(bank.refs)
    assert isinstance(bank.resolve("map:overview"), Picture) and isinstance(bank.resolve("agents"), Strip)
    assert bank.resolve("buy:1").items and bank.resolve("nope") is None
    for ref in (k for k in bank.refs if k.startswith("enemy:")):
        pic = bank.resolve(ref)
        assert isinstance(pic, Picture) and pic.data[:4] == b"\x89PNG"


def test_rules_document_has_every_round_and_the_appendix_table(plan, full_store):
    doc, _ = report.build_document(plan, full_store, use_llm=False)
    assert doc.source == "rules" and doc.blocks[-1].kind == "table"
    assert len(doc.blocks[-1].rows) == len(plan.rounds) + 1  # header + one row per round
    assert sum(1 for b in doc.blocks if b.kind == "h3") == len(plan.rounds)


def test_pdf_is_a_real_multi_page_pdf(plan, full_store):
    doc, bank = report.build_document(plan, full_store, use_llm=False)
    pdf = render_pdf(doc, bank)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 20_000
    assert pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 3
    assert len(pdf) < 4_000_000  # catalog icons are downscaled, not embedded at 1024 px


def _doc(*sections):
    return json.dumps({"sections": [{"heading": h, "blocks": b} for h, b in sections]})


def test_llm_document_keeps_valid_blocks_and_drops_the_rest(plan, full_store, bank, llm_on):
    good = "O time abre o round com o entry e troca o primeiro abate; o plante sai por volta de 49 s."
    answer = _doc(
        ("Visão geral", [{"type": "paragraph", "text": good}, {"type": "image", "ref": "map:overview", "caption": "O mapa"},
                         {"type": "paragraph", "text": "O adversário perde 61% das aberturas."},          # statistic
                         {"type": "paragraph", "text": "Você deve entrar cedo."},                         # direct address
                         {"type": "paragraph", "text": "Use as smokes do agente para fechar o corredor."},  # utility: no data
                         {"type": "image", "ref": "map:inventado", "caption": "x"}]),                    # unknown slot
        ("Ataque", [{"type": "paragraph", "text": good}, {"type": "bullets", "items": [good, "Base de n = 40 rounds."]}]),
        ("Defesa", [{"type": "paragraph", "text": good + " Segue o plano do R3."}]),
    )
    doc, _ = report.build_document(plan, full_store, use_llm=True, client=Fake(answer))
    assert doc.source == "llm"
    texts = [t for b in doc.blocks for t in ([b.text] if b.text else b.items)]
    assert good in texts
    assert not any(w in " ".join(texts) for w in ("61%", "Você", "smokes", "n = 40"))
    assert ["image"] == [b.kind for b in doc.blocks if b.kind == "image"] and doc.blocks[-1].kind == "table"  # appendix always last


def test_possessives_about_the_team_are_fine_in_the_document(plan, full_store, llm_on):
    t = "A equipe mantém sua defesa compacta e protege a sua zona de plante até a chegada do reforço."
    answer = _doc(("Defesa", [{"type": "paragraph", "text": t}]), ("Ataque", [{"type": "paragraph", "text": t + " "}]), ("Fim", [{"type": "paragraph", "text": t + "."}]))
    doc, _ = report.build_document(plan, full_store, use_llm=True, client=Fake(answer))
    assert doc.source == "llm"


def test_unusable_llm_answer_falls_back_to_the_deterministic_document(plan, full_store, llm_on):
    for bad in ("não é json", _doc(("Só um", [{"type": "paragraph", "text": "O time ataca."}]))):
        doc, _ = report.build_document(plan, full_store, use_llm=True, client=Fake(bad))
        assert doc.source == "rules" and sum(1 for b in doc.blocks if b.kind == "h3") == len(plan.rounds)


def test_endpoint_returns_a_pdf_and_validates_the_request(pair):
    body = {"team_a": pair[0], "team_b": pair[1], "map": "Ascent", "rounds_per_half": 3}
    r = client.post("/api/plan/report", json=body)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content[:5] == b"%PDF-"
    assert r.headers["x-report-source"] == "rules" and ".pdf" in r.headers["content-disposition"]
    assert client.post("/api/plan/report", json={**body, "team_b": "Time Inexistente"}).status_code == 404
    assert client.post("/api/plan/report", json={**body, "team_b": pair[0]}).status_code == 422
