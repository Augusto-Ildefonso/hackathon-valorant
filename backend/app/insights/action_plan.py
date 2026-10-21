"""Action Plan builder: a round-by-round plan for a whole match (layer 1: deterministic, always available). Owner: D.

For every round the base scenario fixes the side, the predicted round type and the projected economy; the scouting
report (rosters, sites, tendencies) picks the play and assigns roles to named players; the text is a pt-BR coach
template whose every number comes from the data. The optional win model (`play_model`) and the LLM narrator (`llm`)
sit on top of this and never replace it.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..analytics.players import player_profile
from ..analytics.teams import team_profile
from ..data.catalog import get_catalog
from ..data.store import Store
from ..metrics import make_stat, next_type_distribution, project_next_credits, round_win_probability, team_rounds
from ..metrics.config import ECONOMY
from ..metrics.rounds import ROUND_TYPES, income_per_player
from ..schemas.common import Insight, Stat, TeamRef
from ..schemas.plan import (AgentRecommendation, BuyItem, Contingency, ContingencyOutcome, EnemyMove, OpponentSummary,
                            PlanRequest, PlanResponse, ProjectedEconomy, RoundPlan, RoundStrategy)
from . import engine
from . import thresholds as T
from .agents_meta import agent_class, armor_level
from .baselines import Baselines, get_baselines
from .core import f_num, f_pct, make_insight
from .map_intel import SiteView, avg_plant_ms, enemy_route, shrink, site_views
from .play_model import get_win_model
from .map_plan import build_map_plan
from .plays import History, plan_round, timing_of
from .scouting import PlayerScout, assign_roles, scout_team

TYPE_PT = {"pistol": "pistol", "eco": "eco", "semi_eco": "semi-eco", "force": "force buy", "full_buy": "full buy"}
LOW_BUY = ("eco", "semi_eco")
MAP_SIDE_K = 100  # shrinkage of the map side bias towards the dataset-wide side win rate
LOW_SITE_SAMPLE = 10  # a play backed by fewer plants than this carries the small-sample caveat


@dataclass
class _State:
    """Economy state of one team while the base scenario walks the rounds."""

    remaining: float = 0.0  # credits left per player after the previous round
    streak: int = 0  # consecutive losses before the current round
    prev_streak: int = 0  # streak before the previous round (needed for the income formula)
    won: bool | None = None  # result of the previous round
    typ: str | None = None  # round type of the previous round
    kills: float = 0.0


_TR: dict[int, pd.DataFrame] = {}


def cached_team_rounds(full: Store) -> pd.DataFrame:
    key = id(full)
    if key not in _TR:
        _TR.clear()
        _TR[key] = team_rounds(full)
    return _TR[key]


# ---- small helpers ----------------------------------------------------------------------------------------------------
def _flip(side: str) -> str:
    return "defense" if side == "attack" else "attack"


def _argmax(probs: dict[str, float]) -> str:
    return max(ROUND_TYPES, key=lambda t: probs.get(t, 0.0))


def _spend_table(tr: pd.DataFrame, team: str) -> dict[str, float]:
    glob = tr.groupby("round_type").spent_mean.mean().to_dict()
    mine = tr[tr.team_name == team].groupby("round_type").spent_mean.agg(["mean", "size"])
    return {t: float(mine.loc[t, "mean"]) if t in mine.index and mine.loc[t, "size"] >= 10 else float(glob.get(t, 0.0)) for t in ROUND_TYPES}


def _affordable(typ: str, credits_pp: float, spend: dict[str, float]) -> str:
    """Downgrade a predicted type the team cannot pay for (needs ~85% of the typical spend of that type)."""
    order = ["full_buy", "force", "semi_eco", "eco"]
    if typ not in order:
        return typ
    for t in order[order.index(typ):]:
        if t == "eco" or credits_pp >= 0.85 * spend.get(t, 0.0):
            return t
    return "eco"


def _picks(full: Store, team: str, map_name: str) -> pd.DataFrame:
    mp = full.match_players[(full.match_players.team_name == team) & full.match_players.agent_id.notna()]
    mp = mp.merge(full.matches[["match_id", "map_name", "winner_team"]], on="match_id")
    return mp[mp.map_name == map_name].assign(won=lambda d: d.team_name == d.winner_team)


def _agents(full: Store, team: str, map_name: str) -> list[AgentRecommendation]:
    cat = get_catalog()
    picks = _picks(full, team, map_name)
    out: list[AgentRecommendation] = []
    seen: set[str] = set()
    for aid, g in sorted(picks.groupby("agent_id"), key=lambda kv: -len(kv[1])):
        if len(out) >= 5:
            break
        ref = cat.agent(aid)
        n = len(g)
        out.append(AgentRecommendation(
            agent=ref, role=agent_class(ref.name),
            reason_pt=f"Usado {n} vez(es) pelo time neste mapa, com {f_pct(g.won.mean() * 100)} de vitórias.",
            evidence=make_stat(g.won.mean(), n, "matches")))
        seen.add(aid)
    if len(out) < 5:
        mp = full.match_players.merge(full.matches[["match_id", "map_name", "winner_team"]], on="match_id")
        mp = mp[(mp.map_name == map_name) & mp.agent_id.notna()].assign(won=lambda d: d.team_name == d.winner_team)
        for aid, g in sorted(mp.groupby("agent_id"), key=lambda kv: -len(kv[1])):
            if len(out) >= 5:
                break
            if aid in seen:
                continue
            ref = cat.agent(aid)
            out.append(AgentRecommendation(
                agent=ref, role=agent_class(ref.name),
                reason_pt=f"Agente popular em {map_name}: {f_pct(len(g) / len(mp) * 100)} dos jogadores o escolhem e vencem {f_pct(g.won.mean() * 100)}.",
                evidence=make_stat(g.won.mean(), len(g), "matches")))
    return out


# ---- buy table --------------------------------------------------------------------------------------------------------
class _Buys:
    """Most used weapon / armor per player, side and round type (from `round_player_stats` joined to the team rounds)."""

    def __init__(self, full: Store, tr: pd.DataFrame, team: str, puuids: list[str]):
        rps = full.round_player_stats
        d = rps[(rps.team_name == team) & rps.puuid.isin(puuids)][["match_id", "round_num", "puuid", "weapon_id", "armor_id"]]
        t = tr[tr.team_name == team][["match_id", "round_num", "round_type", "side"]]
        self.d = d.merge(t, on=["match_id", "round_num"])
        self.d["armor"] = [armor_level(a) for a in self.d.armor_id]

    def pick(self, puuid: str, side: str, rtype: str) -> tuple[str | None, str, int, int]:
        """(weapon_id, armor level, rounds with that weapon, rounds considered) from the narrowest sample with >= 3 rounds."""
        d = self.d
        for sub in (d[(d.puuid == puuid) & (d.side == side) & (d.round_type == rtype)],
                    d[(d.puuid == puuid) & (d.round_type == rtype)],
                    d[(d.side == side) & (d.round_type == rtype)]):
            if len(sub) >= 3:
                w = sub.weapon_id.dropna()
                wid = w.value_counts().index[0] if len(w) else None
                armor = sub.armor.value_counts().index[0]
                return wid, armor, int((sub.weapon_id == wid).sum()) if wid else 0, len(sub)
        return None, "none", 0, 0


# ---- the planner ------------------------------------------------------------------------------------------------------
def _team_stat(tr: pd.DataFrame, team: str, mask_fn, kind: str = "rounds") -> Stat:
    d = tr[(tr.team_name == team) & mask_fn(tr)]
    return make_stat(d.won.mean() if len(d) else None, len(d), kind)


def _enemy_insights(full: Store, enemy: str, players: list[PlayerScout], base: Baselines) -> tuple[list[Insight], list[Insight]]:
    """(team insights, player insights named after the player) for the enemy; empty on any failure (best effort)."""
    team_ins: list[Insight] = []
    player_ins: list[Insight] = []
    try:
        team_ins = engine.for_team(team_profile(full, enemy, full_store=full), base)
        for p in players:
            prof = player_profile(full, p.puuid, full_store=full)
            for i in engine.for_player(prof, base):
                if i.kind == "weakness":
                    player_ins.append(i.model_copy(update={"id": f"enemy-{i.id}-{p.name}", "text_pt": f"{p.name}: {i.text_pt}"}))
    except Exception:  # the plan must never fail because an insight could not be built
        pass
    return team_ins, player_ins


def _relevant_weak_points(team_ins: list[Insight], player_ins: list[Insight], my_side: str, enemy_type: str) -> list[Insight]:
    """Enemy weaknesses that matter for this round: its defense when we attack, its attack when we defend, the round type."""
    side_ids = ({"team-defense-weak", "team-retake-weak"} if my_side == "attack" else {"team-attack-weak", "team-site-predictable"})
    type_id = f"team-{enemy_type.replace('_', '-')}-weak"
    picked = [i for i in team_ins if i.id in side_ids or i.id == type_id]
    players = [i for i in player_ins if "first-death" in i.id or "opening" in i.id]
    return (picked + players[:2])[:3]


def _contingency(tr: pd.DataFrame, team: str, st: _State, n: int, pistol: bool) -> Contingency:
    if pistol or st.typ is None:
        o = ContingencyOutcome(round_type="pistol", summary_pt="Round de pistol: a economia reinicia, então não há contingência do round anterior.")
        return Contingency(if_previous_won=o, if_previous_lost=o)
    outs = {}
    for won in (True, False):
        streak = 0 if won else st.prev_streak + 1
        d = next_type_distribution(tr, st.typ, won, streak, team)
        t = _argmax(d["probs"])
        p, cnt = d["probs"][t], d["sample_size"]
        advice = {
            "full_buy": "mantenha o plano padrão e guarde utilitários para o pós-plant.",
            "force": "compre armas leves com escudo e jogue o primeiro contato em grupo.",
            "semi_eco": "compre só o essencial e jogue pela troca do primeiro abate.",
            "eco": "guarde as armas para o próximo round e tente cortar a economia do inimigo.",
            "pistol": "reinicie a economia.",
        }[t]
        src = "do time" if d["source"] == "team" else "do campeonato (o time tem pouco histórico)"
        outs[won] = ContingencyOutcome(
            round_type=t,
            summary_pt=f"Se {'vencer' if won else 'perder'} o R{n - 1}: tende a ir de {TYPE_PT[t]} ({f_pct(p * 100)} dos casos {src}, n = {cnt}); {advice}")
    return Contingency(if_previous_won=outs[True], if_previous_lost=outs[False])


def build_plan(full: Store, req: PlanRequest, base: Baselines | None = None, use_model: bool = True) -> PlanResponse:
    base = base or get_baselines(full)
    cat = get_catalog()
    tr = cached_team_rounds(full)
    win_model = get_win_model(full, tr) if use_model else None
    me, en = (req.team_a, req.team_b) if req.perspective == "a" else (req.team_b, req.team_a)
    map_name = req.map
    rph = req.rounds_per_half
    notes: list[str] = []

    my_players = scout_team(full, me, map_name, base)
    en_players = scout_team(full, en, map_name, base)
    views = site_views(full, me, en, map_name)
    my_plant_ms, _ = avg_plant_ms(full, me, map_name)
    en_plant_ms, en_plants = avg_plant_ms(full, en, map_name)
    map_matches = set(full.matches[full.matches.map_name == map_name].match_id)
    n_me_map = int(((full.matches.team_a == me) | (full.matches.team_b == me))[full.matches.map_name == map_name].sum())
    n_en_map = int(((full.matches.team_a == en) | (full.matches.team_b == en))[full.matches.map_name == map_name].sum())
    if n_me_map < T.MIN_MATCHES_ON_MAP:
        notes.append(f"{me} tem só {n_me_map} partida(s) em {map_name}: o plano usa também o histórico geral e o do campeonato.")
    if n_en_map < T.MIN_MATCHES_ON_MAP:
        notes.append(f"{en} tem só {n_en_map} partida(s) em {map_name}: as tendências do inimigo são do histórico geral.")
    if not views:
        notes.append(f"Sem plantes registrados em {map_name}: a escolha de site não tem dados.")
    notes.append("Cenário base: as vitórias são distribuídas pela probabilidade de cada round (um time com 40% vence cerca de 4 a cada 10 rounds), "
                 "em vez de repetir sempre o resultado mais provável; a contingência mostra o que muda se o resultado for outro.")
    notes.append("O plano descreve jogadas típicas (posição, momento, funções e economia); não há dados de utilitários ou lineups.")
    if win_model is not None and win_model.adopted:
        r = win_model.report
        notes.append(f"Probabilidades de vitória: modelo logístico validado em {r['test_matches']} partidas separadas do treino "
                     f"(erro de previsão {f_num(r['logloss_model'], 3)} contra {f_num(r['logloss_baseline'], 3)} da estimativa empírica).")

    team_ins, player_ins = _enemy_insights(full, en, en_players, base)
    spend_me, spend_en = _spend_table(tr, me), _spend_table(tr, en)
    kills_by_won = (tr.groupby("won").kills.mean() / 5).to_dict()
    plant_lost = tr[(tr.side == "attack") & ~tr.won].planted.mean()
    planted_and_lost = bool(plant_lost >= 0.5)
    start = req.starting_side

    # map side bias, shrunk towards the dataset-wide side win rate (applied to the base-scenario probability)
    tmap = tr[tr.match_id.isin(map_matches) & (tr.side == "attack")]
    g_att = base.rates.get("attack_win_rate", 0.5)
    delta_att = shrink(float(tmap.won.sum()), len(tmap), g_att, MAP_SIDE_K) - g_att if len(tmap) else 0.0

    buys_me = _Buys(full, tr, me, [p.puuid for p in my_players])
    route_cache: dict[tuple, tuple] = {}
    plan_cache: dict = {}  # heavy map_plan pieces shared between rounds
    hist = History()
    acc = 0.5  # error-diffusion accumulator of the base scenario
    ehist: dict = {"site": None, "lost": False}  # where the enemy last attacked and whether it lost that round

    sm, se = _State(), _State()
    rounds: list[RoundPlan] = []
    for n in range(1, 2 * rph + 1):
        half = 1 if n <= rph else 2
        side_me = start if half == 1 else _flip(start)
        side_en = _flip(side_me)
        pistol = n in (1, rph + 1)
        if pistol:
            sm, se = _State(), _State()
            cr_me = cr_en = float(ECONOMY["start"])
            t_me = t_en = "pistol"
            reasoning = "Round de pistol: os dois times começam com 800 créditos por jogador."
        else:
            cr_me = project_next_credits(sm.remaining, sm.won, sm.prev_streak, planted_and_lost and rounds[-1].side == "attack", sm.kills, None)
            cr_en = project_next_credits(se.remaining, se.won, se.prev_streak, planted_and_lost and rounds[-1].side == "defense", se.kills, None)
            d_me = next_type_distribution(tr, sm.typ, sm.won, sm.streak, me)
            d_en = next_type_distribution(tr, se.typ, se.won, se.streak, en)
            t_me = _affordable(_argmax(d_me["probs"]), cr_me, spend_me)
            t_en = _affordable(_argmax(d_en["probs"]), cr_en, spend_en)
            inc =income_per_player(sm.won, 0 if sm.won else sm.prev_streak + 1, False, sm.kills)
            reasoning = (f"Sobra do R{n - 1} ({f_num(sm.remaining, 0)} por jogador) + {f_num(inc, 0)} de "
                         f"{'vitória' if sm.won else f'derrota (sequência de {sm.prev_streak + 1})'} = cerca de {f_num(cr_me, 0)} por jogador. "
                         f"Tipo previsto: {TYPE_PT[t_me]} ({f_pct(d_me['probs'][_argmax(d_me['probs'])] * 100)} dos casos, n = {d_me['sample_size']}"
                         f"{', histórico do campeonato' if d_me['source'] == 'global' else ''}).")

        pm = round_win_probability(tr, me, side_me, t_me, t_en)
        pe = round_win_probability(tr, en, side_en, t_en, t_me)
        p = (pm["value"] + (1 - pe["value"])) / 2
        p += 0.5 * delta_att if side_me == "attack" else -0.5 * delta_att
        if win_model is not None:
            q = win_model.predict(me, en, side_me, t_me, t_en, map_name)
            if q is not None:
                p = q
        p = min(max(p, 0.02), 0.98)
        n_sample = min(pm["sample_size"], pe["sample_size"])
        wp = make_stat(p, n_sample, "rounds")
        # base scenario: wins are spread by probability (error diffusion), so a team that wins 40% of its rounds wins about
        # 4 in 10 of them instead of losing all of them; deterministic for the same request
        acc += p
        result = "win" if acc >= 1 else "loss"
        if result == "win":
            acc -= 1

        # ---- strategy
        if pistol:
            hist = History()
        hist.n = n
        rp = plan_round(side_me, t_me, views, me, en, my_players, en_players, my_plant_ms, en_plant_ms, base, hist) if views else None
        roles = assign_roles(my_players, side_me, base)
        if rp is not None:
            low = rp.best.sample < LOW_SITE_SAMPLE or wp.low_sample
            side_pt = {"attack": "no ataque", "defense": "na defesa"}
            form = (f"Histórico de vitórias do time em rounds {TYPE_PT[t_me]} {side_pt[side_me]}: {f_pct(pm['value'] * 100)} (n = {pm['sample_size']}); "
                    f"o {en} em rounds {TYPE_PT[t_en]} {side_pt[side_en]}: {f_pct(pe['value'] * 100)} (n = {pe['sample_size']}).")
            steps = ([rp.read] if rp.read else []) + list(rp.best.why) + [form] + rp.who + ([rp.target] if rp.target else []) + [rp.best.risk]
            strategy = RoundStrategy(summary_pt=rp.best.headline, site=rp.best.site, timing=rp.best.timing, steps_pt=[s for s in steps if s])
            if low:
                strategy.steps_pt.append("Amostra baixa nesta jogada: trate-a como hipótese e ajuste na leitura do primeiro contato.")
        else:
            strategy = RoundStrategy(summary_pt=f"Sem dados de sites em {map_name}: jogue em grupo e troque o primeiro abate.", steps_pt=[])

        # ---- buy
        buy: list[BuyItem] = []
        for player, role, _why in roles:
            wid, armor, wcount, total = buys_me.pick(player.puuid, side_me, t_me)
            wref = cat.weapon(wid) if wid else None
            if wref is None:
                reason = f"{player.name}: sem compra recorrente em rounds {TYPE_PT[t_me]}; guarde os créditos."
            else:
                wname = wref.name or "uma arma sem nome no catálogo"
                reason = f"{player.name} compra {wname} em {f_pct(wcount / max(total, 1) * 100)} dos rounds {TYPE_PT[t_me]} (n = {total})."
            buy.append(BuyItem(role=role, weapon=wref, armor=armor, reason_pt=reason))

        # ---- enemy move
        target_site = None
        if side_me == "defense" and views:
            use = sum(v.enemy_plants for v in views.values()) >= T.SITE_CONCEDED_MIN_PLANTS
            key = (lambda v: v.enemy_plants) if use else (lambda v: v.map_plants)
            ranked = sorted(views.values(), key=key, reverse=True)
            target_site = ranked[0].site
            # the enemy rotates too: after a lost attack on its favourite site it may try the runner-up
            if (len(ranked) > 1 and ehist["site"] == target_site and ehist["lost"] and key(ranked[1]) >= 0.6 * key(ranked[0])):
                target_site = ranked[1].site
        elif views:
            # attacking: the enemy defends the site we are going for
            target_site = rp.best.site if rp is not None else max(views.values(), key=lambda v: v.vs_plants or v.map_plants * 0.0001).site
        move = _enemy_move(full, views, en, side_en, target_site, en_plant_ms, map_name, t_en, route_cache, tr)

        try:
            enemy_pts, enemy_snaps = route_cache.get((side_en, move.site), ([], 0)) if move.site else ([], 0)
            assigned = [(pl, role) for pl, role, _ in roles]
            map_site = (rp.best.site if (rp is not None and side_me == "attack") else move.site)
            mp = build_map_plan(full, me, en, map_name, side_me, map_site, assigned, enemy_pts, enemy_snaps, plan_cache)
        except Exception:  # drawing is a bonus: the plan never fails because of it
            mp = None

        weak = _relevant_weak_points(team_ins, player_ins, side_me, t_en)
        cont = _contingency(tr, me, sm, n, pistol)

        tips: list[Insight] = []
        if wp.value is not None and wp.value < 0.4:
            tips.append(make_insight(f"round-{n}-hard", "tip",
                                     f"Round difícil: vitória estimada de {f_pct(wp.value * 100)}. Priorize trocas e não force duelos isolados.",
                                     "vitória estimada", wp.value * 100, wp.sample_size, 50, "%"))
        if t_en in LOW_BUY and t_me == "full_buy":
            st_eco = _team_stat(tr, en, lambda d: d.round_type.isin(LOW_BUY))
            if st_eco.value is not None:
                tips.append(make_insight(f"round-{n}-eco-enemy", "tip",
                                         f"O inimigo deve estar em {TYPE_PT[t_en]}, mas vence {f_pct(st_eco.value * 100)} desses rounds: jogue junto e não entregue armas.",
                                         "vitórias do inimigo com economia fraca", st_eco.value * 100, st_eco.sample_size, None, "%"))
        if t_me in LOW_BUY and t_en == "full_buy":
            st_me = _team_stat(tr, me, lambda d: d.round_type.isin(LOW_BUY))
            if st_me.value is not None:
                tips.append(make_insight(f"round-{n}-eco-me", "tip",
                                         f"Economia fraca contra full buy: o time vence {f_pct(st_me.value * 100)} desses rounds. Salvar armas pode valer mais que forçar.",
                                         "vitórias com economia fraca", st_me.value * 100, st_me.sample_size, None, "%"))

        rounds.append(RoundPlan(
            number=n, half=half, side=side_me, round_type=t_me, base_scenario_result=result, win_probability=wp,
            projected_economy=ProjectedEconomy(team_credits=int(round(cr_me * 5)), enemy_credits=int(round(cr_en * 5)), reasoning_pt=reasoning),
            buy=buy, strategy=strategy, enemy_weak_points=weak, enemy_probable_strategy=move, contingency=cont, insights=tips,
            map_plan=mp))

        # ---- advance the base scenario
        won_me = result == "win"
        played_site = strategy.site if rp is not None else None
        hist.repeat = hist.repeat + 1 if (hist.prev_side == side_me and hist.prev_site == played_site and played_site) else 1
        hist.prev_side, hist.prev_site, hist.prev_won = side_me, played_site, won_me
        hist.wins, hist.losses = (hist.wins + 1, 0) if won_me else (0, hist.losses + 1)
        if side_en == "attack":
            ehist["site"], ehist["lost"] = move.site, won_me  # the enemy lost its attack when we won the round
        else:
            ehist["site"], ehist["lost"] = None, False
        for st, won, typ, cr, spend, side in ((sm, won_me, t_me, cr_me, spend_me, side_me), (se, not won_me, t_en, cr_en, spend_en, side_en)):
            st.prev_streak = st.streak
            st.streak = 0 if won else st.streak + 1
            st.won, st.typ = won, typ
            st.remaining = max(cr - spend.get(typ, 0.0), 0.0)
            st.kills = float(kills_by_won.get(won, 0.0))

    return PlanResponse(
        team_a=TeamRef(name=req.team_a), team_b=TeamRef(name=req.team_b), perspective=req.perspective, map=cat.map_ref(map_name),
        rounds_per_half=rph, starting_side=start, agents=_agents(full, me, map_name),
        opponent=_opponent(full, tr, views, en, map_name, en_plant_ms, en_plants, team_ins, n_en_map, notes), rounds=rounds,
        narrative_pt=None, text_source="rules", notes_pt=notes)


def _enemy_move(full: Store, views: dict[str, SiteView], enemy: str, side_en: str, site: str | None, plant_ms: float | None,
                map_name: str, t_en: str, cache: dict, tr: pd.DataFrame) -> EnemyMove:
    prefix = f"Compra fraca esperada ({TYPE_PT[t_en]}): possível rush. " if t_en in LOW_BUY else ""
    if site is None or site not in views:
        return EnemyMove(summary_pt=prefix + "Sem dados suficientes sobre as jogadas do inimigo neste mapa.", site=None, route=[],
                         evidence=make_stat(None, 0, "events"))
    v = views[site]
    key = (side_en, site)
    if key not in cache:
        cache[key] = enemy_route(full, enemy, map_name, side_en, site if side_en == "attack" else None)
    route, snaps = cache[key]
    if side_en == "attack":
        used_enemy = sum(x.enemy_plants for x in views.values()) >= T.SITE_CONCEDED_MIN_PLANTS
        n = v.enemy_plants if used_enemy else v.map_plants
        total = sum((x.enemy_plants if used_enemy else x.map_plants) for x in views.values())
        share = n / total if total else None
        _, hint = timing_of(plant_ms)
        who = f"O {enemy} costuma atacar o site {site} ({f_pct((share or 0) * 100)} dos plantes, n = {total})" if used_enemy else \
            f"Sem histórico suficiente do {enemy} no mapa; no geral {f_pct((share or 0) * 100)} dos plantes saem no site {site} (n = {total})"
        text = prefix + who + (f"; {hint}." if hint else ".")
        if route:
            text += f" O caminho médio dos jogadores aparece no mapa (n = {snaps} posições)."
        return EnemyMove(summary_pt=text, site=site, route=route, evidence=make_stat(share, total, "events"))
    total = sum(x.vs_plants for x in views.values())
    share = v.vs_plants / total if total else None
    text = prefix + (f"O site {site} é o mais pressionado contra o {enemy} ({f_pct((share or 0) * 100)} dos plantes sofridos, n = {total}): espere resistência ali."
                     if total else f"Sem histórico de ataques contra o {enemy} neste mapa.")
    if route:
        text += f" As posições médias dos defensores aparecem no mapa (n = {snaps} posições)."
    return EnemyMove(summary_pt=text, site=site, route=route, evidence=make_stat(share, total, "events"))


def _opponent(full: Store, tr: pd.DataFrame, views: dict[str, SiteView], enemy: str, map_name: str, plant_ms: float | None,
              plants: int, team_ins: list[Insight], matches_on_map: int, notes: list[str]) -> OpponentSummary:
    mm = set(full.matches[full.matches.map_name == map_name].match_id)
    on_map = tr[tr.match_id.isin(mm)]

    def side_stat(side: str) -> Stat:
        s = _team_stat(on_map, enemy, lambda d: d.side == side)
        return s if s.sample_size >= T.MIN_TEAM_ROUNDS else _team_stat(tr, enemy, lambda d: d.side == side)

    pref = None
    if views:
        best = max(views.values(), key=lambda v: v.enemy_plants)
        pref = best.site if best.enemy_plants else None
    return OpponentSummary(
        team=TeamRef(name=enemy), matches_on_map=matches_on_map, preferred_site=pref,
        avg_time_to_plant_ms=make_stat(plant_ms, plants, "events"), attack_win_rate=side_stat("attack"),
        defense_win_rate=side_stat("defense"),
        pistol_win_rate=_team_stat(tr, enemy, lambda d: d.round_type == "pistol", "events"),
        eco_win_rate=_team_stat(tr, enemy, lambda d: d.round_type.isin(LOW_BUY)), insights=team_ins)
