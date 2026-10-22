"""Steps 3-4 of the chat: call the existing engines (the same functions the dashboard endpoints use) and turn their
output into typed blocks. No metric is computed here: every number is formatted from an engine result.
"""
from __future__ import annotations

from urllib.parse import quote, urlencode

from fastapi import HTTPException

from ..routers import maps as r_maps
from ..routers import matches as r_matches
from ..routers import meta as r_meta
from ..routers import players as r_players
from ..routers import plan as r_plan
from ..routers import teams as r_teams
from ..schemas import PlanRequest
from ..schemas.chat import (ChatContext, ChatResponse, ChoiceOption, ChoicesBlock, DashboardLink, InsightsBlock, PlanRoundSummary,
                            PlanSummaryBlock, StatItem, StatsBlock, TableBlock, TextBlock, WarningBlock)
from ..schemas.common import Stat
from .understand import Understood, names

ROUND_TYPE = {"pistol": "pistola", "eco": "eco", "semi_eco": "semi-eco", "force": "force buy", "full_buy": "compra cheia"}
SIDE = {"attack": "ataque", "defense": "defesa"}
CLASS = {"attack": "favorece o ataque", "defense": "favorece a defesa", "balanced": "equilibrado"}
SUGGESTIONS = ["Informações do jogador …", "Detalhes do mapa …", "Plano contra o time … no mapa …", "Resumo do campeonato …"]


def _n(x: float | None, d: int = 2) -> str:
    return "—" if x is None else f"{x:.{d}f}".replace(".", ",")


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.0f}%".replace(".", ",")


def _stat(label: str, s: Stat, fmt=_n) -> StatItem:
    return StatItem(label=label, value=fmt(s.value), sample_size=s.sample_size, low_sample=s.low_sample)


def _insights(items, kinds, title, limit=3) -> InsightsBlock | None:
    sel = [i for i in items if i.kind in kinds][:limit]
    return InsightsBlock(title=title, items=sel) if sel else None


def _blocks(*bs):
    return [b for b in bs if b is not None]


def _prows(rows) -> list[list[str]]:  # /api/leaderboards rows are plain dicts
    return [[str(r["rank"]), r["player"].riot_id, r["team"].name if r.get("team") else "—", _n(r["value"]), str(r["matches"])] for r in rows]


def _trows(rows) -> list[list[str]]:
    return [[str(r["rank"]), r["team"].name, _pct(r["value"]), str(r["matches"])] for r in rows]


def reply(intent, ctx: ChatContext, blocks, dashboard=None, note=None, source="rules", suggestions=None) -> ChatResponse:
    return ChatResponse(intent=intent, source=source, context=ctx, blocks=blocks, dashboard=dashboard, note=note, suggestions=suggestions)


def help_reply(ctx: ChatContext, intro: str | None = None) -> ChatResponse:
    nm = names()
    p = nm.players[0][1] if nm.players else "um jogador"
    t = nm.teams[0] if nm.teams else "um time"
    m = nm.maps[0] if nm.maps else "um mapa"
    text = intro or "Eu respondo perguntas sobre os dados das partidas: jogadores, times, mapas, partidas, campeonatos e o plano de ação contra um adversário."
    return reply("help", ctx, [TextBlock(text=text), TextBlock(text=f"Experimente: “informações do jogador {p}”, “detalhes do mapa {m}”, “plano contra o time {t} no mapa {m}” ou “resumo do campeonato”."),
                              TextBlock(text="Também dá para navegar pelo menu lateral, sem usar o chat. Eu só analiso partidas passadas; não ajudo durante uma partida em andamento.")],
                 suggestions=SUGGESTIONS)


def choices_reply(intent, ctx: ChatContext, prompt: str, options: list[ChoiceOption]) -> ChatResponse:
    return reply(intent, ctx, [ChoicesBlock(prompt=prompt, options=options[:6])])


