// Player Profile (Figma "Screen / Player Profile", 27:155). Owner: Stream B (layout from the design by Stream E).
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMeta, usePlayer } from "@/api/hooks";
import type { InsightMode, PlayerProfile, RoleName, RoleScore } from "@/api/types";
import { AgentIcon, MapIcon, WeaponIcon } from "@/components/ui/AgentIcon";
import { Badge, type Tone } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InsightList } from "@/components/ui/InsightList";
import { InsightModeBar } from "@/components/ui/InsightModeBar";
import { Meter } from "@/components/ui/Meter";
import { Panel } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { useFilters } from "@/lib/filters";
import { ROLE_PT, int, num, pct } from "@/lib/format";
import { tournamentOptions } from "@/lib/tournaments";

const mono = "font-mono font-medium";
const ROLE_BAR: Record<RoleName, string> = {
  entry: "bg-accent", flex: "bg-amber", support: "bg-cyan", lurker: "bg-violet", anchor: "bg-blue", igl: "bg-fg-muted",
};
const ROLE_TONE: Tone[] = ["red", "amber", "cyan"];

/** Text that backs a role score, built only from the signals the API returns. */
function roleEvidence(r: RoleScore, p: PlayerProfile): string {
  const s = Object.fromEntries(r.signals.map((x) => [x.name, x.value]));
  const parts: string[] = [];
  if (r.role === "entry") {
    if (s.first_duel_share != null) parts.push(`1º duelo em ${pct(s.first_duel_share)} dos rounds`);
    if (s.early_kill_share != null) parts.push(`${pct(s.early_kill_share)} dos abates nos primeiros 30 s`);
  } else if (r.role === "flex") {
    parts.push(`${p.agents.length} agentes em ${p.stats.matches} mapas`);
  } else if (r.role === "support") {
    if (s.assists_per_round != null) parts.push(`${num(s.assists_per_round)} assist./round`);
    if (s.casts_per_round != null) parts.push(`${num(s.casts_per_round, 1)} habilidades/round`);
  } else if (r.role === "lurker") {
    if (s.isolation != null) parts.push(`isolamento ${num(s.isolation)}× o do time`);
    if (s.late_kill_share != null) parts.push(`${pct(s.late_kill_share)} dos abates após 60 s`);
  } else if (r.role === "anchor") {
    if (s.defense_site_presence != null) parts.push(`${pct(s.defense_site_presence)} das posições na defesa dentro de um site`);
  }
  return parts.join(" · ") || "sem sinais suficientes";
}

