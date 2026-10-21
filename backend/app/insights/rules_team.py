"""Team rules: TeamProfile + baselines -> strengths, weaknesses, improvement tips and exploitable tendencies. Owner: D."""
from __future__ import annotations

from ..metrics.rounds import ROUND_TYPES
from ..schemas.common import Insight, Stat
from ..schemas.team import TeamProfile
from . import thresholds as T
from .baselines import Baselines, Dist
from .core import Scored, f_num, f_pct, intensity, judge, make_insight, select

TYPE_NAME = {"pistol": "pistol", "eco": "eco", "semi_eco": "semi-eco", "force": "force buy", "full_buy": "full buy"}


def _usable(stat: Stat, minimum: int) -> bool:
    return stat.value is not None and stat.sample_size >= minimum


def for_team(t: TeamProfile, base: Baselines) -> list[Insight]:
    out: list[Scored] = []
    rec, eco = t.record, t.economy

    def tail(id_: str, stat: Stat, dist: Dist | None, metric: str, strong: str, weak: str, minimum: int,
             sample: str = "rounds", tip: str | None = None) -> None:
        if not dist or not _usable(stat, minimum):
            return
        v = stat.value * 100
        j = judge(v, dist)
        if not j:
            return
        text = (strong if j == "strong" else weak).format(v=f_pct(v), m=f_pct(dist.median))
        out.append(Scored(make_insight(f"{id_}-{j}", "strength" if j == "strong" else "weakness", text, metric, v,
                                       stat.sample_size, dist.median, "%", sample), intensity(v, dist)))
        if j == "weak" and tip:
            out.append(Scored(make_insight(f"{id_}-tip", "tip", tip.format(v=f_pct(v), m=f_pct(dist.median)), metric, v,
                                           stat.sample_size, dist.median, "%", sample), intensity(v, dist) * 0.8))

    d = base.teams
    tail("team-attack", rec.attack_win_rate, d.get("attack_win_rate"), "vitórias no ataque",
         "Ataque forte: vence {v} dos rounds como atacante (mediana {m}).",
         "Ataque fraco: vence só {v} dos rounds como atacante (mediana {m}).", T.MIN_TEAM_ROUNDS,
         tip="O ataque vence {v} dos rounds (mediana {m}): trabalhe execuções com utilitários coordenados antes de entrar no site.")
    tail("team-defense", rec.defense_win_rate, d.get("defense_win_rate"), "vitórias na defesa",
         "Defesa sólida: vence {v} dos rounds como defensor (mediana {m}).",
         "Defesa frágil: vence só {v} dos rounds como defensor (mediana {m}).", T.MIN_TEAM_ROUNDS,
         tip="A defesa vence {v} dos rounds (mediana {m}): combine trocas entre os defensores e posições de retake.")
    tail("team-pistol", eco.pistol_win_rate, d.get("pistol_win_rate"), "vitórias nos pistol rounds",
         "Pistols fortes: vence {v} dos pistol rounds (mediana {m}).",
         "Pistols fracos: vence só {v} dos pistol rounds (mediana {m}).", T.MIN_TEAM_EVENTS, "events",
         tip="Só {v} de vitórias nos pistol rounds (mediana {m}): ensaie uma jogada fixa de pistol por lado.")
    for rt in ("eco", "semi_eco", "force", "full_buy"):
        st = eco.win_rate_by_round_type.get(rt)
        if st is None:
            continue
        name = TYPE_NAME[rt]
        tail(f"team-{rt.replace('_', '-')}", st, d.get(f"{rt}_win_rate"), f"vitórias em rounds {name}",
             f"Converte bem os rounds {name}: vence {{v}} deles (mediana {{m}}).",
             f"Rounds {name} são um ponto fraco: vence só {{v}} deles (mediana {{m}}).", T.MIN_TEAM_ROUNDS)
    tail("team-post-plant", eco.post_plant_win_rate, d.get("post_plant_win_rate"), "vitórias pós-plant",
         "Joga bem o pós-plant: vence {v} dos rounds com a spike plantada (mediana {m}).",
         "Pós-plant fraco: vence só {v} dos rounds com a spike plantada (mediana {m}).", T.MIN_TEAM_EVENTS, "events",
         tip="Pós-plant com {v} de vitórias (mediana {m}): defina posições de cobertura do plant e quem ajuda a segurar o retake.")
    tail("team-retake", eco.retake_success_rate, d.get("retake_rate"), "retakes bem-sucedidos",
         "Bom retake: desarma a spike em {v} das plantas sofridas (mediana {m}).",
         "Retake fraco: desarma a spike em só {v} das plantas sofridas (mediana {m}).", T.MIN_TEAM_EVENTS, "events",
         tip="Retake com {v} de sucesso (mediana {m}): evite retakes em fila e entre no site com utilitários juntos.")

    # preferred plant site -> predictable, and an exploitable tendency for the opponent
    plants = eco.avg_time_to_plant_ms.sample_size
    if plants >= T.SITE_CONCEDED_MIN_PLANTS and eco.plant_site_preference:
        site, st = max(eco.plant_site_preference.items(), key=lambda kv: kv[1].value or 0)
        v = (st.value or 0) * 100
        if st.value and st.value >= T.SITE_PREDICTABLE_SHARE:
            out.append(Scored(make_insight(
                "team-site-predictable", "weakness",
                f"Previsível no ataque: {f_pct(v)} dos plantes saem no site {site}.", f"plantes no site {site}", v, plants, None, "%",
                "events"), st.value))
            out.append(Scored(make_insight(
                "team-site-strategy", "strategy",
                f"Contra este time, reforce o site {site}: é onde plantam em {f_pct(v)} das vezes.", f"plantes no site {site}", v,
                plants, None, "%", "events"), st.value))

    out.extend(_map_insights(t))
    out.extend(_trend_and_roles(t))
    return select(out)


