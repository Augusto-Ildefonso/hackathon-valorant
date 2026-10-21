"""Player rules: PlayerProfile + baselines -> strengths, weaknesses and training tips. Owner: Stream D.

Each rule compares one metric with the qualified-population distribution (`baselines.players`); a value in the top
or bottom tail fires the rule. Texts are pt-BR templates; every figure in a text also appears in the evidence.
"""
from __future__ import annotations

from ..schemas.common import Insight
from ..schemas.player import PlayerProfile
from . import thresholds as T
from .baselines import Baselines
from .core import Scored, f_num, f_pct, intensity, judge, make_insight, select


def for_player(p: PlayerProfile, base: Baselines) -> list[Insight]:
    s = p.stats
    out: list[Scored] = []
    dists = base.players
    rounds = s.rounds

    def add(ins: Insight, value: float, dist) -> None:
        out.append(Scored(ins, intensity(value, dist) if dist else 1.0))

    if rounds >= T.MIN_PLAYER_ROUNDS:
        # K/D
        v = s.kd.value
        j = judge(v, dists.get("kd"))
        if j:
            d = dists["kd"]
            text = (f"K/D de {f_num(v)}, entre os melhores do campeonato (mediana {f_num(d.median)})." if j == "strong"
                    else f"K/D de {f_num(v)}, entre os mais baixos do campeonato (mediana {f_num(d.median)}).")
            add(make_insight(f"player-kd-{j}", "strength" if j == "strong" else "weakness", text, "K/D", v, rounds, d.median), v, d)
        # ADR
        v = s.adr.value
        j = judge(v, dists.get("adr"))
        if j:
            d = dists["adr"]
            text = (f"Causa {f_num(v, 0)} de dano por round (mediana {f_num(d.median, 0)}): pressão constante sobre o inimigo." if j == "strong"
                    else f"Causa só {f_num(v, 0)} de dano por round (mediana {f_num(d.median, 0)}): pouco impacto fora dos abates.")
            add(make_insight(f"player-adr-{j}", "strength" if j == "strong" else "weakness", text, "ADR", v, rounds, d.median), v, d)
        # first deaths
        fd = s.first_death_rate.value
        if fd is not None:
            v = fd * 100
            d = dists.get("first_death_rate")
            j = judge(v, d, higher_is_better=False)
            if j == "weak":
                add(make_insight("player-first-death-weak", "weakness",
                                 f"Morre primeiro em {f_pct(v)} dos rounds (mediana {f_pct(d.median)}): entrega vantagem numérica cedo.",
                                 "mortes de abertura por round", v, rounds, d.median, "%"), v, d)
                out.append(Scored(make_insight(
                    "player-first-death-tip", "tip",
                    "Evite o primeiro contato sem apoio: segure o ângulo junto de um colega que possa trocar o abate.",
                    "mortes de abertura por round", v, rounds, d.median, "%"), intensity(v, d) * 0.8))
        # traded deaths
        if s.deaths >= 20:
            v = s.traded_deaths / s.deaths * 100
            d = dists.get("trade_share")
            if judge(v, d) == "weak":
                add(make_insight("player-trade-tip", "tip",
                                 f"Só {f_pct(v)} das mortes foram trocadas por um colega (mediana {f_pct(d.median)}): jogue mais perto do time.",
                                 "mortes trocadas", v, s.deaths, d.median, "%", "events"), v, d)

    # opening duels
    duels = s.first_kills + s.first_deaths
    if duels >= T.MIN_OPENING_DUELS and s.opening_duel_win_pct.value is not None:
        v = s.opening_duel_win_pct.value * 100
        d = dists.get("opening_win_pct")
        j = judge(v, d)
        if j:
            text = (f"Vence {f_pct(v)} dos duelos de abertura (mediana {f_pct(d.median)}): boa opção para abrir o round."
                    if j == "strong" else
                    f"Vence só {f_pct(v)} dos duelos de abertura (mediana {f_pct(d.median)}): evite deixá-lo abrir o round sozinho.")
            add(make_insight(f"player-opening-{j}", "strength" if j == "strong" else "weakness", text,
                             "duelos de abertura vencidos", v, duels, d.median, "%", "events"), v, d)

    # headshot percentage
    if s.shots >= T.MIN_SHOTS and s.hs_pct.value is not None:
        v = s.hs_pct.value * 100
        d = dists.get("hs_pct")
        j = judge(v, d)
        if j:
            text = (f"Acerta a cabeça em {f_pct(v)} dos tiros (mediana {f_pct(d.median)}): mira precisa."
                    if j == "strong" else
                    f"Acerta a cabeça em só {f_pct(v)} dos tiros (mediana {f_pct(d.median)}).")
            add(make_insight(f"player-hs-{j}", "strength" if j == "strong" else "weakness", text, "HS%", v, s.shots, d.median, "%"), v, d)
            if j == "weak":
                out.append(Scored(make_insight(
                    "player-hs-tip", "tip", "Treino de mira: mantenha a mira na altura da cabeça antes de abrir cada ângulo.",
                    "HS%", v, s.shots, d.median, "%"), intensity(v, d) * 0.8))

    out.extend(_weapon_tips(p))
    out.extend(_map_insights(p))
    return select(out)


