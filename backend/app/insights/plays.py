"""Candidate plays for one round, scored by the facts that support them. Owner: Stream D (Action Plan, layer 1).

A play is a site (or a defensive posture) plus a timing. Each candidate is scored by shrunk empirical rates (never raw
small counts) and carries the sentences, with numbers, that explain it; the best one becomes the round's strategy and
the runner-up is kept as the fallback. The base scenario's history varies the plan from round to round: the site rotates
after a loss or after repeating the same site, the tempo follows the round type, the focus on the enemy's weak players
rotates. No utility, lineup or callout advice: the data has none.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas.common import RoundType, Side
from .baselines import Baselines
from .core import f_pct
from .map_intel import SiteView, shrink
from .scouting import PlayerScout, assign_roles

MIN_SITE_PLANTS = 8  # a site needs this many plants on the map to be a candidate
SWITCH_GAP_AFTER_LOSS = 0.10  # score gap under which a lost site is swapped for the runner-up
SWITCH_GAP_REPEAT = 0.06  # score gap under which a site used REPEAT_LIMIT times in a row is swapped
REPEAT_LIMIT = 2


@dataclass
class Play:
    id: str  # execute_site | stack_site | hold_balanced
    site: str | None
    timing: str | None  # early | default | late
    score: float
    headline: str
    why: list[str]
    risk: str
    sample: int  # smallest sample behind the decision (drives low_sample)


@dataclass
class RoundPlay:
    best: Play
    fallback: Play | None
    who: list[str] = field(default_factory=list)
    target: str | None = None
    read: str | None = None  # why this round differs from the previous one (momentum, rotation)


@dataclass
class History:
    """What the base scenario did before this round (for the planned team)."""

    n: int = 1
    prev_side: str | None = None
    prev_site: str | None = None
    prev_won: bool | None = None
    repeat: int = 0  # consecutive rounds on the same side with the same site
    wins: int = 0  # consecutive base-scenario wins before this round
    losses: int = 0


def timing_of(ms: float | None) -> tuple[str | None, str]:
    """('early'|'default'|'late', pt-BR hint) from the average plant time."""
    if ms is None:
        return None, ""
    s = ms / 1000
    label = "early" if s < 35 else "late" if s > 60 else "default"
    return label, f"o plant sai por volta de {s:.0f} s".replace(".", ",")


def _attack_candidates(views: dict[str, SiteView], enemy: str) -> list[Play]:
    out: list[Play] = []
    for s, v in views.items():
        if v.map_plants < MIN_SITE_PLANTS or v.map_win is None:
            continue
        vs_w = (v.vs_win or 0) * v.vs_plants
        conceded = shrink(vs_w, v.vs_plants, v.map_win)
        comfort = shrink((v.my_win or 0) * v.my_plants, v.my_plants, v.map_win)
        score = 0.4 * conceded + 0.35 * comfort + 0.25 * v.map_win
        why = []
        if v.vs_plants:
            why.append(f"Contra a defesa do {enemy}, os atacantes venceram {f_pct((v.vs_win or 0) * 100)} dos rounds com plant no site {s} (n = {v.vs_plants}).")
        else:
            why.append(f"Sem histórico contra o {enemy} no site {s}; no mapa os atacantes vencem {f_pct(v.map_win * 100)} dos rounds com plant ali (n = {v.map_plants}).")
        if v.my_plants and v.my_share is not None:
            why.append(f"O time planta no site {s} em {f_pct(v.my_share * 100)} dos rounds de ataque (n = {v.my_plants}) e vence {f_pct((v.my_win or 0) * 100)} deles.")
        out.append(Play("execute_site", s, None, score, "", why, "", min(v.vs_plants or v.map_plants, v.my_plants or v.map_plants)))
    return sorted(out, key=lambda p: -p.score)


def _defense_candidates(views: dict[str, SiteView], enemy: str) -> list[Play]:
    sites = [v for v in views.values() if v.map_plants >= MIN_SITE_PLANTS]
    if not sites:
        return []
    use_enemy = sum(v.enemy_plants for v in sites) >= MIN_SITE_PLANTS
    total = sum((v.enemy_plants if use_enemy else v.map_plants) for v in sites)
    out: list[Play] = []
    for v in sorted(sites, key=lambda v: -(v.enemy_plants if use_enemy else v.map_plants)):
        n = v.enemy_plants if use_enemy else v.map_plants
        share = n / total if total else 0
        who = f"o {enemy} planta no site {v.site} em {f_pct(share * 100)} dos plantes (n = {total})" if use_enemy else \
            f"no mapa {f_pct(share * 100)} dos plantes saem no site {v.site} (n = {total})"
        out.append(Play("stack_site" if share >= 0.5 else "hold_balanced", v.site, None, share, "",
                        [who[0].upper() + who[1:] + "."], "", total))
    return out


def _weak_enemies(players: list[PlayerScout]) -> list[PlayerScout]:
    cands = [p for p in players if p.flags.get("first_death_rate") == "weak" and p.first_death_rate is not None]
    return sorted(cands, key=lambda p: -p.first_death_rate)


def _read(h: History, side: str) -> str | None:
    """One sentence on the momentum of the base scenario (numbers are the scenario's own counts)."""
    if h.n <= 1 or h.prev_won is None:
        return None
    if h.wins >= 2:
        return f"Sequência de {h.wins} vitórias no cenário base: mantenha o ritmo e não mude o que está funcionando."
    if h.losses >= 2:
        return f"Sequência de {h.losses} derrotas no cenário base: simplifique, jogue junto e evite riscos desnecessários."
    return None


def plan_round(side: Side, round_type: RoundType, views: dict[str, SiteView], me: str, enemy: str, my_players: list[PlayerScout],
               enemy_players: list[PlayerScout], my_plant_ms: float | None, enemy_plant_ms: float | None, base: Baselines,
               history: History | None = None) -> RoundPlay | None:
    """Best play (and fallback) for one round, or None when the map has no usable site data."""
    h = history or History()
    low_buy = round_type in ("eco", "semi_eco")
    roles = assign_roles(my_players, side, base)
    # the cheaper the round, the fewer assignments are worth spelling out
    quote = {"pistol": 2, "eco": 1, "semi_eco": 1, "force": 2, "full_buy": 3}[round_type]
    who = [reason for (_p, role, reason) in roles if role != "flex"][:quote]
    weak = _weak_enemies(enemy_players)
    target = None
    dist = base.players.get("first_death_rate")
    if weak and not low_buy and dist is not None:
        p = weak[(h.n // 2) % len(weak)]  # rotate the focus when several enemy players are weak
        target = f"{p.name} ({enemy}) morre primeiro em {f_pct(p.first_death_rate)} dos rounds (mediana {f_pct(dist.median)}): foque o primeiro duelo contra ele."
    read = _read(h, side)

    if side == "attack":
        cands = _attack_candidates(views, enemy)
        if not cands:
            return None
        best, second = cands[0], (cands[1] if len(cands) > 1 else None)
        # rotate the site: after a loss on the same site, or after using it too many times in a row
        if second is not None and h.prev_side == "attack" and h.prev_site == best.site:
            gap = best.score - second.score
            if h.prev_won is False and gap < SWITCH_GAP_AFTER_LOSS:
                best, second = second, best
                read = f"Trocar de site depois da derrota no R{h.n - 1}: o site {best.site} é quase tão bom quanto o {second.site} nos dados e tira a previsibilidade."
            elif h.repeat >= REPEAT_LIMIT and gap < SWITCH_GAP_REPEAT:
                best, second = second, best
                read = f"O site {second.site} foi o alvo nos últimos {h.repeat} rounds de ataque: alterne para o {best.site} para não ficar previsível."
        label, hint = timing_of(my_plant_ms)
        early = low_buy or round_type in ("force", "pistol")
        if early:
            label = "early"
        if round_type == "pistol":
            best.headline = f"Pistol: entre junto no site {best.site} e troque o primeiro abate; {hint or 'plante rápido'}."
        elif low_buy:
            best.headline = f"Economia fraca: rush coordenado no site {best.site}, sem entrar sozinho; se perder a abertura, guarde as armas."
        elif round_type == "force":
            best.headline = f"Force buy: execute no site {best.site} cedo, antes que o inimigo complete a compra{'' if not hint else '; ' + hint}."
        elif h.losses >= 2:
            best.headline = f"Depois de {h.losses} derrotas, jogue o básico no site {best.site}: entrada em grupo, plant padrão{'' if not hint else ' (' + hint + ')'}."
        else:
            best.headline = f"Execute no site {best.site} com plant padrão{'' if not hint else ': ' + hint}."
        best.timing = label
        if second is not None:
            sv = views[second.site]
            best.risk = (f"Se a abertura falhar, o plano B é o site {second.site}: no mapa, os atacantes vencem "
                         f"{f_pct((sv.map_win or 0) * 100)} dos rounds com plant ali (n = {sv.map_plants}).")
            second.headline = f"Plano B: execute no site {second.site}."
            second.timing = label
        else:
            best.risk = "Se a abertura falhar, volte ao básico e reorganize o time antes de nova entrada."
        return RoundPlay(best, second, who, target, read)

    tot_def = sum(v.my_def_plants for v in views.values())
    tot_ret = sum(v.my_def_retakes for v in views.values())
    cands = _defense_candidates(views, enemy)
    if not cands:
        return None
    best, second = cands[0], (cands[1] if len(cands) > 1 else None)
    elabel, ehint = timing_of(enemy_plant_ms)
    anchors = [p.name for p, r, _ in roles if r == "anchor"]
    anchor_txt = " e ".join(anchors) if anchors else "os defensores"
    if best.id == "stack_site":
        best.headline = f"Reforce o site {best.site} com {anchor_txt}."
    else:
        best.headline = f"Distribua a defesa entre os sites; o mais provável é o {best.site}."
    if h.prev_side == "defense" and h.prev_won is False:
        best.headline += f" Depois da derrota no R{h.n - 1}, deixe um jogador de rotação para o site {second.site if second else best.site}."
        read = read or f"Derrota na defesa no R{h.n - 1}: o inimigo pode ter lido a defesa; varie a posição do anchor."
    if low_buy:
        best.headline = f"Economia fraca: segure junto no site {best.site} e jogue por trocas; salve as armas se perder o primeiro duelo."
    if round_type == "pistol":
        best.headline = f"Pistol: segure o site {best.site} em dupla e jogue pela troca do primeiro abate."
    best.timing = elabel
    parts = []
    if ehint:
        parts.append(f"Espere o plant ({ehint.replace('o plant sai', 'o inimigo planta')}) e retome em grupo.")
    if tot_def >= MIN_SITE_PLANTS:
        parts.append(f"O time desarma {f_pct(tot_ret / tot_def * 100)} das plantas sofridas (n = {tot_def}).")
    if second is not None:
        parts.append(f"Se plantarem no site {second.site}, rotacione sem deixar o {best.site} vazio.")
    best.risk = " ".join(parts) or "Se perder o primeiro duelo, não corra atrás do abate: reagrupe para o retake."
    return RoundPlay(best, second, who, target, read)
