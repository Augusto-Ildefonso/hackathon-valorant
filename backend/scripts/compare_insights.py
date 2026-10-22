"""Rules vs LLM insight mode on the same entities (Stream D). Usage, from the repo root (key in .env):

    backend/.venv/bin/python backend/scripts/compare_insights.py [--players 5 --teams 4 --maps 2 --matches 3]

Writes `.claude/docs/insights-comparison.md` (aggregate metrics + side-by-side texts). The LLM is run WITHOUT the
coherence guard (`strict=False`) so the report can say how often the raw model over-claims; "LLM com guarda" is what the
app would serve (the same answers minus the ones the guard rejects).
Coverage is measured on topics: every rule id and every cited fact id is mapped to the metric it is about.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.analytics.maps import map_profile  # noqa: E402
from app.analytics.matches import match_report  # noqa: E402
from app.analytics.players import player_profile  # noqa: E402
from app.analytics.teams import team_profile  # noqa: E402
from app.deps import get_store  # noqa: E402
from app.insights import engine, llm, llm_insights  # noqa: E402
from app.insights.baselines import get_baselines  # noqa: E402
from app.metrics import player_table, team_table  # noqa: E402

RULE_TOPICS = [
    ("player-first-death", "first_death"), ("player-kd", "kd"), ("player-adr", "adr"), ("player-hs", "hs"), ("player-opening", "opening"),
    ("player-trade", "trade"), ("player-weapon", "weapon"), ("player-map", "map"),
    ("team-attack", "attack_wr"), ("team-defense", "defense_wr"), ("team-pistol", "type:pistol"), ("team-semi-eco", "type:semi_eco"),
    ("team-eco", "type:eco"), ("team-force", "type:force"), ("team-full-buy", "type:full_buy"), ("team-post-plant", "post_plant"),
    ("team-retake", "retake"), ("team-site", "site"), ("team-map", "map"), ("team-trend", "trend_last3"), ("team-role", "roles"),
    ("map-side", "attack_wr,defense_wr"), ("map-site", "site"), ("map-blind", "zone"),
    ("match-pistol", "pistols"), ("match-eco", "eco_vs_full"), ("match-fullbuy", "full_vs_eco_lost"), ("match-side-attack", "attack_wr"),
    ("match-side-defense", "defense_wr"), ("match-opening", "openings"), ("match-streak", "losing_streak"), ("match-site", "site"),
]


def rule_topics(rule_id: str) -> set[str]:
    for prefix, topics in RULE_TOPICS:
        if rule_id.startswith(prefix):
            return set(topics.split(","))
    return {rule_id}


def fact_topic(fid: str) -> str:
    f = re.sub(r"^[ab]:", "", fid)
    head = f.split(":")[0]
    if head == "type":
        return f
    if head == "map" and f.count(":") == 2:
        return "map"
    return head


def words(t: str) -> int:
    return len(t.split())


def fmt(i, with_ev=True, flag="") -> str:
    ev = i.evidence
    tail = f" _[{ev.metric}: {ev.value:g}{ev.unit or ''}" + (f" · ref {ev.baseline:g}" if ev.baseline is not None else "") + f" · n={ev.sample_size}{' · amostra baixa' if i.low_sample else ''}]_" if with_ev else ""
    return f"{flag}**{i.kind}** — {i.text_pt}{tail}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=5)
    ap.add_argument("--teams", type=int, default=4)
    ap.add_argument("--maps", type=int, default=2)
    ap.add_argument("--matches", type=int, default=3)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    if not llm.enabled():
        sys.exit("LLM is off: set GEMINI_API_KEY in .env (and do not set VAVAGYM_LLM=0)")

    s = get_store()
    base = get_baselines(s)
    pt = player_table(s)
    players = list(pt[pt.rounds >= 150].sort_values("rounds", ascending=False).index[:args.players - 1]) + list(pt[(pt.rounds >= 40) & (pt.rounds < 120)].index[:1])
    tt = team_table(s).sort_values("matches", ascending=False)
    teams = list(tt.index[:args.teams - 1]) + list(tt[tt.matches == 3].index[:1])
    maps = list(s.matches.map_name.value_counts().index[:args.maps])
    matches = list(s.matches.sort_values("game_start_ms").groupby("map_name").tail(1).match_id[:args.matches])

    def job_player(pid):
        prof = player_profile(s, pid, s)
        return "jogador", prof.player.riot_id, engine.for_player(prof, base), llm_insights.for_player(prof, base, strict=False)

    def job_team(t):
        prof = team_profile(s, t, s)
        return "time", t, engine.for_team(prof, base), llm_insights.for_team(prof, base, strict=False)

    def job_map(m):
        sm = s.where(map_name=m)
        prof = map_profile(sm, m)
        return "mapa", m, engine.for_map(prof, sm), llm_insights.for_map(prof, sm, strict=False)

    def job_match(mid):
        rep = match_report(s, mid)
        a, b = engine.for_match(rep)
        return "partida", f"{rep.team_a.team.name} x {rep.team_b.team.name} ({rep.map.name})", a + b, llm_insights.for_match(rep, strict=False)

    jobs = [lambda p=p: job_player(p) for p in players] + [lambda t=t: job_team(t) for t in teams] + \
           [lambda m=m: job_map(m) for m in maps] + [lambda x=x: job_match(x) for x in matches]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        raw = list(pool.map(lambda j: j(), jobs))

    results = []
    for kind, name, rules, run in raw:
        every = run.insights if kind != "partida" else run.by_team.get("a", []) + run.by_team.get("b", [])
        kept = [i for i in every if i.id not in run.violations]
        rule_t = set().union(*[rule_topics(i.id) for i in rules]) if rules else set()
        llm_t = {fact_topic(f) for i in kept for f in run.cited_ids[i.id]}
        results.append({"kind": kind, "name": name, "rules": rules, "all": every, "kept": kept, "run": run, "rule_topics": rule_t, "llm_topics": llm_t})
        print(f"{kind:8} {name[:40]:40} rules={len(rules):2} llm={len(every):2} guard-rejects={len(run.violations):2} hard-rejects={len(run.rejected)} "
              f"{run.seconds:5.1f}s {'cache' if run.cached else ''} {run.error or ''}", flush=True)

    n_r = sum(len(r["rules"]) for r in results)
    n_all = sum(len(r["all"]) for r in results)
    n_kept = sum(len(r["kept"]) for r in results)
    asked = sum(r["run"].requested for r in results)
    rej = sum(len(r["run"].rejected) for r in results)
    viol = sum(len(r["run"].violations) for r in results)
    cov_num = sum(len(r["rule_topics"] & r["llm_topics"]) for r in results)
    cov_den = sum(len(r["rule_topics"]) for r in results)
    novel = sum(1 for r in results for i in r["kept"] if not ({fact_topic(f) for f in r["run"].cited_ids[i.id]} & r["rule_topics"]))
    cross = sum(1 for r in results for i in r["kept"] if len({fact_topic(f) for f in r["run"].cited_ids[i.id]}) >= 2)
    secs = [r["run"].seconds for r in results if not r["run"].cached]
    lowsmp = sum(1 for r in results for i in r["kept"] if i.low_sample)
    by_kind = lambda lst: {k: sum(1 for i in lst if i.kind == k) for k in ("strength", "weakness", "tip", "strategy")}  # noqa: E731
    kinds_rules = by_kind([i for r in results for i in r["rules"]])
    kinds_llm = by_kind([i for r in results for i in r["kept"]])
    out = ROOT / ".claude" / "docs"
    out.mkdir(parents=True, exist_ok=True)
    L = [f"# Regras × LLM: comparação de insights ({time.strftime('%Y-%m-%d')})", "",
         f"Modelos (ordem de tentativa): {', '.join(llm.gemini_models())}. Amostra: {len(players)} jogadores, {len(teams)} times, {len(maps)} mapas, {len(matches)} partidas. "
         "Gerado por `backend/scripts/compare_insights.py`. Os números vêm sempre do código; o LLM só escolhe os fatos e redige.", "",
         "## Métricas", "", "| métrica | valor |", "|---|---|",
         f"| insights por regras | {n_r} |", f"| insights propostos pelo LLM | {asked} |",
         f"| rejeitados pela validação dura (id inexistente, número fora dos fatos citados, formato) | {rej} ({(rej / asked * 100 if asked else 0):.0f}% dos propostos) |",
         f"| aceitos pela validação dura, antes da guarda de coerência | {n_all} |",
         f"| desses, reprovados pela guarda de coerência (ponto forte/fraco fora da faixa, direção errada, amostra baixa) | {viol} ({(viol / n_all * 100 if n_all else 0):.0f}%) |",
         f"| **insights do LLM servidos (com guarda)** | **{n_kept}** |",
         f"| tópicos das regras também cobertos pelo LLM (com guarda) | {cov_num} de {cov_den} ({(cov_num / cov_den * 100 if cov_den else 0):.0f}%) |",
         f"| insights do LLM sobre um tópico que nenhuma regra cobre | {novel} de {n_kept} |",
         f"| insights do LLM que cruzam 2+ tópicos | {cross} de {n_kept} |",
         f"| insights do LLM com amostra baixa declarada | {lowsmp} de {n_kept} |",
         f"| tipos (strength/weakness/tip/strategy): regras | {kinds_rules['strength']}/{kinds_rules['weakness']}/{kinds_rules['tip']}/{kinds_rules['strategy']} |",
         f"| tipos (strength/weakness/tip/strategy): LLM com guarda | {kinds_llm['strength']}/{kinds_llm['weakness']}/{kinds_llm['tip']}/{kinds_llm['strategy']} |",
         f"| tamanho médio do texto (palavras): regras / LLM | {sum(words(i.text_pt) for r in results for i in r['rules']) / max(n_r, 1):.1f} / {sum(words(i.text_pt) for r in results for i in r['kept']) / max(n_kept, 1):.1f} |",
         f"| latência média por chamada (sem cache) | {(sum(secs) / len(secs) if secs else 0):.1f} s |", ""]
    notes = Path(__file__).with_name("insights_comparison_conclusions.md")
    if notes.exists():
        L += [notes.read_text(), ""]
    for r in results:
        run = r["run"]
        L += [f"## {r['kind'].capitalize()}: {r['name']}", "",
              f"Fatos enviados: {run.n_facts} · propostos {run.requested} · rejeitados (duro) {len(run.rejected)} · reprovados na guarda {len(run.violations)} · {run.seconds:.1f} s{' (cache)' if run.cached else ''}"
              + (f" · erro: {run.error}" if run.error else ""), "",
              f"Tópicos das regras: {', '.join(sorted(r['rule_topics'])) or '—'}. Tópicos citados pelo LLM (com guarda): {', '.join(sorted(r['llm_topics'])) or '—'}.", "",
              "**Regras**", ""] + ([f"- {fmt(i, False)}" for i in r["rules"]] or ["- (nenhum)"]) + ["", "**LLM** (🚫 = reprovado pela guarda de coerência)", ""]
        flag = lambda i: f"🚫 [{run.violations[i.id]}] " if i.id in run.violations else ""  # noqa: E731
        if r["kind"] == "partida":
            for t in ("a", "b"):
                L += [f"- _time {t}_"] + [f"  - {fmt(i, True, flag(i))}" for i in run.by_team.get(t, [])]
        else:
            L += [f"- {fmt(i, True, flag(i))}" for i in r["all"]] or ["- (nenhum)"]
        if run.rejected:
            L += ["", "Rejeitados (validação dura):"] + [f"- {why}: “{txt}”" for txt, why in run.rejected]
        L.append("")
    (out / "insights-comparison.md").write_text("\n".join(L))
    print(f"\nwrote {out / 'insights-comparison.md'}")
    print(f"rules={n_r} asked={asked} hard-rejected={rej} accepted={n_all} guard-rejected={viol} served={n_kept} coverage={cov_num}/{cov_den} novel={novel} cross={cross}")


if __name__ == "__main__":
    main()