def not_found(ctx: ChatContext, what: str) -> ChatResponse:
    return reply("unknown", ctx, [WarningBlock(text=f"Não encontrei “{what}” nos dados. Confira a grafia ou escolha pelo menu lateral."),
                                  TextBlock(text="Dica: o nome precisa existir nas partidas carregadas; posso procurar por parte do nome.")], suggestions=SUGGESTIONS)


# ── per-intent composers ──────────────────────────────────────────────────────────────────────

def player(puuid: str, ctx: ChatContext) -> ChatResponse:
    p = r_players.player(puuid)
    s = p.stats
    team = p.teams[0].name if p.teams else None
    role = p.roles[0].role if p.roles else None
    head = f"{p.player.riot_id}" + (f" · {team}" if team else "") + f" · {s.matches} mapas, {s.rounds} rounds"
    if role:
        head += f" · papel mais provável: {role}"
    if p.favorite_agent and p.favorite_agent.name:
        head += f" · agente favorito: {p.favorite_agent.name}"
    stats = StatsBlock(items=[_stat("K/D", s.kd), _stat("ADR", s.adr, lambda v: _n(v, 0)), _stat("HS%", s.hs_pct, _pct),
                              _stat("Duelos de abertura vencidos", s.opening_duel_win_pct, _pct)])
    best = max((m for m in p.by_map if m.matches >= 2), key=lambda m: m.kd.value or 0, default=None)
    extra = TextBlock(text=f"Melhor mapa por K/D: {best.map.name} ({_n(best.kd.value)} em {best.matches} partidas).") if best else None
    ctx = ctx.model_copy(update={"player_puuid": puuid, "team": team or ctx.team})
    return reply("player", ctx, _blocks(TextBlock(text=head), stats, extra, _insights(p.insights, {"strength"}, "Pontos fortes"),
                                         _insights(p.insights, {"weakness", "tip"}, "Onde pode melhorar")),
                 DashboardLink(path=f"/jogador/{puuid}"))


def team(name: str, ctx: ChatContext) -> ChatResponse:
    t = r_teams.team(name)
    r = t.record
    head = f"{name} · {r.matches} mapas, {r.wins} vitórias e {r.losses} derrotas em séries"
    stats = StatsBlock(items=[_stat("Rounds vencidos", r.round_win_rate, _pct), _stat("Ataque", r.attack_win_rate, _pct), _stat("Defesa", r.defense_win_rate, _pct),
                              _stat("Pistol rounds", t.economy.pistol_win_rate, _pct)])
    maps = sorted(t.by_map, key=lambda m: -m.matches)[:5]
    table = TableBlock(title="Mapas mais jogados", columns=["Mapa", "Jogos", "Vitórias"],
                       rows=[[m.map.name, str(m.matches), _pct(m.win_rate.value) + (" ⚠" if m.win_rate.low_sample else "")] for m in maps]) if maps else None
    ctx = ctx.model_copy(update={"team": name, "player_puuid": None})
    return reply("team", ctx, _blocks(TextBlock(text=head), stats, table, _insights(t.insights, {"strength"}, "Pontos fortes"),
                                       _insights(t.insights, {"weakness", "tip", "strategy"}, "Pontos fracos e recomendações")),
                 DashboardLink(path=f"/time/{quote(name)}"))


def map_(name: str, ctx: ChatContext) -> ChatResponse:
    m = r_maps.map_profile_endpoint(name)
    head = f"{m.map.name} · {m.matches} partidas, {m.rounds} rounds · {CLASS[m.classification]}"
    stats = StatsBlock(items=[_stat("Vitória no ataque", m.attack_win_rate, _pct), _stat("Vitória na defesa", m.defense_win_rate, _pct)])
    sites = TableBlock(title="Sites", columns=["Site", "Plantes", "Defuse", "Retomada"],
                       rows=[[s.site, str(s.plants), _pct(s.defuse_rate.value), _pct(s.retake_rate.value)] for s in m.sites]) if m.sites else None
    agents = [a.name for a in m.top_agents[:5] if a.name]
    ag = TextBlock(text="Agentes mais usados: " + ", ".join(agents) + ".") if agents else None
    note = None if m.map.has_minimap else WarningBlock(text=f"{m.map.name} não tem minimapa no catálogo fornecido; as camadas do mapa ficam indisponíveis.")
    ctx = ctx.model_copy(update={"map": m.map.name})
    return reply("map", ctx, _blocks(TextBlock(text=head), stats, sites, ag, note, _insights(m.insights, {"strength", "weakness", "tip", "strategy"}, "Pontos de atenção", 4)),
                 DashboardLink(path=f"/mapa/{quote(m.map.name)}"))