def _weapon_tips(p: PlayerProfile) -> list[Scored]:
    rows = [w for w in p.weapons if w.buy_type is None and w.weapon.name and w.rounds >= T.MIN_WEAPON_ROUNDS
            and w.round_win_rate.value is not None]
    if len(rows) < 2:
        return []
    total = sum(w.rounds for w in rows)
    avg = sum(w.round_win_rate.value * w.rounds for w in rows) / total
    best = max(rows, key=lambda w: w.round_win_rate.value)
    worst = min(rows, key=lambda w: w.round_win_rate.value)
    out: list[Scored] = []
    if best.round_win_rate.value - avg >= T.WEAPON_GAP:
        v = best.round_win_rate.value * 100
        out.append(Scored(make_insight(
            "player-weapon-best", "tip",
            f"Rende mais com a {best.weapon.name}: o time venceu {f_pct(v)} dos rounds em que comprou (média do jogador {f_pct(avg * 100)}).",
            f"vitórias com {best.weapon.name}", v, best.rounds, avg * 100, "%"), (best.round_win_rate.value - avg) * 5))
    if avg - worst.round_win_rate.value >= T.WEAPON_GAP and worst.weapon.id != best.weapon.id:
        v = worst.round_win_rate.value * 100
        out.append(Scored(make_insight(
            "player-weapon-worst", "tip",
            f"Com a {worst.weapon.name} o time venceu só {f_pct(v)} dos rounds (média do jogador {f_pct(avg * 100)}): reveja quando comprá-la.",
            f"vitórias com {worst.weapon.name}", v, worst.rounds, avg * 100, "%"), (avg - worst.round_win_rate.value) * 5))
    return out


def _map_insights(p: PlayerProfile) -> list[Scored]:
    kd = p.stats.kd.value
    rows = [m for m in p.by_map if m.matches >= T.MIN_MATCHES_ON_MAP and m.kd.value is not None]
    if not kd or len(rows) < 2:
        return []
    out: list[Scored] = []
    best = max(rows, key=lambda m: m.kd.value)
    worst = min(rows, key=lambda m: m.kd.value)
    if best.kd.value / kd >= 1.25:
        out.append(Scored(make_insight(
            "player-map-best", "strength", f"Rende muito mais em {best.map.name}: K/D de {f_num(best.kd.value)} contra {f_num(kd)} no geral.",
            f"K/D em {best.map.name}", best.kd.value, best.matches, kd, None, "matches"), best.kd.value / kd - 1))
    if worst.kd.value / kd <= 0.75 and worst.map.name != best.map.name:
        out.append(Scored(make_insight(
            "player-map-worst", "tip",
            f"Em {worst.map.name} o K/D cai para {f_num(worst.kd.value)} (geral {f_num(kd)}): revise as posições e os ângulos desse mapa.",
            f"K/D em {worst.map.name}", worst.kd.value, worst.matches, kd, None, "matches"), 1 - worst.kd.value / kd))
    return out