def _map_insights(t: TeamProfile) -> list[Scored]:
    rec = t.record
    if not rec.matches:
        return []
    overall = rec.wins / rec.matches
    rows = [m for m in t.by_map if m.matches >= T.MIN_MATCHES_ON_MAP and m.win_rate.value is not None]
    if len(rows) < 2:
        return []
    out: list[Scored] = []
    best, worst = max(rows, key=lambda m: m.win_rate.value), min(rows, key=lambda m: m.win_rate.value)
    if best.win_rate.value - overall >= T.MAP_GAP:
        v = best.win_rate.value * 100
        out.append(Scored(make_insight(
            "team-map-best", "strength",
            f"Mapa forte: {best.map.name}, com {f_pct(v)} de vitórias (geral {f_pct(overall * 100)}).", f"vitórias em {best.map.name}", v,
            best.matches, overall * 100, "%", "matches"), best.win_rate.value - overall))
    if overall - worst.win_rate.value >= T.MAP_GAP and worst.map.name != best.map.name:
        v = worst.win_rate.value * 100
        out.append(Scored(make_insight(
            "team-map-worst", "weakness",
            f"Mapa fraco: {worst.map.name}, com só {f_pct(v)} de vitórias (geral {f_pct(overall * 100)}).", f"vitórias em {worst.map.name}", v,
            worst.matches, overall * 100, "%", "matches"), overall - worst.win_rate.value))
        out.append(Scored(make_insight(
            "team-map-tip", "tip", f"Priorize treinar {worst.map.name}: é o mapa em que o time mais perde ({f_pct(v)} de vitórias).",
            f"vitórias em {worst.map.name}", v, worst.matches, overall * 100, "%", "matches"), (overall - worst.win_rate.value) * 0.8))
    return out


def _trend_and_roles(t: TeamProfile) -> list[Scored]:
    out: list[Scored] = []
    if len(t.trend) >= 3:
        last = t.trend[-3:]
        avg = sum(p.round_diff for p in last) / 3
        if avg >= 4:
            out.append(Scored(make_insight(
                "team-trend-up", "strength", f"Em alta: nas últimas 3 partidas venceu por {f_num(avg, 1)} rounds de diferença em média.",
                "saldo de rounds (últimas 3)", avg, 3, 0, None, "matches"), avg / 13))
        elif avg <= -4:
            out.append(Scored(make_insight(
                "team-trend-down", "weakness", f"Em queda: nas últimas 3 partidas perdeu por {f_num(-avg, 1)} rounds de diferença em média.",
                "saldo de rounds (últimas 3)", avg, 3, 0, None, "matches"), -avg / 13))
    counts = {c.role: c.count for c in t.role_composition}
    if counts and not counts.get("entry"):
        out.append(Scored(make_insight(
            "team-role-entry-tip", "tip",
            "A última escalação não tem um entry fragger claro: defina quem abre os rounds de ataque.",
            "jogadores com perfil de entry", 0, sum(counts.values()), None, None, "matches"), 0.3))
    return out