def match_(team_name: str, ctx: ChatContext) -> ChatResponse:
    t = r_teams.team(team_name)
    if not t.matches:
        return not_found(ctx, team_name)
    last = max(t.matches, key=lambda x: x.date)
    rep = r_matches.match(last.match_id)
    a, b = rep.team_a, rep.team_b
    win = a if rep.winner == "a" else b
    head = f"{a.team.name} {a.score} x {b.score} {b.team.name} · {rep.map.name} · {rep.date[:10]} · {rep.tournament}. Venceu: {win.team.name}."
    mine = rep.insights_a if a.team.name == team_name else rep.insights_b
    mvp = TextBlock(text=f"Destaque da partida: {rep.mvp.riot_id}.") if rep.mvp else None
    ctx = ctx.model_copy(update={"team": team_name, "map": rep.map.name})
    return reply("match", ctx, _blocks(TextBlock(text="Última partida de " + team_name + ": " + head), mvp, _insights(mine, {"strength"}, f"Pontos fortes de {team_name}", 2),
                                        _insights(mine, {"weakness", "tip"}, f"A melhorar em {team_name}", 2)),
                 DashboardLink(path=f"/partida/{rep.match_id}"))


def plan(a: str, b: str, map_name: str, ctx: ChatContext) -> ChatResponse:
    req = PlanRequest(team_a=a, team_b=b, map=map_name)
    try:
        p = r_plan.plan(req)
    except HTTPException as e:
        return reply("plan", ctx, [WarningBlock(text=f"Não consegui montar o plano: {e.detail}")])
    rounds = [r for r in p.rounds if r.number in (1, 2, 3, p.rounds_per_half + 1)]
    summary = [PlanRoundSummary(number=r.number, side=SIDE[r.side], round_type=ROUND_TYPE[r.round_type], summary_pt=r.strategy.summary_pt,
                                buy_pt=r.projected_economy.reasoning_pt) for r in rounds]
    o = p.opponent
    site = f", com preferência pelo site {o.preferred_site}" if o.preferred_site else ""
    head = f"Plano de {a} contra {b} em {p.map.name}: {len(p.rounds)} rounds simulados. O adversário tem {o.matches_on_map} partidas neste mapa{site}."
    agents = [x.agent.name for x in p.agents if x.agent.name]
    ag = TextBlock(text="Composição sugerida pelo histórico: " + ", ".join(agents) + ".") if agents else None
    lowmap = WarningBlock(text="O adversário tem poucas partidas neste mapa; o plano usa também o histórico geral do time.") if o.matches_on_map < 3 else None
    block = PlanSummaryBlock(title="Rounds-chave do plano", rounds=summary, weak_points=[i for i in o.insights if i.kind == "weakness"][:3], pdf_request=req)
    q = urlencode({"teamA": a, "teamB": b, "map": p.map.name, "run": 1})
    ctx = ctx.model_copy(update={"team": a, "team_b": b, "map": p.map.name})
    return reply("plan", ctx, _blocks(TextBlock(text=head), ag, lowmap, block), DashboardLink(path=f"/plano?{q}"), note="; ".join(p.notes_pt) or None)


