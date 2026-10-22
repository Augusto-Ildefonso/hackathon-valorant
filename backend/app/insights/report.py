"""Printable Action Plan (Stream D): a text-first dossier, not a copy of the web page.

Flow: the plan's facts and the list of available image slots go to the LLM, which writes the document as JSON blocks
(headings, paragraphs, bullets and image PLACEHOLDERS such as "enemy:B"); `report_images` fills the slots and
`report_pdf` lays everything out. The same checks as the coach narrative apply (every number must exist in the plan,
no statistics recited, impersonal tone), and a deterministic document is used when the LLM is off or fails, so the
export always works. A compact round-by-round table is always appended by code, never written by the model.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..data.store import Store
from ..schemas.plan import PlanResponse
from . import llm
from .report_images import ImageBank

MAX_PARAGRAPH = 900
MAX_BULLET = 320
MAX_CAPTION = 140
MAX_HEADING = 80
MIN_PARAGRAPHS = 3  # fewer surviving paragraphs than this and the model's document is not used
ROUND_TYPE_PT = {"pistol": "Pistol", "eco": "Eco", "semi_eco": "Semi-eco", "force": "Force", "full_buy": "Full buy"}


@dataclass
class Block:
    kind: str  # h1 h2 h3 p bullets image table
    text: str = ""
    items: list[str] = field(default_factory=list)
    ref: str = ""
    caption: str = ""
    rows: list[list[str]] = field(default_factory=list)  # table: header row first
    widths: list[float] = field(default_factory=list)    # table column weights


@dataclass
class Document:
    title: str
    subtitle: str
    meta: list[str]
    blocks: list[Block] = field(default_factory=list)
    source: str = "rules"  # "llm" when the model wrote the body
    note: str | None = None


# ---- deterministic body -------------------------------------------------------------------------------------------------
def _names(plan: PlanResponse) -> tuple[str, str]:
    mine, enemy = (plan.team_a, plan.team_b) if plan.perspective == "a" else (plan.team_b, plan.team_a)
    return mine.name, enemy.name


def _header(plan: PlanResponse) -> tuple[str, str, list[str]]:
    mine, enemy = _names(plan)
    side = "ataque" if plan.starting_side == "attack" else "defesa"
    return (f"Plano de ação: {mine} x {enemy}", f"{plan.map.name} · visão de {mine}",
            [f"{plan.rounds_per_half * 2} rounds ({plan.rounds_per_half} por tempo)", f"Começa no {side}", "Gerado pelo VaváGym a partir de partidas reais"])


def _round_title(r) -> str:
    return f"R{r.number} · {'Ataque' if r.side == 'attack' else 'Defesa'} · {ROUND_TYPE_PT.get(r.round_type, r.round_type)}"


def rules_body(plan: PlanResponse, bank: ImageBank) -> list[Block]:
    mine, enemy = _names(plan)
    b: list[Block] = [Block("h1", "Visão geral")]
    side = "ataque" if plan.starting_side == "attack" else "defesa"
    b.append(Block("p", f"Plano round a round de {mine} contra {enemy} em {plan.map.name}, com {plan.rounds_per_half * 2} rounds começando no {side}. "
                        "O cenário base distribui as vitórias pela probabilidade de cada round; a contingência de cada round mostra o que muda se o resultado for outro."))
    if "map:overview" in bank.refs:
        b.append(Block("image", ref="map:overview", caption=f"{plan.map.name} e seus sites"))
    elif not plan.map.has_minimap:
        b.append(Block("p", f"Observação: {plan.map.name} não tem minimapa no catálogo fornecido, por isso este documento não traz imagens de mapa."))
    if plan.agents:
        b.append(Block("h1", "Agentes recomendados"))
        if "agents" in bank.refs:
            b.append(Block("image", ref="agents"))
        b.append(Block("bullets", items=[f"{a.agent.name or 'Agente desconhecido'}" + (f" ({a.role})" if a.role else "") + f": {a.reason_pt}" for a in plan.agents]))
    o = plan.opponent
    b.append(Block("h1", f"Leitura do adversário: {enemy}"))
    if o.insights:
        b.append(Block("bullets", items=[i.text_pt for i in o.insights]))
    for ref in sorted(k for k in bank.refs if k.startswith("enemy:")):
        b.append(Block("image", ref=ref, caption=f"Caminho provável do adversário rumo ao site {ref.split(':')[1]}"))
    b.append(Block("h1", "Plano round a round"))
    for half, title in ((1, "Primeiro tempo"), (2, "Segundo tempo")):
        rounds = [r for r in plan.rounds if r.half == half]
        if not rounds:
            continue
        b.append(Block("h2", title))
        for r in rounds:
            b.append(Block("h3", _round_title(r)))
            if f"buy:{r.number}" in bank.refs:
                b.append(Block("image", ref=f"buy:{r.number}"))
            b.append(Block("p", r.strategy.summary_pt))
            if r.strategy.steps_pt:
                b.append(Block("bullets", items=list(r.strategy.steps_pt)))
            b.append(Block("p", f"Adversário: {r.enemy_probable_strategy.summary_pt}"))
            b.append(Block("p", f"Se o round anterior for vencido: {r.contingency.if_previous_won.summary_pt} "
                                f"Se for perdido: {r.contingency.if_previous_lost.summary_pt}"))
    return b


def appendix(plan: PlanResponse) -> list[Block]:
    """Compact round table, written by code in both modes."""
    rows = [["R", "Lado", "Tipo", "Site", "Compra", "Plano"]]
    for r in plan.rounds:
        weapons: dict[str, int] = {}
        for it in r.buy:
            w = (it.weapon.name or "Arma desconhecida") if it.weapon else "sem arma"
            weapons[w] = weapons.get(w, 0) + 1
        rows.append([str(r.number), "ATQ" if r.side == "attack" else "DEF", ROUND_TYPE_PT.get(r.round_type, r.round_type), r.strategy.site or "-",
                     ", ".join(f"{k} x{v}" if v > 1 else k for k, v in weapons.items()), r.strategy.summary_pt])
    return [Block("h1", "Apêndice: resumo round a round"), Block("table", rows=rows, widths=[0.5, 0.8, 1.1, 0.6, 2.4, 6.0])]


# ---- LLM body ----------------------------------------------------------------------------------------------------------
SYSTEM = """Você é o analista-chefe de um time de VALORANT e escreve o dossiê impresso do plano de jogo, em português do Brasil.
Receberá, em JSON, os fatos do plano round a round (já calculados de partidas reais), os agentes, o adversário e a lista de imagens disponíveis (`imagens`).
Escreva um documento de leitura corrida e detalhado, como um treinador que entrega o playbook ao time, em seções, e posicione imagens nos lugares onde ajudam a entender o texto.
Regras obrigatórias:
- Use SOMENTE os fatos recebidos. Não invente números, jogadores, agentes, mapas, habilidades, lineups, posições nem táticas.
- Estratégia, não dados: NÃO escreva percentuais, "n = ...", medianas, taxas de vitória nem tamanhos de amostra. Traduza cada dado em orientação ("o adversário é frágil na abertura do site A: vale forçar ali cedo"). Números só como parte da instrução, exatamente como nos fatos (segundos de plante, site, número de rounds, "R<número>").
- Tom impessoal: nunca fale com o leitor ("você", "seu", "sua", "te"). Use o nome do time, "o time", "a equipe", "o adversário", terceira pessoa ou frases impessoais ("convém priorizar o site A").
- Estrutura sugerida (adapte): 1) Visão geral e identidade do plano; 2) Leitura do adversário; 3) Agentes e funções; 4) Plano de ataque, por fases (pistol, eco/force, full buy); 5) Plano de defesa; 6) Rounds-chave e contingências (cite como "R5"); 7) Checklist de execução (antes do round, durante, pós-plante). Cada seção com 1 a 4 blocos.
- Profundidade: é um dossiê para estudar, não um resumo. Escreva de 1.800 a 3.000 palavras no total, com pelo menos 8 seções e 2 a 4 parágrafos por seção principal (4 a 6 frases cada), mais listas onde ajudarem. O plano de ataque e o de defesa têm, cada um, uma seção própria dividida por fases do jogo (pistol, eco e force, full buy, rounds contra compra fraca), dizendo o que cada fase pede, quem faz o quê e como o ritmo muda ao longo dos 12 rounds do tempo. Cite pelo menos 6 rounds específicos pelo número ("R5") com o que fazer neles e a contingência de vencer ou perder o anterior.
- Use as imagens: coloque `map:overview` na visão geral, `enemy:<site>` (todas as disponíveis) na leitura do adversário, `agents` na seção de agentes e alguns `buy:<n>` nos rounds que você detalhar. Cada imagem com legenda curta que diga o que olhar.
- Seja concreto e acionável: quem abre o round e em que função, ritmo de entrada, momento do plante, trocas, proteção do plante, plano B e como reagir ao movimento provável do adversário. Economia e compra entram só como decisão, sem créditos.
- Não há dados de utilitários, habilidades, smokes, flashes, ultimates nem lineups: NÃO escreva sobre eles. Fale de posição, ritmo, funções, trocas, economia e rotações.
- Se um fato tiver amostra baixa, trate como aposta ("vale testar"), sem citar a amostra.
- Imagens: use apenas referências da lista `imagens`, no máximo uma vez cada, em blocos {"type":"image","ref":"...","caption":"legenda curta"}. Não descreva a imagem no texto como se o leitor a visse sem ela.
- Limites: parágrafo até 900 caracteres, item de lista até 320, legenda até 140, título de seção até 80.
Responda apenas com JSON: {"sections":[{"heading":"...","blocks":[{"type":"paragraph","text":"..."},{"type":"bullets","items":["..."]},{"type":"image","ref":"enemy:B","caption":"..."}]}]}
"""


def _packet(plan: PlanResponse, bank: ImageBank) -> dict:
    mine, enemy = _names(plan)
    o = plan.opponent
    return {
        "time_do_plano": mine, "adversario": enemy, "mapa": plan.map.name, "rounds_por_tempo": plan.rounds_per_half,
        "comeca_no": "ataque" if plan.starting_side == "attack" else "defesa",
        "agentes": [{"agente": a.agent.name or "Agente desconhecido", "funcao": a.role, "motivo": a.reason_pt} for a in plan.agents],
        "perfil_do_adversario": {
            "site_preferido": o.preferred_site, "tempo_medio_ate_plantar_s": None if o.avg_time_to_plant_ms.value is None else round(o.avg_time_to_plant_ms.value / 1000),
            "leituras": [i.text_pt for i in o.insights]},
        "rounds": [llm.round_facts(r) for r in plan.rounds],
        "imagens": bank.refs,
    }


def _allowed_numbers(plan: PlanResponse) -> set[str]:
    nums: set[str] = set(str(i) for i in range(1, plan.rounds_per_half * 2 + 1))
    nums.add(str(plan.rounds_per_half))
    for r in plan.rounds:
        nums |= llm._allowed(llm.round_facts(r))
    o = plan.opponent
    nums |= llm.numbers_in(json.dumps([i.text_pt for i in o.insights] + [a.reason_pt for a in plan.agents], ensure_ascii=False))
    if o.avg_time_to_plant_ms.value is not None:
        nums.add(str(round(o.avg_time_to_plant_ms.value / 1000)))
    return nums


# The files carry no utility, ability or lineup data, so a document that tells the team how to use them is inventing tactics.
_UTILITY_TALK = re.compile(r"utilit[áa]ri|habilidade|\bsmokes?\b|\bflash(es|ar)?\b|molotov|lineup|\bdrones?\b|\bdardos?\b|\bultimate|\bultimates\b|\bskills?\b", re.IGNORECASE)


def _clean(text, limit: int, allowed: set[str], total: int) -> str | None:
    if not isinstance(text, str):
        return None
    t = re.sub(r"\s+", " ", text).strip()
    if not t or len(t) > limit or not llm.valid(t, allowed, total, strict=False) or _UTILITY_TALK.search(t):
        return None
    return t


def validate_sections(data: object, plan: PlanResponse, bank: ImageBank) -> tuple[list[Block], int]:
    """Blocks the model proposed that pass every check, and how many were dropped."""
    sections = data.get("sections") if isinstance(data, dict) else None
    if not isinstance(sections, list):
        return [], 0
    allowed, total = _allowed_numbers(plan), plan.rounds_per_half * 2
    out: list[Block] = []
    dropped, used_refs = 0, set()
    for sec in sections[:16]:
        heading = _clean(sec.get("heading") if isinstance(sec, dict) else None, MAX_HEADING, allowed, total)
        blocks = sec.get("blocks") if isinstance(sec, dict) else None
        if not heading or not isinstance(blocks, list):
            dropped += 1
            continue
        body: list[Block] = []
        for bl in blocks[:12]:
            kind = bl.get("type") if isinstance(bl, dict) else None
            if kind == "paragraph":
                t = _clean(bl.get("text"), MAX_PARAGRAPH, allowed, total)
                if t:
                    body.append(Block("p", t))
                    continue
            elif kind == "bullets" and isinstance(bl.get("items"), list):
                items = [t for t in (_clean(i, MAX_BULLET, allowed, total) for i in bl["items"][:12]) if t]
                if items:
                    body.append(Block("bullets", items=items))
                    continue
            elif kind == "image" and bl.get("ref") in bank.refs and bl["ref"] not in used_refs:
                cap = _clean(bl.get("caption"), MAX_CAPTION, allowed, total) or ""
                used_refs.add(bl["ref"])
                body.append(Block("image", ref=bl["ref"], caption=cap))
                continue
            dropped += 1
        if any(x.kind in ("p", "bullets") for x in body):
            out += [Block("h1", heading), *body]
    return out, dropped


def llm_body(plan: PlanResponse, bank: ImageBank, client=None) -> tuple[list[Block] | None, str | None]:
    """(blocks, note). Blocks is None when the model's document cannot be used."""
    if not llm.enabled():
        return None, None
    data, err, _hit = llm.generate_json(SYSTEM, json.dumps(_packet(plan, bank), ensure_ascii=False), client)
    if data is None:
        return None, err
    blocks, _dropped = validate_sections(data, plan, bank)
    if sum(1 for x in blocks if x.kind == "p") < MIN_PARAGRAPHS:
        return None, "o texto da IA não passou nas verificações"
    return blocks, None


def build_document(plan: PlanResponse, full: Store | None, use_llm: bool = False, client=None) -> tuple[Document, ImageBank]:
    bank = ImageBank(plan, full)
    title, sub, meta = _header(plan)
    doc = Document(title, sub, meta)
    blocks, note = llm_body(plan, bank, client) if use_llm else (None, None)
    if blocks:
        doc.blocks, doc.source = blocks, "llm"
    else:
        doc.blocks, doc.note = rules_body(plan, bank), note
    notes = bank.data_notes()  # always written by code, in both modes: a missing image or name must never look like a bug
    if notes:
        doc.meta.append("Itens sem nome ou imagem no catálogo estão explicados em \"Notas sobre os dados\"")
        doc.blocks += [Block("h1", "Notas sobre os dados"), Block("bullets", items=notes)]
    doc.blocks += appendix(plan)
    return doc, bank
