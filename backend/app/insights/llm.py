"""Optional LLM narrator for the Action Plan (layer 3). Owner: Stream D.

The rule-based planner decides everything: the plays, the numbers, the evidence. This module only asks the model to
rewrite the plan's text the way a coach would say it, strictly from the facts the planner produced. Safety:
* off unless `VAVAGYM_LLM=1` and `ANTHROPIC_API_KEY` are set; the app is complete without it;
* every number in a rewritten field must already appear in that round's input (references like "R5" must point to a
  real round), otherwise that field keeps the template text;
* any failure (network, timeout, bad JSON) leaves the plan untouched; results are cached on disk by input hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ..deps import REPO_ROOT
from ..schemas.plan import PlanResponse, RoundPlan

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"
CACHE_DIR = REPO_ROOT / ".cache" / "llm"

SYSTEM = """Você é um analista de VALORANT que escreve o plano de um treinador em português do Brasil.
Receberá, em JSON, os fatos de cada round (já calculados a partir de partidas reais) e o texto-base do plano.
Regras obrigatórias:
- Use SOMENTE os fatos recebidos. Não invente números, jogadores, mapas, habilidades, posições ou táticas.
- Cada número do seu texto deve aparecer exatamente como nos fatos do mesmo round (ex.: "61%", "n = 40"). Não crie percentuais novos nem faça contas.
- Pode citar outros rounds apenas como "R<número>" quando o número existir no plano.
- Escreva como um treinador: o plano em uma frase, por que (2 a 3 fatos), quem faz o quê e o risco com o plano B.
- Se um fato indicar amostra baixa, diga que é uma hipótese.
Responda apenas com JSON no formato:
{"rounds":[{"number":1,"strategy_summary":"...","strategy_steps":["..."],"enemy_summary":"...","contingency_won":"...","contingency_lost":"..."}],"narrative":"resumo, em até 4 frases, apenas dos rounds recebidos"}
"""

_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_ROUND_REF = re.compile(r"\bR\d+\b")


def enabled() -> bool:
    return os.environ.get("VAVAGYM_LLM") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def model_name() -> str:
    return os.environ.get("VAVAGYM_LLM_MODEL", DEFAULT_MODEL)


# ---- number check -----------------------------------------------------------------------------------------------------
def numbers_in(text: str) -> set[str]:
    """Numbers of a text normalized to '.' decimals, without the trailing zeros ('61,0' == '61')."""
    out = set()
    for m in _NUM.findall(_ROUND_REF.sub("", text)):
        s = m.replace(",", ".")
        out.add(s.rstrip("0").rstrip(".") if "." in s else s)
    return out


def refs_ok(text: str, total_rounds: int) -> bool:
    return all(1 <= int(r[1:]) <= total_rounds for r in _ROUND_REF.findall(text))


def valid(text: str, allowed: set[str], total_rounds: int) -> bool:
    return numbers_in(text) <= allowed and refs_ok(text, total_rounds)


# ---- facts ------------------------------------------------------------------------------------------------------------
def round_facts(r: RoundPlan) -> dict:
    return {
        "number": r.number, "half": r.half, "lado": "ataque" if r.side == "attack" else "defesa", "tipo_de_round": r.round_type,
        "vitoria_estimada_pct": None if r.win_probability.value is None else round(r.win_probability.value * 100),
        "amostra": r.win_probability.sample_size, "economia": r.projected_economy.reasoning_pt,
        "compra": [b.reason_pt for b in r.buy], "estrategia_base": r.strategy.summary_pt, "passos_base": r.strategy.steps_pt,
        "site": r.strategy.site, "inimigo_base": r.enemy_probable_strategy.summary_pt,
        "pontos_fracos_do_inimigo": [w.text_pt for w in r.enemy_weak_points],
        "se_vencer": r.contingency.if_previous_won.summary_pt, "se_perder": r.contingency.if_previous_lost.summary_pt,
        "dicas": [i.text_pt for i in r.insights],
    }


def _allowed(facts: dict) -> set[str]:
    return numbers_in(json.dumps(facts, ensure_ascii=False))


# ---- API --------------------------------------------------------------------------------------------------------------
def _complete(client, user: str) -> str:
    resp = client.post(API_URL, headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                                         "content-type": "application/json"},
                       json={"model": model_name(), "max_tokens": 6000, "system": SYSTEM,
                             "messages": [{"role": "user", "content": user}]})
    resp.raise_for_status()
    return "".join(b.get("text", "") for b in resp.json()["content"] if b.get("type") == "text")


def _parse(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _cached(key: str, fn):
    path = Path(CACHE_DIR) / f"{key}.json"
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (OSError, ValueError):
        pass
    value = fn()
    if value is not None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False))
        except OSError:
            pass
    return value


def _rewrite_half(client, plan: PlanResponse, rounds: list[RoundPlan], total_rounds: int) -> dict | None:
    facts = {"time": plan.team_a.name if plan.perspective == "a" else plan.team_b.name,
             "inimigo": plan.team_b.name if plan.perspective == "a" else plan.team_a.name, "mapa": plan.map.name,
             "rounds": [round_facts(r) for r in rounds]}
    user = json.dumps(facts, ensure_ascii=False)
    key = hashlib.sha256(f"{model_name()}|{SYSTEM}|{user}".encode()).hexdigest()

    def call():
        try:
            return _parse(_complete(client, user))
        except Exception:  # network, auth, rate limit...: the plan keeps its template text
            return None

    return _cached(key, call)


def narrate(plan: PlanResponse, client=None) -> PlanResponse:
    """Rewrite the plan's texts with the LLM where the number check passes. Never raises."""
    total = len(plan.rounds)
    own = client is None
    try:
        client = client or httpx.Client(timeout=90)
        halves = [[r for r in plan.rounds if r.half == h] for h in (1, 2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda rs: _rewrite_half(client, plan, rs, total) if rs else None, halves))
    except Exception:
        return plan
    finally:
        if own and client is not None:
            client.close()

    by_number: dict[int, dict] = {}
    narrative_parts: list[str] = []
    for res in results:
        if not res:
            continue
        for item in res.get("rounds", []):
            if isinstance(item, dict) and isinstance(item.get("number"), int):
                by_number[item["number"]] = item
        if isinstance(res.get("narrative"), str):
            narrative_parts.append(res["narrative"])

    changed = False
    new_rounds: list[RoundPlan] = []
    for r in plan.rounds:
        item = by_number.get(r.number)
        if not item:
            new_rounds.append(r)
            continue
        ok = _allowed(round_facts(r))

        def good(s) -> bool:
            return isinstance(s, str) and s.strip() != "" and valid(s, ok, total)

        upd: dict = {}
        if good(item.get("strategy_summary")):
            upd["strategy"] = r.strategy.model_copy(update={"summary_pt": item["strategy_summary"].strip()})
        steps = item.get("strategy_steps")
        if isinstance(steps, list) and steps and all(good(s) for s in steps):
            upd["strategy"] = upd.get("strategy", r.strategy).model_copy(update={"steps_pt": [s.strip() for s in steps]})
        if good(item.get("enemy_summary")):
            upd["enemy_probable_strategy"] = r.enemy_probable_strategy.model_copy(update={"summary_pt": item["enemy_summary"].strip()})
        c = r.contingency
        if good(item.get("contingency_won")):
            c = c.model_copy(update={"if_previous_won": c.if_previous_won.model_copy(update={"summary_pt": item["contingency_won"].strip()})})
        if good(item.get("contingency_lost")):
            c = c.model_copy(update={"if_previous_lost": c.if_previous_lost.model_copy(update={"summary_pt": item["contingency_lost"].strip()})})
        if c is not r.contingency:
            upd["contingency"] = c
        if upd:
            changed = True
            r = r.model_copy(update=upd)
        new_rounds.append(r)

    narrative = " ".join(narrative_parts).strip() or None
    if narrative:
        everything = set()
        for r in plan.rounds:
            everything |= _allowed(round_facts(r))
        if not valid(narrative, everything, total):
            narrative = None
    if not changed and narrative is None:
        return plan
    return plan.model_copy(update={"rounds": new_rounds, "narrative_pt": narrative, "text_source": "llm"})
