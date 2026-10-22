"""Optional LLM help for the chat. Both uses are guarded: the offline understanding stays the fallback, and a summary is
only shown when it passes the same checks as the plan narrator (no invented numbers, no statistics, no "você").
"""
from __future__ import annotations

import json

from ..insights import llm
from ..insights.report import _UTILITY_TALK
from ..routers.meta import _norm
from ..schemas.chat import Block, ChatContext
from .understand import Names, Understood, _fuzzy, _map_in, _players_in, _teams_in, _tournament_in, names

INTENTS = ("player", "team", "map", "match", "plan", "tournament", "leaderboard", "help")
SUMMARY_INTENTS = {"player", "team", "map", "match", "plan", "tournament", "leaderboard"}

UNDERSTAND_SYSTEM = """Você classifica perguntas de um chat de análise de partidas de VALORANT (torneios universitários brasileiros).
Responda SOMENTE um JSON: {"intent": ..., "player": ..., "team": ..., "team_b": ..., "map": ..., "tournament": ...}.
intent: "player" (informações de um jogador), "team" (informações de um time), "map" (detalhes de um mapa), "match" (última partida de um time),
"plan" (plano de ação de um time contra outro em um mapa), "tournament" (resumo de um campeonato), "leaderboard" (melhores jogadores/times),
"help" (cumprimento, ajuda ou pergunta fora do escopo).
Preencha os campos com o texto que a pessoa escreveu, corrigindo a grafia quando houver um nome parecido nas listas dadas; use null quando não houver.
Em "plan", "team" é o time que recebe o plano e "team_b" o adversário. Não invente nomes que a pessoa não citou."""


def _norm_s(s: str | None) -> str:
    return " " + _norm(s or "").strip() + " "


def _resolve(data: dict, nm: Names) -> Understood | None:
    """Turn the model's raw fields into real entities; anything that does not resolve makes the whole answer unusable."""
    intent = data.get("intent")
    if intent not in INTENTS:
        return None
    u = Understood(intent=intent, source="llm")  # type: ignore[arg-type]
    for key in ("team", "team_b"):
        raw = data.get(key)
        if not raw:
            continue
        t = _teams_in(_norm_s(raw), nm) or _fuzzy(_norm(raw), {_norm(x): x for x in nm.teams}, set())[:1]
        if not t:
            return None
        u.teams.append(t[0])  # type: ignore[arg-type]
    if data.get("player"):
        p = _players_in(_norm_s(data["player"]), nm) or _fuzzy(_norm(data["player"]), {_norm(x[1].split("#")[0]): x for x in nm.players}, set())[:1]
        if not p:
            return None
        u.players = list(p)  # type: ignore[arg-type]
    if data.get("map"):
        u.map = _map_in(_norm_s(data["map"]), nm) or next(iter(_fuzzy(_norm(data["map"]), {_norm(x): x for x in nm.maps}, set())), None)  # type: ignore[assignment]
        if not u.map:
            return None
    if data.get("tournament"):
        u.tournament = _tournament_in(_norm_s(data["tournament"]), nm)
    need = {"player": bool(u.players), "team": bool(u.teams), "map": bool(u.map), "match": bool(u.teams),
            "plan": len(u.teams) >= 1, "tournament": True, "leaderboard": True, "help": True}
    return u if need[intent] else None


def understand_llm(message: str, ctx: ChatContext | None, client=None) -> Understood | None:
    if not llm.enabled():
        return None
    nm = names()
    user = json.dumps({"pergunta": message, "contexto": ctx.model_dump(exclude_none=True) if ctx else {}, "times": nm.teams, "mapas": nm.maps,
                       "campeonatos": [t["name"] for t in nm.tournaments]}, ensure_ascii=False)
    data, _err, _hit = llm.generate_json(UNDERSTAND_SYSTEM, user, client)
    return _resolve(data, nm) if isinstance(data, dict) else None


SUMMARY_SYSTEM = """Você é um analista de VALORANT escrevendo um resumo curto para um painel.
Receberá fatos já calculados. Escreva de 2 a 3 frases em português do Brasil que interpretam o que se destaca e o que isso significa taticamente.
Regras: tom impessoal, em terceira pessoa, sem nunca falar com o leitor (nada de "você", "seu", "sua"); NÃO cite números, porcentagens, médias ou tamanhos de amostra;
use apenas nomes e fatos presentes nos dados; não invente táticas de habilidades nem posições. Responda SOMENTE um JSON: {"resumo": "..."}."""


def facts_from(blocks: list[Block]) -> list[str]:
    out: list[str] = []
    for b in blocks:
        if b.type in ("text", "warning"):
            out.append(b.text)
        elif b.type == "stats":
            out += [f"{i.label}: {i.value}" + (f" (n = {i.sample_size})" if i.sample_size else "") for i in b.items]
        elif b.type == "insights":
            out += [f"{b.title}: {i.text_pt}" for i in b.items]
        elif b.type == "table":
            out += [(b.title or "Tabela") + ": " + " | ".join(r) for r in b.rows]
        elif b.type == "plan_summary":
            out += [f"Round {r.number} ({r.side}, {r.round_type}): {r.summary_pt}" for r in b.rounds] + [f"Ponto fraco do adversário: {w.text_pt}" for w in b.weak_points]
    return out


def summarize(intent: str, blocks: list[Block], client=None) -> tuple[str | None, str | None]:
    """(summary | None, note). Never raises; the text must pass the plan narrator's checks or it is dropped."""
    if not llm.enabled() or intent not in SUMMARY_INTENTS:
        return None, None
    facts = facts_from(blocks)
    if not facts:
        return None, None
    data, err, _ = llm.generate_json(SUMMARY_SYSTEM, json.dumps({"tipo": intent, "fatos": facts}, ensure_ascii=False), client)
    text = data.get("resumo") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        return None, (f"Resumo por IA indisponível: {err}" if err else None)
    allowed = llm.numbers_in(json.dumps(facts, ensure_ascii=False))
    if not llm.valid(text, allowed, 30) or _UTILITY_TALK.search(text):  # the dataset has no utility data: such tactics would be invented
        return None, None  # silently keep the plain answer: the rejected text is never shown
    return text.strip(), None
