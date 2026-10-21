"""Candidate plays for one round, scored by the facts that support them. Owner: Stream D (Action Plan, layer 1).

A play is a site (or a defensive posture) plus a timing. Each candidate is scored by shrunk empirical rates (never raw
small counts) and carries the sentences, with numbers, that explain it; the best one becomes the round's strategy and
the runner-up is kept as the fallback. No utility, lineup or callout advice: the data has none.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas.common import RoundType, Side
from .baselines import Baselines
from .core import f_pct
from .map_intel import SiteView, shrink
from .scouting import PlayerScout, assign_roles

MIN_SITE_PLANTS = 8  # a site needs this many plants on the map to be a candidate


@dataclass
class Play:
    id: str  # execute_site | rush_site | stack_site | hold_balanced | hold_eco
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


def _defense_candidates(views: dict[str, SiteView], enemy: str, my_retake: tuple[int, int]) -> list[Play]:
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
        why = [who[0].upper() + who[1:] + "."]
        stack = share >= 0.5
        out.append(Play("stack_site" if stack else "hold_balanced", v.site, None, share, "", why, "", total))
    return out


def plan_round(side: Side, round_type: RoundType, views: dict[str, SiteView], me: str, enemy: str, my_players: list[PlayerScout],
               enemy_players: list[PlayerScout], my_plant_ms: float | None, enemy_plant_ms: float | None, base: Baselines) -> RoundPlay | None:
    """Best play (and fallback) for one round, or None when the map has no usable site data."""
    low_buy = round_type in ("eco", "semi_eco")
    roles = assign_roles(my_players, side, base)
    # the cheaper the round, the fewer assignments are worth spelling out
    quote = {"pistol": 2, "eco": 1, "semi_eco": 1, "force": 2, "full_buy": 3}[round_type]
    who = [reason for (_p, role, reason) in roles if role != "flex"][:quote]
    weak = _weak_enemy(enemy_players, base)
    target = None
    if weak is not None and not low_buy:
        p, med = weak
        target = f"{p.name} ({enemy}) morre primeiro em {f_pct(p.first_death_rate)} dos rounds (mediana {f_pct(med)}): foque o primeiro duelo contra ele."

    if side == "attack":
        cands = _attack_candidates(views, enemy)
        if not cands:
            return None
        label, hint = timing_of(my_plant_ms)
        best, second = cands[0], (cands[1] if len(cands) > 1 else None)
        if round_type == "pistol":
            best.headline = f"Pistol: entre junto no site {best.site} e troque o primeiro abate; {hint or 'plante rápido'}."
        elif low_buy:
            best.headline = f"Economia fraca: rush coordenado no site {best.site}, sem entrar sozinho; se perder a abertura, guarde as armas."
        elif round_type == "force":
            best.headline = f"Force buy: execute no site {best.site} cedo, antes que o inimigo complete a compra{'' if not hint else '; ' + hint}."
        else:
            best.headline = f"Execute no site {best.site} com plant padrão{'' if not hint else ': ' + hint}."
        best.timing = label
        if second is not None:
            best.risk = (f"Se a abertura falhar, o plano B é o site {second.site}: no mapa, os atacantes vencem "
                         f"{f_pct((views[second.site].map_win or 0) * 100)} dos rounds com plant ali (n = {views[second.site].map_plants}).")
            second.headline = f"Plano B: execute no site {second.site}."
            second.timing = label
        else:
            best.risk = "Se a abertura falhar, volte ao básico e reorganize o time antes de nova entrada."
        return RoundPlay(best, second, who, target)

    tot_def = sum(v.my_def_plants for v in views.values())
    tot_ret = sum(v.my_def_retakes for v in views.values())
    cands = _defense_candidates(views, enemy, (tot_ret, tot_def))
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
    return RoundPlay(best, second, who, target)


def _weak_enemy(players: list[PlayerScout], base: Baselines) -> tuple[PlayerScout, float] | None:
    dist = base.players.get("first_death_rate")
    if dist is None:
        return None
    cands = [p for p in players if p.flags.get("first_death_rate") == "weak" and p.first_death_rate is not None]
    if not cands:
        return None
    p = max(cands, key=lambda x: x.first_death_rate)
    return p, dist.median
