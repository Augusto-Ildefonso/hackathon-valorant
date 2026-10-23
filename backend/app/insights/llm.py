"""Optional LLM narrator for the Action Plan (layer 3). Owner: Stream D.

The rule-based planner decides everything: the plays, the numbers, the evidence. This module only asks the model to
rewrite the plan's text the way a coach would say it, strictly from the facts the planner produced. Safety:
* Google Gemini only: on whenever `GEMINI_API_KEY` (Google AI Studio) is set, in the environment or in the git-ignored
  `<repo>/.env` (`VAVAGYM_LLM=0` turns it off); without a key the app is complete with the rules alone;
* every number in a rewritten field must already appear in that round's input (references like "R5" must point to a
  real round), otherwise that field keeps the template text;
* any failure (network, timeout, bad JSON) leaves the plan untouched; results are cached on disk by input hash.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ..deps import REPO_ROOT
from ..schemas.plan import PlanResponse, RoundPlan

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
CACHE_DIR = REPO_ROOT / ".cache" / "llm"

SYSTEM = """Você é um analista de VALORANT que escreve o plano de um treinador em português do Brasil.
Receberá, em JSON, os fatos de cada round (já calculados a partir de partidas reais) e o texto-base do plano.
Regras obrigatórias:
- Use SOMENTE os fatos recebidos. Não invente números, jogadores, mapas, habilidades, posições ou táticas.
- Os fatos servem para você DECIDIR e entender o plano, não para serem recitados. Um treinador não lê estatísticas para o time: ele explica a estratégia. Portanto NÃO escreva percentuais, "n = ...", tamanhos de amostra, medianas nem taxas de vitória. Traduza o dado em orientação (ex.: em vez de "o adversário perde 61% das aberturas no site A", diga "o adversário é frágil na abertura do site A: vale forçar ali cedo").
- Pode usar números só como parte da instrução em si, exatamente como aparecem nos fatos do round: tempo de plante em segundos, número do site, número de jogadores. Não crie números novos nem faça contas. Outros rounds só como "R<número>", quando existirem no plano.
- Escreva a estratégia em detalhe, como um treinador no quadro tático: o plano do round em uma frase; quem abre o round e em que função (use os nomes e funções dos fatos); como o time entra, o ritmo e o momento do plante; como a equipe troca de posição ou protege o plante; o que fazer se a abertura falhar e como reagir ao movimento provável do adversário. Seja concreto e acionável, em frases curtas.
- O texto-base do plano é uma lista de evidências cheia de estatísticas: NÃO copie suas frases nem seus números. Reescreva cada ideia como instrução tática, sem a estatística que a sustenta (ex.: "o site A vence 80% das vezes (n = 10)" vira "o site A é a melhor aposta contra esta defesa").
- Compra e economia entram só como decisão (ex.: "compra completa, rifle e colete pesado"), sem recitar créditos.
- Se um fato indicar amostra baixa, trate como palpite do treinador (ex.: "aposta", "vale testar"), sem citar o tamanho da amostra.
- Tom impessoal: nunca fale com o leitor. Não use "você", "vocês", "seu", "sua", "seus", "suas", "te" nem "teu". Refira-se ao time pelo nome ou como "o time", "a equipe", "o adversário", e use a terceira pessoa ou frases impessoais (ex.: "o time ataca o site B", "convém priorizar o site A").
Responda apenas com JSON no formato:
{"rounds":[{"number":1,"strategy_summary":"...","strategy_steps":["..."],"enemy_summary":"...","contingency_won":"...","contingency_lost":"..."}],"narrative":"resumo, em até 4 frases, apenas dos rounds recebidos"}
"""

_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_ROUND_REF = re.compile(r"\bR\d+\b")


def _load_dotenv() -> None:
    """Read KEY=VALUE lines from `<repo>/.env` (git-ignored) into the environment; real env vars win. No dependency."""
    path = REPO_ROOT / ".env"
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_dotenv()


def api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None


def enabled() -> bool:
    return os.environ.get("VAVAGYM_LLM") != "0" and api_key() is not None  # on whenever a key exists; VAVAGYM_LLM=0 is the opt-out


def model_name() -> str:
    return gemini_models()[0]


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


_SECOND_PERSON = re.compile(r"\b(voc[êe]s?|seus?|suas?|teus?|tuas?|te|ti|contigo|convosco)\b", re.IGNORECASE)


_DIRECT_ADDRESS = re.compile(r"\b(voc[êe]s?|teus?|tuas?|te|ti|contigo|convosco)\b", re.IGNORECASE)


def addresses_reader(text: str, strict: bool = True) -> bool:
    """True when the text speaks to the reader ("você", "sua"): the app is impartial and its texts must stay impersonal.

    `strict` also flags "seu/sua": right for short insight cards, where it read as the reader's own stats. Long prose about a
    team (the printable plan) legitimately says "sua defesa" about the team, so it only rejects direct address."""
    return bool((_SECOND_PERSON if strict else _DIRECT_ADDRESS).search(text))


_STAT_TALK = re.compile(r"%|\bn\s*=|\bmediana\b|\bamostra\b", re.IGNORECASE)


def recites_stats(text: str) -> bool:
    """True when a coach text quotes percentages, sample sizes or medians: a coach explains the plan, not the data."""
    return bool(_STAT_TALK.search(text))


def valid(text: str, allowed: set[str], total_rounds: int, strict: bool = True) -> bool:
    return numbers_in(text) <= allowed and refs_ok(text, total_rounds) and not addresses_reader(text, strict) and not recites_stats(text)


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
RETRY_STATUS = (429, 500, 502, 503, 504)  # overload / rate limits are usually temporary
RETRY_WAIT_S = (2, 5)
CHUNK = 6  # rounds per model call
# Only these three models are used (project decision, 2026-10-22), tried in order unless a model is forced. The Flash Lite
# model is the fast one; the Gemma models have a separate quota pool, so they keep the feature alive when it is exhausted or
# overloaded (429/503), only slower (earlier benchmark on a 6-round chunk: Gemma 31B 88 s, Gemma 26B 132 s, valid JSON).
GEMINI_FALLBACKS = ("gemini-3.1-flash-lite", "gemma-4-31b-it", "gemma-4-26b-a4b-it")


def gemini_models() -> list[str]:
    forced = os.environ.get("VAVAGYM_LLM_MODEL")
    return [forced] if forced else list(GEMINI_FALLBACKS)


def _post(client, url: str, headers: dict, body: dict):
    """POST with a few retries on temporary errors (Gemini answers 503 "high demand" in spikes)."""
    resp = client.post(url, headers=headers, json=body)
    for wait in RETRY_WAIT_S:
        if resp.status_code not in RETRY_STATUS:
            break
        log.warning("LLM returned %s, retrying in %ss", resp.status_code, wait)
        time.sleep(wait)
        resp = client.post(url, headers=headers, json=body)
    resp.raise_for_status()
    return resp


def _complete(client, user: str, system: str = SYSTEM) -> str:
    return _complete_from(client, user, system, gemini_models())[0]


def _complete_from(client, user: str, system: str, models: list[str]) -> tuple[str, str]:
    """One Gemini generateContent call (JSON answer): (text, model that answered), trying `models` in order until one answers."""
    key = api_key()
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 32768, "temperature": 0.4}}  # thinking tokens count against it
    last: Exception | None = None
    for model in models:  # next model when this one is overloaded or retired for the key
        try:
            resp = _post(client, GEMINI_URL.format(model=model), {"x-goog-api-key": key, "content-type": "application/json"}, body)
            parts = resp.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought")), model
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            log.warning("Gemini model %s failed: %s", model, describe_error(e))
            last = e
            if status not in (*RETRY_STATUS, 404) and not isinstance(e, httpx.TransportError):  # timeouts / connection drops move on
                raise
    raise last  # type: ignore[misc]


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


log = logging.getLogger("vavagym.llm")


def describe_error(e: Exception) -> str:
    """Short pt-BR-friendly reason shown to the user and logged (never includes the API key)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            msg = resp.json().get("error", {}).get("message") or resp.text
        except ValueError:
            msg = resp.text
        return f"{resp.status_code}: {str(msg)[:200]}"
    return f"{type(e).__name__}: {str(e)[:200]}"


