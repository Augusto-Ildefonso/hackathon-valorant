// Match Report (Figma "Screen / Match Report", 31:360). Owner: Stream C (layout from the design by Stream E).
// Data: /api/matches/{id} and /api/matches/{id}/kills (stubs return fixtures until Stream C ships them).
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMatch, useMatchKills } from "@/api/hooks";
import type { InsightMode, KillEvent, MatchReport, RoundSummary } from "@/api/types";
import { MinimapCanvas } from "@/components/map/MinimapCanvas";
import { AgentIcon, WeaponIcon } from "@/components/ui/AgentIcon";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { InsightList } from "@/components/ui/InsightList";
import { InsightModeBar } from "@/components/ui/InsightModeBar";
import { Panel } from "@/components/ui/Panel";
import { dateBR, num, pct } from "@/lib/format";
import { tournamentLabel } from "@/lib/tournaments";

const mono = "font-mono font-medium";
const TEAM = { a: { text: "text-cyan", bg: "bg-cyan" }, b: { text: "text-amber", bg: "bg-amber" } } as const;
const RESULT_LETTER: Record<RoundSummary["result"], string> = { eliminated: "E", detonated: "P", defused: "D", timer: "T" };
const RESULT_PT: Record<RoundSummary["result"], string> = { eliminated: "eliminação", detonated: "detonação", defused: "desarme", timer: "tempo esgotado" };
const clock = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
const first = (name: string) => name.split(" ")[0].toUpperCase();

function Scoreboard({ r, side }: { r: MatchReport; side: "a" | "b" }) {
  const team = side === "a" ? r.team_a : r.team_b;
  const rows = r.scoreboard.filter((p) => p.team === side).sort((x, y) => y.kills - x.kills);
  return (
    <Panel className="flex-1" title={team.team.name} subtitle={`Placar da equipe · ${team.score} rounds vencidos`}>
      <DataTable
        rows={rows}
        rowKey={(p) => p.player.puuid}
        columns={[
          { key: "p", header: "Jogador", width: 120, className: "font-semibold text-fg", render: (p) => (
            <Link to={`/jogador/${p.player.puuid}`} className={`truncate hover:text-accent ${r.mvp?.puuid === p.player.puuid ? "text-amber" : ""}`}>
              {p.player.riot_id}{r.mvp?.puuid === p.player.puuid && <span className="ml-1">★ MVP</span>}
            </Link>
          ) },
          { key: "a", header: "Agente", width: 106, render: (p) => <AgentIcon agent={p.agent} size={24} showName /> },
          { key: "k", header: "K", width: 30, align: "right", className: `${mono} text-fg`, render: (p) => p.kills },
          { key: "d", header: "D", width: 30, align: "right", className: mono, render: (p) => p.deaths },
          { key: "as", header: "A", width: 30, align: "right", className: mono, render: (p) => p.assists },
          { key: "adr", header: "ADR", width: 44, align: "right", className: mono, render: (p) => num(p.adr.value, 0) },
          { key: "hs", header: "HS%", width: 44, align: "right", className: mono, render: (p) => pct(p.hs_pct.value) },
          { key: "fk", header: "FK", width: 30, align: "right", className: mono, render: (p) => p.first_kills },
        ]}
      />
    </Panel>
  );
}

