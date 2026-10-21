"""Match rules: MatchReport -> improvement insights for each team, from this match only. Owner: Stream D.

A single map has few events, so every rule counts events (rounds of a kind) and the evidence says so; the amber
`low_sample` badge appears when the count is below `LOW_SAMPLE["events"]`.
"""
from __future__ import annotations

from collections import Counter

from ..schemas.common import Insight
from ..schemas.match import MatchReport, RoundSummary
from . import thresholds as T
from .core import Scored, f_pct, make_insight, select

LOW_BUY = ("eco", "semi_eco")


def _won(r: RoundSummary, team: str) -> bool:
    return r.winner == team


def _side(r: RoundSummary, team: str) -> str:
    return r.team_a_side if team == "a" else ("defense" if r.team_a_side == "attack" else "attack")


def _type(r: RoundSummary, team: str) -> str:
    return r.economy.team_a_type if team == "a" else r.economy.team_b_type


def _enemy_type(r: RoundSummary, team: str) -> str:
    return _type(r, "b" if team == "a" else "a")


def for_match(report: MatchReport) -> tuple[list[Insight], list[Insight]]:
    return _team(report, "a"), _team(report, "b")


def _team(report: MatchReport, team: str) -> list[Insight]:
    rounds = report.rounds
    out: list[Scored] = []

    # pistol rounds (the first round of each half)
    pistols = [r for r in rounds if r.number in (1, 13)]
    if len(pistols) == 2:
        wins = sum(_won(r, team) for r in pistols)
        if wins == 2:
            out.append(Scored(make_insight("match-pistol-strong", "strength", "Venceu os dois pistol rounds da partida.",
                                           "pistols vencidos", 2, 2, None, None, "events"), 0.9))
        elif wins == 0:
            out.append(Scored(make_insight("match-pistol-weak", "weakness", "Perdeu os dois pistol rounds da partida.",
                                           "pistols vencidos", 0, 2, None, None, "events"), 0.9))
            out.append(Scored(make_insight("match-pistol-tip", "tip",
                                           "Revise as jogadas de pistol: perder os dois entrega vantagem de economia ao adversário por vários rounds.",
                                           "pistols vencidos", 0, 2, None, None, "events"), 0.7))

    # eco conversion: low buy against a full buy
    upsets = [r for r in rounds if _type(r, team) in LOW_BUY and _enemy_type(r, team) == "full_buy"]
    if len(upsets) >= 3:
        wins = sum(_won(r, team) for r in upsets)
        rate = wins / len(upsets) * 100
        if wins >= 2 and rate >= 40:
            out.append(Scored(make_insight(
                "match-eco-strong", "strength", f"Converteu {wins} de {len(upsets)} rounds de economia fraca contra full buy.",
                "rounds eco vencidos", rate, len(upsets), None, "%", "events"), rate / 100))
    lost_fulls = [r for r in rounds if _type(r, team) == "full_buy" and _enemy_type(r, team) in LOW_BUY and not _won(r, team)]
    if len(lost_fulls) >= 2:
        out.append(Scored(make_insight(
            "match-fullbuy-weak", "weakness", f"Perdeu {len(lost_fulls)} rounds de full buy contra um adversário com economia fraca.",
            "full buys perdidos para eco", len(lost_fulls), len(lost_fulls), None, None, "events"), 0.5 + 0.1 * len(lost_fulls)))
        out.append(Scored(make_insight(
            "match-fullbuy-tip", "tip", "Contra economia fraca, jogue junto e evite duelos isolados: o adversário só precisa de um abate para recuperar arma.",
            "full buys perdidos para eco", len(lost_fulls), len(lost_fulls), None, None, "events"), 0.4))

    # side gap
    for side, name in (("attack", "ataque"), ("defense", "defesa")):
        rs = [r for r in rounds if _side(r, team) == side]
        other = [r for r in rounds if _side(r, team) != side]
        if len(rs) >= 8 and len(other) >= 8:
            w, o = sum(_won(r, team) for r in rs) / len(rs), sum(_won(r, team) for r in other) / len(other)
            if w - o >= 0.3:
                out.append(Scored(make_insight(
                    f"match-side-{side}-strong", "strength", f"Dominou no {name}: venceu {f_pct(w * 100)} dos rounds nesse lado.",
                    f"vitórias no {name}", w * 100, len(rs), o * 100, "%", "events"), w - o))
            elif o - w >= 0.3:
                out.append(Scored(make_insight(
                    f"match-side-{side}-weak", "weakness", f"Foi mal no {name}: venceu só {f_pct(w * 100)} dos rounds nesse lado.",
                    f"vitórias no {name}", w * 100, len(rs), o * 100, "%", "events"), o - w))

    # opening duels (first kills in the scoreboard)
    mine = sum(row.first_kills for row in report.scoreboard if row.team == team)
    theirs = sum(row.first_kills for row in report.scoreboard if row.team != team)
    if mine + theirs >= 10:
        share = mine / (mine + theirs)
        if share - 0.5 >= T.MATCH_OPENING_SHARE_GAP:
            out.append(Scored(make_insight(
                "match-opening-strong", "strength", f"Ganhou {f_pct(share * 100)} dos duelos de abertura ({mine} de {mine + theirs}).",
                "aberturas vencidas", share * 100, mine + theirs, 50, "%", "events"), share - 0.5))
        elif 0.5 - share >= T.MATCH_OPENING_SHARE_GAP:
            out.append(Scored(make_insight(
                "match-opening-weak", "weakness", f"Perdeu a maior parte das aberturas: só {f_pct(share * 100)} ({mine} de {mine + theirs}).",
                "aberturas vencidas", share * 100, mine + theirs, 50, "%", "events"), 0.5 - share))
            out.append(Scored(make_insight(
                "match-opening-tip", "tip", "Troque a forma de abrir os rounds: use utilitário antes do primeiro duelo e busque trocas rápidas.",
                "aberturas vencidas", share * 100, mine + theirs, 50, "%", "events"), 0.4))

    # longest losing streak
    streak = best = 0
    for r in rounds:
        streak = 0 if _won(r, team) else streak + 1
        best = max(best, streak)
    if best >= T.MATCH_LOSING_STREAK:
        out.append(Scored(make_insight(
            "match-streak-weak", "weakness", f"Sequência de {best} rounds perdidos seguidos.", "maior sequência de derrotas", best,
            len(rounds), None, None, "events"), best / 10))
        out.append(Scored(make_insight(
            "match-streak-tip", "tip", "Em sequências de derrota, peça tempo e simplifique: voltar ao básico ajuda a quebrar a série.",
            "maior sequência de derrotas", best, len(rounds), None, None, "events"), best / 12))

    # predictable plant site while attacking
    plants = Counter(r.plant_site for r in rounds if _side(r, team) == "attack" and r.plant_site)
    total = sum(plants.values())
    if total >= 4:
        site, n = plants.most_common(1)[0]
        if n / total >= 0.75:
            out.append(Scored(make_insight(
                "match-site-predictable", "weakness", f"Previsível no ataque: {n} de {total} plantes foram no site {site}.",
                f"plantes no site {site}", n / total * 100, total, None, "%", "events"), n / total - 0.5))
    return select(out)