def _rewrite_half(client, plan: PlanResponse, rounds: list[RoundPlan], total_rounds: int, errors: list[str] | None = None) -> dict | None:
    facts = {"time": plan.team_a.name if plan.perspective == "a" else plan.team_b.name,
             "inimigo": plan.team_b.name if plan.perspective == "a" else plan.team_a.name, "mapa": plan.map.name,
             "rounds": [round_facts(r) for r in rounds]}
    user = json.dumps(facts, ensure_ascii=False)
    key = hashlib.sha256(f"{','.join(gemini_models())}|{SYSTEM}|{user}".encode()).hexdigest()

    def call():
        try:
            data = _parse(_complete(client, user))
        except Exception as e:  # network, auth, rate limit...: the plan keeps its template text
            log.warning("LLM call failed: %s", describe_error(e))
            if errors is not None:
                errors.append(describe_error(e))
            return None
        if data is None and errors is not None:
            errors.append("a resposta do modelo não veio em JSON")
        return data

    return _cached(key, call)


def generate_json(system: str, user: str, client=None) -> tuple[dict | None, str | None, bool]:
    """Generic structured call: (parsed JSON | None, error message | None, served from the disk cache). Never raises."""
    key = hashlib.sha256(f"{','.join(gemini_models())}|{system}|{user}".encode()).hexdigest()
    errors: list[str] = []
    hit = (Path(CACHE_DIR) / f"{key}.json").exists()

    def call():
        models = gemini_models()
        while models:  # a model that answers with malformed JSON is skipped like one that is overloaded
            try:
                text, used = _complete_from(client, user, system, models)
            except Exception as e:
                log.warning("LLM call failed: %s", describe_error(e))
                errors.append(describe_error(e))
                return None
            data = _parse(text)
            if data is not None:
                return data
            log.warning("Gemini model %s answered with malformed JSON", used)
            errors.append("a resposta do modelo não veio em JSON")
            models = models[models.index(used) + 1:]
        return None

    own = client is None
    try:
        client = client or httpx.Client(timeout=180)
        data = _cached(key, call)
    except Exception as e:
        return None, describe_error(e), False
    finally:
        if own and client is not None:
            client.close()
    return data, (None if data else (errors[0] if errors else None)), hit and data is not None


