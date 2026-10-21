"""LLM insight mode (Stream D): the model picks and words the insights, the code owns every number. Owner: D.

Flow: `insight_facts` computes a packet of facts with ids -> the model returns JSON insights that cite fact ids -> each
insight is validated (known ids, allowed kind, every number in the text equals a cited fact's value / reference / n) and
its evidence is filled FROM THE FACT, never from the text. Anything that fails validation is dropped and reported.
Off unless the LLM flag is on; callers fall back to the rule-based insights (`rules_*`) when this returns nothing.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from ..data.store import Store
from ..schemas.common import Evidence, Insight
from ..schemas.map import MapProfile
from ..schemas.match import MatchReport
from ..schemas.player import PlayerProfile
from ..schemas.team import TeamProfile
from . import insight_facts as IF
from . import llm
from . import thresholds as T
from .baselines import Baselines, get_baselines

KINDS = ("strength", "weakness", "tip", "strategy")
CAPS = {"strength": T.MAX_STRENGTHS, "weakness": T.MAX_WEAKNESSES, "tip": T.MAX_TIPS, "strategy": 2}
MAX_TEXT = 320

SYSTEM = """Você é um analista de VALORANT que escreve insights em português do Brasil a partir de fatos já calculados.
Receberá um JSON com o tipo de entidade e uma lista de fatos (id, rótulo, valor, n, referência, faixa).
Regras obrigatórias:
- Use SOMENTE os fatos recebidos. Cada número do texto deve ser exatamente o `valor`, a `referencia` ou o `n` de um fato que você citou (pode arredondar para inteiro). Não calcule diferenças, somas, razões nem percentuais novos.
- Cada insight cita de 1 a 3 `fact_ids` que o sustentam. Não cite números de fatos que você não citou.
- Tipos: strength (ponto forte), weakness (ponto fraco), tip (recomendação acionável apoiada nos fatos), strategy (tendência explorável ou estratégia).
- No máximo 3 strength, 3 weakness, 3 tip e 2 strategy; menos se os fatos não sustentarem mais. Não repita a mesma ideia.
- Priorize o que mais se afasta da referência e tem amostra suficiente. Fato com `amostra_baixa` NUNCA é strength nem weakness: só pode entrar como tip ou strategy, dizendo que a amostra é pequena (escreva "amostra pequena" ou "hipótese").
- `faixa` compara com os demais jogadores/times do campeonato; `referencia` é a mediana, ou a média do próprio jogador quando o rótulo disser.
- strength só para fato cuja faixa é "entre os 20% melhores" (ou, sem faixa, claramente acima da referência); weakness só para "entre os 20% piores" (ou claramente abaixo). Fato em "faixa intermediária" ou perto da referência NÃO é ponto forte nem fraco: no máximo tip ou strategy. Em rótulos "menor é melhor", valor acima da referência é ruim.
- Ao citar a faixa, escreva "entre os melhores" ou "entre os piores do campeonato", sem número.
- Não afirme o que os fatos não dizem (por exemplo "rounds econômicos" se o fato não fala de economia, ou "domínio" com poucos jogos).
- Você pode cruzar fatos (ex.: muitas aberturas vencidas mas poucas mortes trocadas) e deve explicar o porquê em uma frase.
- Não invente habilidades, lineups, posições, nomes nem táticas que os fatos não sustentem. Frases curtas, tom de analista.
Responda apenas com JSON: {"insights":[{"kind":"strength|weakness|tip|strategy","fact_ids":["id1","id2"],"text_pt":"..."}]}
"""

AUDIENCE = {
    "jogador": "Público: o próprio jogador e seu treinador. Pontos fortes, fraquezas e dicas de treino.",
    "time": "Público: a comissão técnica. Pontos fortes, fraquezas, melhorias e tendências que um adversário poderia explorar (strategy).",
    "mapa": "Público: analistas e times que vão jogar neste mapa. Viés de lado, sites, retake e pontos cegos como strategy ou tip.",
    "partida": 'Público: cada time no pós-jogo. Gere insights para os dois times e marque cada um com "time":"a" ou "time":"b" (campo extra obrigatório). Use só fatos do próprio time no insight dele (ids começam com "a:" ou "b:").',
}


@dataclass
class Run:
    """Result of one LLM insight request, with the audit trail used by the comparison script and the notes."""

    insights: list[Insight] = field(default_factory=list)
    by_team: dict[str, list[Insight]] = field(default_factory=dict)  # matches only
    requested: int = 0
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (text, reason)
    cited: list[list[str]] = field(default_factory=list)  # fact ids of each accepted insight
    violations: dict[str, str] = field(default_factory=dict)  # insight id -> coherence-guard reason (enforced when strict)
    cited_ids: dict[str, list[str]] = field(default_factory=dict)  # insight id -> cited fact ids
    error: str | None = None
    cached: bool = False
    seconds: float = 0.0
    n_facts: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.insights or any(self.by_team.values()))


GAP_NO_BAND = 0.15  # a fact without a band needs a relative gap of at least 15% from its reference to be a strength/weakness


def _guard(kind: str, text: str, cited: list[IF.Fact]) -> str | None:
    """Coherence checks the number check cannot do: is the claimed direction/size backed by the primary fact?"""
    low = [c for c in cited if c.low_sample]
    if low and kind in ("strength", "weakness"):
        return "amostra baixa usada como ponto forte/fraco"
    if low and not any(w in text.lower() for w in ("amostra", "hipótese", "hipotese")):
        return "amostra baixa sem aviso no texto"
    if kind in ("strength", "weakness"):
        f = cited[0]
        if f.band:
            want = "entre os 20% melhores" if kind == "strength" else "entre os 20% piores"
            if f.band != want:
                return f"{kind} sobre fato em '{f.band}'"
        elif f.baseline is not None:
            signed = (f.value - f.baseline) if f.better else (f.baseline - f.value)
            if (signed <= 0) == (kind == "strength"):
                return f"{kind} com direção contrária à referência"
            if abs(f.value - f.baseline) / max(abs(f.baseline), 1e-9) < GAP_NO_BAND:
                return f"{kind} com diferença menor que {GAP_NO_BAND:.0%} da referência"
    return None


def _allowed_numbers(facts: list[IF.Fact]) -> set[str]:
    out: set[str] = set()
    for f in facts:
        out |= llm.numbers_in(f.band or "")  # "20% melhores" may be echoed
        for x in (f.value, f.baseline, f.n):
            if x is None:
                continue
            for d in (0, 1, 2):
                out |= llm.numbers_in(f"{abs(x):.{d}f}")
    return out


def _convert(item: object, by_id: dict[str, IF.Fact], idx: int, match: bool) -> tuple[Insight | None, str | None, str | None, list[str]]:
    """(insight, team, rejection reason, cited ids) for one model item."""
    if not isinstance(item, dict):
        return None, None, "item não é objeto", []
    text = item.get("text_pt")
    kind = item.get("kind")
    ids = item.get("fact_ids")
    if kind not in KINDS:
        return None, None, f"tipo inválido ({kind})", []
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        return None, None, "texto vazio ou longo demais", []
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or not all(isinstance(i, str) and i in by_id for i in ids):
        return None, None, f"fact_ids inexistentes ({ids})", []
    team = item.get("time") if match else None
    if match:
        if team not in ("a", "b"):
            return None, None, "partida sem time a/b", []
        if not all(i.startswith(f"{team}:") for i in ids):
            return None, None, "cita fato do outro time", []
    cited = [by_id[i] for i in ids]
    extra = llm.numbers_in(text) - _allowed_numbers(cited)
    if extra:
        return None, None, f"números fora dos fatos citados: {sorted(extra)}", []
    f = cited[0]
    ev = Evidence(metric=f.label, value=round(f.value, 2), baseline=None if f.baseline is None else round(f.baseline, 2),
                  sample_size=f.n, unit=f.unit)
    return Insight(id=f"llm-{kind}-{idx}", kind=kind, text_pt=text.strip(), evidence=ev, low_sample=any(c.low_sample for c in cited)), team, None, list(ids)


def _violation(ins: Insight, ids: list[str], by_id: dict[str, IF.Fact]) -> str | None:
    return _guard(ins.kind, ins.text_pt, [by_id[i] for i in ids])


def _run(entity: str, name: str, facts: list[IF.Fact], extra: dict | None = None, client=None, strict: bool = True) -> Run:
    run = Run(n_facts=len(facts))
    if not llm.enabled() or not facts:
        run.error = "LLM desligado ou sem fatos"
        return run
    user = json.dumps({"tipo": entity, "nome": name, **(extra or {}), "fatos": [f.as_dict() for f in facts]}, ensure_ascii=False)
    t0 = time.time()
    data, err, hit = llm.generate_json(SYSTEM + "\n" + AUDIENCE[entity], user, client)
    run.seconds, run.cached, run.error = time.time() - t0, hit, err
    if not data or not isinstance(data.get("insights"), list):
        run.error = run.error or "resposta sem a lista de insights"
        return run
    by_id = {f.id: f for f in facts}
    match = entity == "partida"
    seen: set[tuple] = set()
    counts: dict[tuple, int] = {}
    buckets: dict[str, list[Insight]] = {"a": [], "b": []}
    for i, item in enumerate(data["insights"]):
        run.requested += 1
        ins, team, why, ids = _convert(item, by_id, i, match)
        if ins is None:
            run.rejected.append((str(item.get("text_pt", item))[:160] if isinstance(item, dict) else str(item)[:160], why or "?"))
            continue
        why_guard = _violation(ins, ids, by_id)
        if why_guard:
            run.violations[ins.id] = why_guard  # measured even when not enforced (comparison script)
            if strict:
                run.rejected.append((ins.text_pt[:160], f"guarda de coerência: {why_guard}"))
                continue
        key = (team, ins.kind, tuple(sorted(ids)))
        if key in seen:
            continue
        seen.add(key)
        ck = (team, ins.kind)
        if counts.get(ck, 0) >= CAPS[ins.kind]:
            continue
        counts[ck] = counts.get(ck, 0) + 1
        run.cited.append(ids)
        run.cited_ids[ins.id] = ids
        (buckets[team] if match else run.insights).append(ins)
    if match:
        run.by_team = {k: _ordered(v) for k, v in buckets.items()}
    else:
        run.insights = _ordered(run.insights)
    return run


def _ordered(items: list[Insight]) -> list[Insight]:
    return [i for k in KINDS for i in items if i.kind == k]


# ---- entry points ------------------------------------------------------------------------------------------------------
def for_player(p: PlayerProfile, base: Baselines | None = None, client=None, strict: bool = True) -> Run:
    return _run("jogador", p.player.riot_id, IF.player_facts(p, base or get_baselines()), client=client, strict=strict)


def for_team(t: TeamProfile, base: Baselines | None = None, client=None, strict: bool = True) -> Run:
    return _run("time", t.team.name, IF.team_facts(t, base or get_baselines()), client=client, strict=strict)


def for_map(m: MapProfile, store: Store | None = None, client=None, strict: bool = True) -> Run:
    return _run("mapa", m.map.name, IF.map_facts(m, store), client=client, strict=strict)


def for_match(r: MatchReport, client=None, strict: bool = True) -> Run:
    names = {"a": r.team_a.team.name, "b": r.team_b.team.name}
    return _run("partida", f"{names['a']} x {names['b']} em {r.map.name}", IF.match_facts(r), {"times": names}, client=client, strict=strict)