def tournament(tid: str | None, ctx: ChatContext) -> ChatResponse:
    m = r_meta.meta()
    ts = m["tournaments"]
    sel = next((t for t in ts if t["id"] == tid), None)
    if sel is None:
        rows = [[t["name"], str(len(t["phases"]) or 1), str(t["matches"])] for t in ts]
        return reply("tournament", ctx, [TextBlock(text=f"Há {len(ts)} campeonatos nos dados, de {m['date_from'][:10]} a {m['date_to'][:10]}."),
                                         TableBlock(columns=["Campeonato", "Fases", "Partidas"], rows=rows), TextBlock(text="Pergunte por um deles para ver os destaques.")],
                     DashboardLink(label="Ver campeonatos", path="/campeonatos"))
    board = r_meta.leaderboards(tid)
    top_p = board["players"]["kd"][:5]
    top_t = board["teams"]["win_rate"][:5]
    ctx = ctx.model_copy(update={"tournament": tid})
    return reply("tournament", ctx, _blocks(
        TextBlock(text=f"{sel['name']} · {sel['matches']} partidas" + (f" · fases: {', '.join(sel['phases'])}" if sel["phases"] else "")),
        TableBlock(title="Melhores jogadores por K/D", columns=["#", "Jogador", "Time", "K/D", "Mapas"],
                   rows=_prows(top_p)),
        TableBlock(title="Times com mais vitórias", columns=["#", "Time", "Aproveitamento", "Mapas"],
                   rows=_trows(top_t))),
        DashboardLink(path=f"/campeonatos?tournament={quote(tid)}"))


def _leaders(ctx: ChatContext) -> ChatResponse:
    board = r_meta.leaderboards(ctx.tournament)
    return reply("leaderboard", ctx, [
        TableBlock(title="Melhores jogadores por K/D (mínimo de 5 mapas)", columns=["#", "Jogador", "Time", "K/D", "Mapas"],
                   rows=_prows(board["players"]["kd"][:5])),
        TableBlock(title="Times com mais vitórias", columns=["#", "Time", "Aproveitamento", "Mapas"],
                   rows=_trows(board["teams"]["win_rate"][:5]))],
        DashboardLink(path="/campeonatos"))


def dispatch(u: Understood, ctx: ChatContext) -> ChatResponse:
    """Run the engine for the understood intent. Ambiguity and missing pieces come back as questions, never guesses."""
    ctx = ctx.model_copy(deep=True)
    if u.intent == "help":
        return help_reply(ctx)
    if u.intent == "player":
        if len(u.players) > 1:
            return choices_reply("player", ctx, "Encontrei mais de um jogador com esse nome. Qual deles?", [ChoiceOption(label=f"{p[1]} · {p[2]}", send=f"jogador {p[1]}") for p in u.players])
        return player(u.players[0][0], ctx)
    if u.intent == "team":
        return team(u.teams[0], ctx)
    if u.intent == "map":
        return map_(u.map, ctx)  # type: ignore[arg-type]
    if u.intent == "match":
        return match_(u.teams[0], ctx)
    if u.intent == "tournament":
        return tournament(u.tournament, ctx)
    if u.intent == "leaderboard":
        return _leaders(ctx)
    if u.intent == "plan":
        a = u.teams[0] if u.teams else ctx.team
        b = u.teams[1] if len(u.teams) > 1 else (ctx.team_b if ctx.team_b and ctx.team_b != a else None)
        if a and not b and ctx.team and ctx.team != a:  # "plano contra X" after talking about Y
            a, b = ctx.team, a
        mp = u.map or ctx.map
        if not (a and b and mp):
            missing = ["os dois times" if not a else "o segundo time" if not b else None, None if mp else "o mapa"]
            return reply("plan", ctx, [TextBlock(text="Para montar o plano são necessários dois times e um mapa. Faltou informar " + " e ".join(m for m in missing if m) + "."),
                                       TextBlock(text="Exemplo: “plano do time A contra o time B no mapa Ascent”. O primeiro time é o que recebe o plano.")], suggestions=SUGGESTIONS)
        return plan(a, b, mp, ctx)
    if u.miss:
        return not_found(ctx, u.miss)
    return help_reply(ctx, "Não entendi a pergunta. Eu consigo:")