function Timeline({ r, selected, onSelect }: { r: MatchReport; selected: number; onSelect: (n: number) => void }) {
  const halves: Array<[RoundSummary["half"], string]> = [[1, "1º tempo"], [2, "2º tempo"], ["ot", "Prorrogação"]];
  return (
    <Panel
      title="Linha do tempo dos rounds"
      subtitle="Cada bloco mostra quem venceu o round e como terminou"
      aside={
        <div className="flex items-center gap-4 text-[11px] text-fg-secondary">
          <span><span className="mr-1 inline-block size-[10px] rounded-[2px] bg-cyan" />{r.team_a.team.name}</span>
          <span><span className="mr-1 inline-block size-[10px] rounded-[2px] bg-amber" />{r.team_b.team.name}</span>
          <span className="text-fg-muted">E elim. · P detonação · D desarme · T tempo</span>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        {halves.map(([h, label]) => {
          const rounds = r.rounds.filter((x) => x.half === h);
          if (!rounds.length) return null;
          const attacker = rounds[0].team_a_side === "attack" ? r.team_a.team.name : r.team_b.team.name;
          return (
            <div key={String(h)}>
              <p className="mb-2 font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">
                {label}{h !== "ot" && ` · ${first(attacker)} ataca`}
              </p>
              <div className="flex flex-wrap">
                {rounds.map((x) => {
                  const t = TEAM[x.winner];
                  return (
                    <button
                      key={x.number}
                      onClick={() => onSelect(x.number)}
                      title={`Round ${x.number}: ${RESULT_PT[x.result]}${x.ceremony ? ` · ${x.ceremony.replace("Ceremony", "")}` : ""}`}
                      className={`flex h-[66px] w-14 flex-col items-center gap-1 border pt-[9px] ${selected === x.number ? "border-accent bg-surface-accent" : "border-border bg-surface-raised/40 hover:border-border-strong"}`}
                    >
                      <span className="text-[11px] leading-[14px] text-fg-muted">{x.number}</span>
                      <span className={`mt-[6px] h-[6px] w-10 rounded-[1px] ${t.bg}`} />
                      <span className={`font-display text-base font-semibold ${t.text}`}>{RESULT_LETTER[x.result]}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function roundSummary(r: MatchReport, round: RoundSummary, kills: KillEvent[]): { headline: string; detail: string } {
  const win = round.winner === "a" ? r.team_a.team.name : r.team_b.team.name;
  const attackerSide = round.team_a_side === "attack" ? "a" : "b";
  const attackers = 5;
  const lostAttackers = kills.filter((k) => k.victim.team === attackerSide).length;
  const econ = round.economy;
  const label = (t: string) => t.replace("_", " ");
  return {
    headline: `${win} venceu por ${RESULT_PT[round.result]}${round.plant_site ? `: plante no site ${round.plant_site}` : ""}${round.defused ? ", desarmado pela defesa" : ""}.`,
    detail: [
      `${kills.filter((k) => k.killer.puuid !== k.victim.puuid).length} abates`, // spike deaths are not kills
      kills.length ? `${attackers - lostAttackers} de ${attackers} atacantes sobreviveram` : null,
      `economia: ${label(econ.team_a_type)} (${r.team_a.team.name}) contra ${label(econ.team_b_type)} (${r.team_b.team.name})`,
    ].filter(Boolean).join(" · "),
  };
}

function Replay({ r, round, setRound }: { r: MatchReport; round: number; setRound: (n: number) => void }) {
  const { data } = useMatchKills(r.match_id, { round });
  const [sel, setSel] = useState(0);
  useEffect(() => setSel(0), [round, data]);
  const kills = (data?.kills ?? []).slice().sort((a, b) => a.time_ms - b.time_ms);
  const kill = kills[sel];
  const roundInfo = r.rounds.find((x) => x.number === round);
  const total = r.rounds.length;
  const start = Math.max(1, Math.min(round - 2, total - 4));
  const chips = Array.from({ length: Math.min(5, total) }, (_, i) => start + i);
  const summary = roundInfo ? roundSummary(r, roundInfo, kills) : null;

  return (
    <Panel
      title="Replay de abates"
      subtitle={`Round ${round} · selecione um abate para ver killer, vítima e trajetória`}
      aside={<div className="flex gap-2">{chips.map((n) => <FilterChip key={n} on={n === round} onClick={() => setRound(n)}>R{n}</FilterChip>)}</div>}
    >
      <div className="flex items-start gap-5">
        <div className="flex shrink-0 flex-col gap-2">
          {data && (
            <MinimapCanvas
              map={r.map}
              size={560}
              lines={kill && kill.killer.pos && kill.victim.pos ? [{ from: kill.killer.pos, to: kill.victim.pos, dashed: true, color: "#f1eee8" }] : []}
              points={kill ? [
                ...kill.others_alive.filter((p) => p.pos).map((p) => ({ point: p.pos!, kind: "player" as const, team: p.team, viewRadians: p.view_radians })),
                ...(kill.killer.pos ? [{ point: kill.killer.pos, kind: "kill" as const, team: kill.killer.team, label: `${kill.killer.riot_id} · ${kill.weapon?.name ?? "—"}`, viewRadians: kill.killer.view_radians }] : []),
                ...(kill.victim.pos ? [{ point: kill.victim.pos, kind: "death" as const, label: kill.victim.riot_id }] : []),
              ] : []}
            />
          )}
          <div className="flex gap-4 text-[11px] text-fg-secondary">
            <span><span className="mr-1 inline-block size-2 rounded-full bg-cyan" />{r.team_a.team.name}</span>
            <span><span className="mr-1 inline-block size-2 rounded-full bg-amber" />{r.team_b.team.name}</span>
            <span><span className="mr-1 inline-block size-2 rounded-full bg-accent" />Vítima</span>
            <span className="text-fg-muted">Cones = direção de visão</span>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">Abates do round {round}</p>
          {kills.length === 0 && <p className="text-sm text-fg-muted">Nenhum abate registrado neste round.</p>}
          {kills.map((k, i) => (
            <button
              key={k.id}
              onClick={() => setSel(i)}
              className={`flex h-[60px] items-center gap-4 rounded-sm border px-3 text-left ${i === sel ? "border-accent bg-tint-red" : "border-border bg-surface-raised/50 hover:border-border-strong"}`}
            >
              <span className={`${mono} w-9 text-sm text-fg-muted`}>{clock(k.time_ms)}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">
                  <span className={TEAM[k.killer.team].text}>{k.killer.riot_id}</span>
                  <span className="mx-2 text-fg-secondary">→</span>
                  <span className={TEAM[k.victim.team].text}>{k.victim.riot_id}</span>
                </span>
                <span className="flex items-center gap-[6px] text-[11px] text-fg-muted">
                  {k.damage_type === "weapon" && <WeaponIcon weapon={k.weapon} size={16} />}
                  {k.weapon?.name ?? (k.damage_type === "weapon" ? "Arma desconhecida" : k.damage_type)}
                  {k.damage_type === "ability" && " · habilidade"}{k.damage_type === "bomb" && " · spike"}
                </span>
              </span>
              {i === 0 && <span className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">First blood</span>}
            </button>
          ))}
          {kills.length > 0 && <p className="text-xs text-fg-muted">Selecionado: killer (anel branco) → vítima (✕). Os cones mostram para onde cada jogador vivo olhava no momento do abate.</p>}
          {summary && (
            <div className="mt-2 rounded-sm border border-border bg-surface-raised p-4">
              <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">Resumo do round {round}</p>
              <p className="mt-2 text-sm leading-5 text-fg">{summary.headline}</p>
              <p className="mt-2 text-xs leading-4 text-fg-muted">{summary.detail}</p>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}

export default function MatchPage() {
  const { matchId = "" } = useParams();
  const [mode, setMode] = useState<InsightMode>("rules");
  const { data: r, isLoading, isFetching, error } = useMatch(matchId, mode);
  const [round, setRound] = useState(1);
  useEffect(() => setRound(1), [matchId]);

  if (isLoading) return <p className="text-fg-muted">Carregando…</p>;
  if (error || !r) return <EmptyState title="Partida não encontrada" message="Não há dados desta partida." />;
  const aWon = r.winner === "a";

  return (
    <>
      <p className="text-xs leading-4 text-fg-muted">
        <Link to="/partidas" className="hover:text-fg">Partidas</Link> › {r.team_a.team.name} × {r.team_b.team.name}
      </p>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-6 rounded-md border border-border bg-surface px-8 py-6">
        <div className="flex flex-col items-end gap-1">
          <Link to={`/time/${encodeURIComponent(r.team_a.team.name)}`} className="font-display text-[32px] font-bold leading-10 text-fg hover:text-accent">{r.team_a.team.name}</Link>
          <Badge tone={aWon ? "cyan" : "amber"}>{aWon ? "Vencedor" : "Derrota"}</Badge>
        </div>
        <div className="flex flex-col items-center gap-1">
          <div className="flex items-center gap-4 font-display text-[48px] font-bold leading-[56px]">
            <span className="text-cyan">{r.team_a.score}</span>
            <span className="text-[28px] text-fg-muted">×</span>
            <span className="text-amber">{r.team_b.score}</span>
          </div>
          <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">
            {r.map.name} · {Math.round(r.duration_ms / 60000)} min · {dateBR(r.date)} · {tournamentLabel(r.tournament, r.phase)}
          </p>
        </div>
        <div className="flex flex-col items-start gap-1">
          <Link to={`/time/${encodeURIComponent(r.team_b.team.name)}`} className="font-display text-[32px] font-bold leading-10 text-fg hover:text-accent">{r.team_b.team.name}</Link>
          <Badge tone={aWon ? "amber" : "cyan"}>{aWon ? "Derrota" : "Vencedor"}</Badge>
        </div>
      </div>

      <div className="flex items-start gap-4">
        <Scoreboard r={r} side="a" />
        <Scoreboard r={r} side="b" />
      </div>

      <Timeline
        r={r}
        selected={round}
        onSelect={(n) => {  // choosing a round in the timeline brings its kill replay into view
          setRound(n);
          requestAnimationFrame(() => document.getElementById("partida-replay")?.scrollIntoView({ behavior: "smooth", block: "start" }));
        }}
      />
      <div id="partida-replay" className="scroll-mt-20">
        <Replay r={r} round={round} setRound={setRound} />
      </div>

      <InsightModeBar mode={mode} onChange={setMode} loading={isFetching && mode === "llm" && r.insights_source !== "llm"} source={r.insights_source} />
      <div className="flex items-start gap-4">
        <Panel className="flex-1" title={r.team_a.team.name} subtitle="Melhorias sugeridas com base nesta partida"><InsightList insights={r.insights_a} /></Panel>
        <Panel className="flex-1" title={r.team_b.team.name} subtitle="Melhorias sugeridas com base nesta partida"><InsightList insights={r.insights_b} /></Panel>
      </div>
    </>
  );
}
