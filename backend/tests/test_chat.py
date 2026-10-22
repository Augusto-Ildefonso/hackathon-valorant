"""Chat (Stream G): rule-based understanding over real names, blocks from the existing engines, dashboard links."""
import re
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from fastapi.testclient import TestClient

from app.chat.understand import names, understand_rules
from app.main import app
from app.schemas import ChatResponse

client = TestClient(app)


def ask(message, context=None):
    r = client.post("/api/chat", json={"message": message, "context": context})
    assert r.status_code == 200, r.text
    return ChatResponse.model_validate(r.json())  # the response honours the contract


@pytest.fixture(scope="module")
def nm(full_store):
    return names()


def kinds(resp):
    return [b.type for b in resp.blocks]


def test_player_question_returns_stats_with_sample_sizes_and_a_dashboard_link(nm):
    puuid, riot_id, _ = nm.players[0]
    r = ask(f"informações do jogador {riot_id}")
    assert r.intent == "player" and r.dashboard.path == f"/jogador/{puuid}" and r.context.player_puuid == puuid
    stats = next(b for b in r.blocks if b.type == "stats")
    assert all(i.sample_size for i in stats.items)


def test_accents_case_and_typos_are_forgiven(nm):
    team = nm.teams[0]
    assert ask(f"COMO ESTÁ O TIME {team.upper()}?").intent == "team"
    m = nm.maps[0]
    r = ask(f"detalhes do mapa {m[:-1]}")  # one letter missing
    assert r.intent == "map" and r.dashboard.path == f"/mapa/{m}"


def test_plan_question_keeps_the_order_of_the_teams_and_fills_the_deep_link(nm, full_store):
    from collections import Counter
    m = full_store.matches[full_store.matches.map_name == "Ascent"]
    (a, _), (b, _) = Counter(list(m.team_a) + list(m.team_b)).most_common(2)
    r = ask(f"quero um plano do {a} contra o {b} no mapa Ascent")
    assert r.intent == "plan" and "plan_summary" in kinds(r)
    q = parse_qs(urlparse(r.dashboard.path).query)
    assert (q["teamA"][0], q["teamB"][0], q["map"][0], q["run"][0]) == (a, b, "Ascent", "1")
    assert (r.context.team, r.context.team_b, r.context.map) == (a, b, "Ascent")


def test_plan_with_missing_pieces_asks_instead_of_guessing(nm):
    r = ask(f"plano contra o time {nm.teams[0]}")
    assert r.intent == "plan" and r.dashboard is None and "warning" not in kinds(r)
    text = " ".join(b.text for b in r.blocks if b.type == "text")
    assert "Faltou" in text and not re.search(r"\b(você|seu|sua)\b", text.lower())


def test_follow_up_uses_the_previous_context(full_store):
    from collections import Counter
    m = full_store.matches[full_store.matches.map_name == "Ascent"]
    (a, _), (b, _) = Counter(list(m.team_a) + list(m.team_b)).most_common(2)
    r1 = ask(f"plano do {a} contra o {b} no mapa Ascent")
    r2 = ask("e no Lotus?", r1.context.model_dump())
    assert r2.intent == "plan" and "Lotus" in r2.dashboard.path


def test_tournament_and_leaderboard_questions(nm):
    t = nm.tournaments[0]
    r = ask(f"resumo do campeonato {t['name']}")
    assert r.intent == "tournament" and unquote(r.dashboard.path) == f"/campeonatos?tournament={t['id']}" and "table" in kinds(r)
    assert ask("quais os melhores jogadores?").intent == "leaderboard"
    assert ask("resumo do campeonato").dashboard.path == "/campeonatos"


def test_unknown_and_help_are_explained_not_silent():
    r = ask("jogador xyzabcq")
    assert r.intent == "unknown" and r.blocks[0].type == "warning" and "xyzabcq" in r.blocks[0].text
    h = ask("oi")
    assert h.intent == "help" and h.dashboard is None
    assert ask("blá blá").intent == "help"  # not understood: says what it can do


def test_ambiguous_player_name_returns_choices(nm):
    base = {}
    for _, rid, _t in nm.players:
        base.setdefault(rid.split("#")[0].lower(), []).append(rid)
    dup = next((k for k, v in base.items() if len(v) > 1 and len(k) >= 3), None)
    if dup is None:
        pytest.skip("no two players share a name in this dataset")
    r = ask(f"jogador {dup}")
    assert "choices" in kinds(r) and all(o.send.startswith("jogador ") for o in r.blocks[0].options)


def test_every_dashboard_path_points_at_an_existing_route(nm):
    ok = re.compile(r"^/(jogador/[^/]+|time/[^/]+|mapa/[^/]+|partida/[^/]+|plano\?.+|campeonatos(\?.+)?)$")
    for s in (f"jogador {nm.players[0][1]}", f"time {nm.teams[0]}", f"mapa {nm.maps[0]}", f"última partida do {nm.teams[0]}", "resumo do campeonato"):
        d = ask(s).dashboard
        assert d and ok.match(d.path), (s, d)


def test_understanding_is_deterministic_and_needs_no_network(nm):
    a = understand_rules(f"plano contra {nm.teams[1]}", None)
    b = understand_rules(f"plano contra {nm.teams[1]}", None)
    assert a == b and a.source == "rules"