export default function PlayerPage() {
  const { puuid = "" } = useParams();
  const [mode, setMode] = useState<InsightMode>("rules");
  const { data: p, isLoading, isFetching, error } = usePlayer(puuid, mode);
  const { data: meta } = useMeta();
  const { filters } = useFilters();

  if (isLoading) return <p className="text-fg-muted">Carregando…</p>;
  if (error || !p) return <EmptyState title="Jogador não encontrado" message="Não há dados deste jogador para os filtros atuais." />;

  const { stats } = p;
  const initials = p.player.riot_id.replace(/[^\p{L}\p{N}]/gu, "").slice(0, 2).toUpperCase() || "?";
  const fav = p.agents[0];
  const favShare = fav ? fav.matches / Math.max(stats.matches, 1) : 0;
  const team = p.teams[0];
  const weapons = p.weapons.filter((w) => w.buy_type == null);
  const tName = tournamentOptions(meta).find((o) => o.value === (filters.tournament ?? ""))?.label;
  const roles = [...p.roles, ...(p.roles.some((r) => r.role === "igl") ? [] : [{ role: "igl" as const, score: 0, confidence: 0, inferred: true, signals: [] }])];
  const topMap = [...p.by_map].sort((a, b) => b.matches - a.matches)[0];

  return (
    <>
      <p className="text-xs leading-4 text-fg-muted">
        <Link to="/jogadores" className="hover:text-fg">Jogadores</Link> › {p.player.riot_id}
      </p>

      <div className="flex items-center gap-5 rounded-md border border-border bg-surface px-6 py-5">
        <div className="flex size-[72px] shrink-0 items-center justify-center rounded-sm border border-border-strong bg-surface-raised font-display text-[32px] font-bold leading-10 text-accent">{initials}</div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 className="truncate font-display text-[32px] font-bold leading-10 text-fg">{p.player.riot_id}</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm leading-5">
            {team && <Link to={`/time/${encodeURIComponent(team.name)}`}><Badge tone="neutral">{team.name}</Badge></Link>}
            {fav && (
              <span className="inline-flex items-center gap-2 text-fg-secondary">
                <AgentIcon agent={fav.agent} size={24} />
                Agente favorito: {fav.agent.name ?? "Agente desconhecido"} ({pct(favShare)} das partidas)
              </span>
            )}
            <span className="text-fg-muted">{stats.matches} mapas · {int(stats.rounds)} rounds</span>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className="font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] text-fg-muted">Função no time</span>
          <div className="flex gap-2">
            {p.roles.slice(0, 2).map((r, i) => <Badge key={r.role} tone={ROLE_TONE[i]}>{ROLE_PT[r.role]} · {pct(r.score)}</Badge>)}
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <StatCard label="K/D" value={num(stats.kd.value)} lowSample={stats.kd.low_sample} footnote={`${int(stats.kills)} abates · ${int(stats.deaths)} mortes`} />
        <StatCard label="% Headshot" value={pct(stats.hs_pct.value)} footnote={`de ${int(stats.shots)} acertos`} />
        <StatCard label="ADR" value={num(stats.adr.value, 0)} footnote="dano médio por round" />
        <StatCard label="Abertura de round" value={pct(stats.opening_duel_win_pct.value)} footnote="duelos iniciais vencidos" />
        <StatCard label="Rounds jogados" value={int(stats.rounds)} footnote={`em ${stats.matches} mapas`} />
        <StatCard label="Assistências" value={num(stats.assists / Math.max(stats.rounds, 1))} footnote="por round" />
      </div>

      <div className="flex items-stretch gap-4">
        <Panel className="flex-1" title="Classificação por função" subtitle="Heurísticas comportamentais calculadas a partir dos dados">
          <DataTable
            rows={roles}
            rowKey={(r) => r.role}
            columns={[
              { key: "f", header: "Função", width: 130, className: "font-semibold text-fg", render: (r) => ROLE_PT[r.role] },
              { key: "s", header: "Pontuação", width: 190, render: (r) => <Meter width={146} value={r.score} color={ROLE_BAR[r.role]} label={pct(r.role === "igl" ? 0 : r.score)} /> },
              { key: "e", header: "Sinais que sustentam", render: (r) => (r.role === "igl" ? "não inferido com confiança (dados insuficientes)" : roleEvidence(r, p)) },
            ]}
          />
          <div className="rounded-sm border border-border bg-surface-raised p-4">
            <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">Como calculamos</p>
            <p className="mt-2 text-sm leading-5 text-fg-secondary">
              A função é inferida pelo comportamento em rounds reais: primeiro duelo, tempo de entrada, distância ao time, assistências, uso de habilidades e presença em sites na defesa. Não depende apenas do agente escolhido.
            </p>
            <p className="mt-2 text-xs leading-4 text-fg-muted">IGL não é identificável com os dados disponíveis e só aparece quando há evidência suficiente.</p>
          </div>
        </Panel>

        <div className="flex w-[330px] shrink-0 flex-col gap-4">
          <Panel title="Abertura de rounds" subtitle="Primeiro duelo de cada round">
            <div className="flex items-end gap-2">
              <span className="font-display text-[56px] font-bold leading-[56px] text-green">{pct(stats.opening_duel_win_pct.value)}</span>
              <span className="pb-1 text-xs text-fg-muted">de vitórias na abertura</span>
            </div>
            <div className="flex flex-col">
              {[
                ["Primeiros abates", stats.first_kills],
                ["Primeiras mortes", stats.first_deaths],
                ["Trocas recebidas", stats.traded_deaths],
                ["Clutches (1vX)", stats.clutches],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between border-b border-border py-3 text-sm">
                  <span className="text-fg-secondary">{l}</span>
                  <span className={`${mono} text-fg`}>{v}</span>
                </div>
              ))}
            </div>
          </Panel>
          <Panel className="flex-1" title="Agentes jogados" subtitle={fav ? `Favorito: ${fav.agent.name ?? "Agente desconhecido"}` : undefined}>
            <DataTable
              rows={p.agents.slice(0, 4)}
              rowKey={(a) => a.agent.id}
              columns={[
                { key: "a", header: "Agente", width: 126, className: "font-semibold text-fg", render: (a) => <AgentIcon agent={a.agent} size={24} showName /> },
                { key: "m", header: "Partidas", render: (a) => <Meter width={96} value={a.matches / Math.max(stats.matches, 1)} label={pct(a.matches / Math.max(stats.matches, 1))} /> },
              ]}
            />
            <p className="text-[11px] leading-[14px] text-fg-muted">
              K/D por agente: {p.agents.slice(0, 4).map((a) => `${a.agent.name ?? "Desconhecido"} ${num(a.kd.value)}`).join(" · ")}
            </p>
          </Panel>
        </div>
      </div>

      <div className="flex items-start gap-4">
        <Panel className="flex-[690]" title="Desempenho por arma comprada" subtitle="Rounds em que a arma foi comprada (eco, force e full buy)">
          <DataTable
            rows={weapons}
            rowKey={(w) => w.weapon.id}
            emptyText="Poucos rounds por arma para exibir."
            columns={[
              { key: "w", header: "Arma", className: "font-semibold text-fg", render: (w) => <WeaponIcon weapon={w.weapon} showName /> },
              { key: "r", header: "Rounds", width: 64, align: "right", className: mono, render: (w) => w.rounds },
              { key: "v", header: "Vitórias", width: 90, render: (w) => <Meter width={46} color="bg-green" value={w.round_win_rate.value} label={pct(w.round_win_rate.value)} /> },
              { key: "k", header: "Abates", width: 64, align: "right", className: mono, render: (w) => w.kills },
              { key: "kd", header: "K/D", width: 56, align: "right", className: mono, render: (w) => num(w.kd.value) },
              { key: "h", header: "HS%", width: 56, align: "right", className: mono, render: (w) => pct(w.hs_pct.value) },
            ]}
          />
        </Panel>
        <Panel className="flex-[430]" title="Abates e mortes por mapa" subtitle={tName && tName !== "Todos" ? tName : "Todos os torneios"}>
          <DataTable
            rows={p.by_map}
            rowKey={(m) => m.map.codename}
            columns={[
              { key: "m", header: "Mapa", className: "font-semibold text-fg", render: (m) => <Link className="inline-flex items-center hover:text-accent" to={`/mapa/${m.map.name}`}><MapIcon map={m.map} showName /></Link> },
              { key: "k", header: "Abates", width: 60, align: "right", className: `${mono} text-green`, render: (m) => m.kills },
              { key: "d", header: "Mortes", width: 60, align: "right", className: `${mono} text-accent`, render: (m) => m.deaths },
              { key: "kd", header: "K/D", width: 56, align: "right", className: mono, render: (m) => num(m.kd.value) },
            ]}
          />
          {topMap && (
            <Link to={`/mapa/${topMap.map.name}`} className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">
              Ver abates e mortes no mapa →
            </Link>
          )}
        </Panel>
      </div>

      <InsightModeBar mode={mode} onChange={setMode} loading={isFetching && mode === "llm" && p.insights_source !== "llm"} source={p.insights_source} />
      <div className="grid grid-cols-3 gap-4">
        <Panel title="Pontos fortes"><InsightList insights={p.insights} kinds={["strength"]} /></Panel>
        <Panel title="Pontos fracos"><InsightList insights={p.insights} kinds={["weakness"]} /></Panel>
        <Panel title="Recomendações de treino"><InsightList insights={p.insights} kinds={["tip"]} /></Panel>
      </div>
    </>
  );
}
