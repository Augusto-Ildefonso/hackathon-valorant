"""Fact packets for the LLM insight mode (Stream D). Owner: D.

The code computes every number (same stats and baselines the rules use); the LLM only chooses which facts matter and
words them. Each fact has a stable id the model must cite, so the evidence of an insight is filled from the fact, never
from the model's text. Values are in display units (percentages 0-100, K/D plain, times in seconds).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..metrics.config import LOW_SAMPLE
from ..schemas.map import MapProfile
from ..schemas.match import MatchReport, RoundSummary
from ..schemas.player import PlayerProfile
from ..schemas.team import TeamProfile
from .baselines import Baselines, Dist


@dataclass
class Fact:
    id: str
    label: str
    value: float
    n: int
    baseline: float | None = None
    unit: str | None = None  # "%", "s" or None
    band: str | None = None  # where the value sits in the qualified population
    sample: str = "rounds"  # LOW_SAMPLE key
    note: str | None = None  # words only, never numbers (numbers the model may quote are value / baseline / n)
    better: bool = True  # False when a LOWER value is the good direction (e.g. first-death rate)

    @property
    def low_sample(self) -> bool:
        return self.n < LOW_SAMPLE[self.sample]

    @staticmethod
    def _num(x: float) -> float | int:
        """Whole numbers travel as ints (a count of 13 must not be read as '13.0')."""
        return int(x) if float(x).is_integer() else round(x, 2)

    def as_dict(self) -> dict:
        d = {"id": self.id, "rotulo": self.label, "valor": self._num(self.value), "n": self.n}
        if self.baseline is not None:
            d["referencia"] = self._num(self.baseline)
        if self.unit:
            d["unidade"] = self.unit
        if self.band:
            d["faixa"] = self.band
        if self.low_sample:
            d["amostra_baixa"] = True
        if self.note:
            d["nota"] = self.note
        return d


def band_of(value: float, dist: Dist | None, higher_better: bool = True) -> str | None:
    if dist is None:
        return None
    if value >= dist.p_strong:
        return "entre os 20% melhores" if higher_better else "entre os 20% piores"
    if value <= dist.p_weak:
        return "entre os 20% piores" if higher_better else "entre os 20% melhores"
    return "faixa intermediária"


class _Facts(list):
    def add(self, id_: str, label: str, value: float | None, n: int, *, dist: Dist | None = None, better: bool = True,
            baseline: float | None = None, unit: str | None = None, sample: str = "rounds", note: str | None = None) -> None:
        if value is None or value != value:
            return
        ref = baseline if baseline is not None else (dist.median if dist else None)
        self.append(Fact(id_, label, float(value), int(n), ref, unit, band_of(value, dist, better), sample, note, better))


def player_facts(p: PlayerProfile, base: Baselines) -> list[Fact]:
    s, pl, F = p.stats, base.players, _Facts()
    r = s.rounds
    F.add("rounds", "Rounds jogados", r, r)
    F.add("kd", "K/D", s.kd.value, r, dist=pl.get("kd"))
    F.add("adr", "Dano por round (ADR)", s.adr.value, r, dist=pl.get("adr"))
    if s.hs_pct.value is not None:
        F.add("hs", "Acerto de cabeça (HS%)", s.hs_pct.value * 100, s.shots, dist=pl.get("hs_pct"), unit="%")
    if s.opening_duel_win_pct.value is not None:
        F.add("opening", "Duelos de abertura vencidos", s.opening_duel_win_pct.value * 100, s.first_kills + s.first_deaths,
              dist=pl.get("opening_win_pct"), unit="%", sample="events")
    F.add("first_death", "Rounds em que morre primeiro (menor é melhor)", s.first_deaths / max(r, 1) * 100, r,
          dist=pl.get("first_death_rate"), better=False, unit="%")
    F.add("first_kill", "Rounds em que abre com um abate", s.first_kills / max(r, 1) * 100, r, dist=pl.get("first_kill_rate"), unit="%")
    if s.deaths:
        F.add("trade", "Mortes trocadas por um colega", s.traded_deaths / s.deaths * 100, s.deaths, dist=pl.get("trade_share"), unit="%", sample="events")
    F.add("clutches", "Clutches (1vX) vencidos", s.clutches, r, sample="events")
    F.add("multikills", "Rounds com 3 abates ou mais", s.multikills.k3 + s.multikills.k4 + s.multikills.k5, r, sample="events")
    for role in p.roles[:2]:
        F.add(f"role:{role.role}", f"Pontuação do perfil de {role.role} (0 a 1)", role.score, r, note="função inferida do estilo de jogo")
    for a in p.agents[:3]:
        if a.agent.name:
            F.add(f"agent:{a.agent.name}", f"K/D com {a.agent.name}", a.kd.value, a.matches, baseline=s.kd.value, sample="matches")
    rows = [w for w in p.weapons if w.buy_type is None and w.weapon.name and w.rounds >= 10 and w.round_win_rate.value is not None]
    if rows:
        avg = sum(w.round_win_rate.value * w.rounds for w in rows) / sum(w.rounds for w in rows) * 100
        for w in sorted(rows, key=lambda w: -w.rounds)[:5]:
            F.add(f"weapon:{w.weapon.name}", f"Vitórias do time em rounds com {w.weapon.name}", w.round_win_rate.value * 100, w.rounds,
                  baseline=avg, unit="%")
    for m in p.by_map:
        F.add(f"map:{m.map.name}", f"K/D em {m.map.name}", m.kd.value, m.matches, baseline=s.kd.value, sample="matches")
    return F


def team_facts(t: TeamProfile, base: Baselines) -> list[Fact]:
    tm, F = base.teams, _Facts()
    rec, eco = t.record, t.economy
    F.add("win_rate", "Partidas vencidas", rec.wins / rec.matches * 100 if rec.matches else None, rec.matches, dist=tm.get("win_rate"), unit="%", sample="matches")
    for key, stat, dist_key, label in (("round_wr", rec.round_win_rate, "round_win_rate", "Rounds vencidos"),
                                      ("attack_wr", rec.attack_win_rate, "attack_win_rate", "Rounds vencidos no ataque"),
                                      ("defense_wr", rec.defense_win_rate, "defense_win_rate", "Rounds vencidos na defesa")):
        if stat.value is not None:
            F.add(key, label, stat.value * 100, stat.sample_size, dist=tm.get(dist_key), unit="%")
    names = {"pistol": "pistol", "eco": "eco", "semi_eco": "semi-eco", "force": "force buy", "full_buy": "full buy"}
    for rt, stat in eco.win_rate_by_round_type.items():
        if stat.value is not None:
            F.add(f"type:{rt}", f"Rounds {names[rt]} vencidos", stat.value * 100, stat.sample_size, dist=tm.get(f"{rt}_win_rate"), unit="%",
                  sample="events" if rt == "pistol" else "rounds")
    if eco.post_plant_win_rate.value is not None:
        F.add("post_plant", "Rounds vencidos com a spike plantada", eco.post_plant_win_rate.value * 100, eco.post_plant_win_rate.sample_size,
              dist=tm.get("post_plant_win_rate"), unit="%", sample="events")
    if eco.retake_success_rate.value is not None:
        F.add("retake", "Plantas sofridas desarmadas (retake)", eco.retake_success_rate.value * 100, eco.retake_success_rate.sample_size,
              dist=tm.get("retake_rate"), unit="%", sample="events")
    if eco.avg_time_to_plant_ms.value is not None:
        F.add("plant_time", "Tempo médio até o plante", eco.avg_time_to_plant_ms.value / 1000, eco.avg_time_to_plant_ms.sample_size, unit="s", sample="events")
    for site, st in eco.plant_site_preference.items():
        F.add(f"site:{site}", f"Plantes no site {site}", (st.value or 0) * 100, eco.avg_time_to_plant_ms.sample_size, unit="%", sample="events")
    overall = rec.wins / rec.matches * 100 if rec.matches else None
    for m in t.by_map:
        F.add(f"map:{m.map.name}", f"Vitórias em {m.map.name}", (m.win_rate.value or 0) * 100, m.matches, baseline=overall, unit="%", sample="matches")
        if m.attack_win_rate.value is not None and m.attack_win_rate.sample_size >= 12:
            F.add(f"map:{m.map.name}:attack", f"Ataque vencido em {m.map.name}", m.attack_win_rate.value * 100, m.attack_win_rate.sample_size, unit="%")
        if m.defense_win_rate.value is not None and m.defense_win_rate.sample_size >= 12:
            F.add(f"map:{m.map.name}:defense", f"Defesa vencida em {m.map.name}", m.defense_win_rate.value * 100, m.defense_win_rate.sample_size, unit="%")
    if len(t.trend) >= 3:
        F.add("trend_last3", "Saldo médio de rounds nas últimas 3 partidas", sum(p.round_diff for p in t.trend[-3:]) / 3, 3, sample="matches")
    for m in t.roster[:6]:
        F.add(f"player:{m.player.riot_id.split('#')[0]}", f"K/D de {m.player.riot_id.split('#')[0]} no time", m.kd, m.matches, sample="matches",
              note=f"função mais provável: {m.top_role.role}" if m.top_role else None)
    for rc in t.role_composition:
        F.add(f"roles:{rc.role}", f"Jogadores com perfil de {rc.role} na última escalação", rc.count, sum(c.count for c in t.role_composition), sample="matches")
    return F


def map_facts(m: MapProfile, store=None) -> list[Fact]:
    F = _Facts()
    n = m.rounds
    F.add("matches", "Partidas analisadas", m.matches, m.matches, sample="matches")
    F.add("attack_wr", "Rounds vencidos pelo ataque", m.attack_win_rate.value and m.attack_win_rate.value * 100, n, unit="%", note=f"classificação: {m.classification}")
    F.add("defense_wr", "Rounds vencidos pela defesa", m.defense_win_rate.value and m.defense_win_rate.value * 100, n, unit="%")
    total = sum(s.plants for s in m.sites)
    for s in m.sites:
        F.add(f"site:{s.site}:plants", f"Plantes no site {s.site} (parcela dos plantes)", s.plants / total * 100 if total else 0, total, unit="%", sample="events")
        if s.defuse_rate.value is not None:
            F.add(f"site:{s.site}:defuse", f"Plantas desarmadas no site {s.site}", s.defuse_rate.value * 100, s.defuse_rate.sample_size, unit="%", sample="events")
    for u in m.top_agents[:5]:
        if u.name:
            F.add(f"agent:{u.name}", f"Jogadores que escolhem {u.name}", u.share * 100, u.picks, unit="%", sample="matches")
    for u in m.top_weapons[:5]:
        if u.name:
            F.add(f"weapon:{u.name}", f"Rounds com {u.name} comprada", u.share * 100, u.picks, unit="%")
    if store is not None and m.map.has_minimap:
        from . import rules_map

        for i in rules_map._blind_spots(m, store):
            ev = i.insight.evidence
            if "tip" in i.insight.id.split("danger")[-1] or ev.sample_size <= 0:
                continue  # the rule's own tip duplicates the danger-zone insight
            where = i.insight.text_pt.split(":")[0].replace("Zona perigosa ", "").replace("Zona descoberta ", "")
            if "danger" in i.insight.id:
                # evidence = deaths, baseline = kills, n = deaths + kills inside the box: express it as the deaths' share of the events
                F.add("zone:danger", "Zona perigosa: parcela de mortes entre mortes e abates ocorridos na área (50% seria equilíbrio)",
                      ev.value / ev.sample_size * 100, ev.sample_size, baseline=50, unit="%", sample="events", note=where, better=False)
            else:
                # evidence = kills scored from unwatched positions, n = kills scored from the area
                F.add("zone:uncovered", "Zona descoberta: parcela dos abates inimigos na área que saíram sem nenhum adversário cobrindo (a referência é a média do dataset)",
                      ev.value / ev.sample_size * 100, ev.sample_size, baseline=24, sample="events", unit="%", note=where, better=False)
    return F


# ---- match -------------------------------------------------------------------------------------------------------------
def _side(r: RoundSummary, team: str) -> str:
    return r.team_a_side if team == "a" else ("defense" if r.team_a_side == "attack" else "attack")


def _type(r: RoundSummary, team: str) -> str:
    return r.economy.team_a_type if team == "a" else r.economy.team_b_type


def match_facts(rep: MatchReport) -> list[Fact]:
    F = _Facts()
    rounds = rep.rounds
    total = len(rounds)
    for team in ("a", "b"):
        other = "b" if team == "a" else "a"
        name = (rep.team_a if team == "a" else rep.team_b).team.name
        pre = f"{team}:"
        F.add(pre + "rounds_won", f"Rounds vencidos por {name}", (rep.team_a if team == "a" else rep.team_b).score, total, sample="events")
        pistols = [r for r in rounds if r.number in (1, 13)]
        F.add(pre + "pistols", f"Pistol rounds vencidos por {name}", sum(r.winner == team for r in pistols), len(pistols), sample="events")
        low = [r for r in rounds if _type(r, team) in ("eco", "semi_eco") and _type(r, other) == "full_buy"]
        if low:
            F.add(pre + "eco_vs_full", f"Rounds de economia fraca contra full buy vencidos por {name}", sum(r.winner == team for r in low), len(low), sample="events")
        lost_full = [r for r in rounds if _type(r, team) == "full_buy" and _type(r, other) in ("eco", "semi_eco")]
        if lost_full:
            F.add(pre + "full_vs_eco_lost", f"Full buys de {name} perdidos para economia fraca", sum(r.winner != team for r in lost_full), len(lost_full), sample="events", better=False)
        for side, pt in (("attack", "no ataque"), ("defense", "na defesa")):
            rs = [r for r in rounds if _side(r, team) == side]
            if rs:
                F.add(pre + f"{side}_wr", f"Rounds vencidos por {name} {pt}", sum(r.winner == team for r in rs) / len(rs) * 100, len(rs), unit="%", sample="events")
        mine = sum(x.first_kills for x in rep.scoreboard if x.team == team)
        theirs = sum(x.first_kills for x in rep.scoreboard if x.team != team)
        if mine + theirs:
            F.add(pre + "openings", f"Duelos de abertura vencidos por {name}", mine / (mine + theirs) * 100, mine + theirs, baseline=50, unit="%", sample="events")
        streak = best = 0
        for r in rounds:
            streak = 0 if r.winner == team else streak + 1
            best = max(best, streak)
        F.add(pre + "losing_streak", f"Maior sequência de rounds perdidos por {name}", best, total, sample="events", better=False)
        plants: dict[str, int] = {}
        for r in rounds:
            if _side(r, team) == "attack" and r.plant_site:
                plants[r.plant_site] = plants.get(r.plant_site, 0) + 1
        tp = sum(plants.values())
        for site, k in plants.items():
            F.add(pre + f"site:{site}", f"Plantes de {name} no site {site}", k / tp * 100, tp, unit="%", sample="events")
        top = sorted((x for x in rep.scoreboard if x.team == team), key=lambda x: -x.score)[:3]
        for x in top:
            F.add(pre + f"player:{x.player.riot_id.split('#')[0]}", f"K/D de {x.player.riot_id.split('#')[0]} ({name})", x.kills / max(x.deaths, 1), total,
                  note=f"agente {x.agent.name}" if x.agent.name else None)
    return F