def _with_note(plan: PlanResponse, note: str) -> PlanResponse:
    return plan.model_copy(update={"notes_pt": [*plan.notes_pt, note]})


def narrate(plan: PlanResponse, client=None) -> PlanResponse:
    """Rewrite the plan's texts with the LLM where the number check passes. Never raises; says why when it cannot."""
    total = len(plan.rounds)
    own = client is None
    errors: list[str] = []
    try:
        client = client or httpx.Client(timeout=180)
        # chunks of CHUNK rounds, run in parallel: short generations finish well inside the timeout; only the first
        # chunk of each half contributes the narrative paragraph
        chunks: list[tuple[list[RoundPlan], bool]] = []
        for h in (1, 2):
            rs = [r for r in plan.rounds if r.half == h]
            chunks += [(rs[i:i + CHUNK], i == 0) for i in range(0, len(rs), CHUNK)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda c: (_rewrite_half(client, plan, c[0], total, errors), c[1]), chunks))
    except Exception as e:
        log.warning("LLM narrator failed: %s", describe_error(e))
        return _with_note(plan, f"Narrativa por IA indisponível ({describe_error(e)}).")
    finally:
        if own and client is not None:
            client.close()

    by_number: dict[int, dict] = {}
    narrative_parts: list[str] = []
    for res, first in results:
        if not res:
            continue
        for item in res.get("rounds", []):
            if isinstance(item, dict) and isinstance(item.get("number"), int):
                by_number[item["number"]] = item
        if first and isinstance(res.get("narrative"), str):
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
            if not isinstance(s, str) or not s.strip():
                return False
            return valid(s, ok, total)

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
    notes = list(plan.notes_pt)
    if errors:
        notes.append(f"Narrativa por IA incompleta: {errors[0]}")
    # fields the checks rejected silently keep the template text: no summary note (the plan stays complete either way)
    if not changed and narrative is None:
        return plan.model_copy(update={"notes_pt": notes}) if notes != plan.notes_pt else plan
    return plan.model_copy(update={"rounds": new_rounds, "narrative_pt": narrative, "text_source": "llm", "notes_pt": notes})
