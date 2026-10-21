// Team Profile (Figma "Screen / Team Profile", 29:254). Owner: Stream B (layout from the design by Stream E).
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTeam } from "@/api/hooks";
import type { InsightMode, RoleName, RoundType, TrendPoint } from "@/api/types";
import { MapIcon } from "@/components/ui/AgentIcon";
import { Badge, type Tone } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InsightList } from "@/components/ui/InsightList";
import { InsightModeBar } from "@/components/ui/InsightModeBar";
import { Meter } from "@/components/ui/Meter";
import { Panel } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { ROLE_PT, ROUND_TYPE_PT, dateShort, int, num, pct } from "@/lib/format";

const mono = "font-mono font-medium";
const ROLE_TONE: Record<RoleName, Tone> = { entry: "red", support: "cyan", anchor: "violet", lurker: "amber", flex: "neutral", igl: "green" };
const RT: RoundType[] = ["pistol", "eco", "semi_eco", "force", "full_buy"];

/** "Rush Series Esquenta", "Rush Series Esquenta 2" -> "Rush Esquenta, Esquenta 2 e Inclusivo" */
function tournamentsText(names: string[]): string {
  const uniq = [...new Set(names.map((n) => n.replace("Series ", "")))].sort();
  const first = uniq[0]?.split(" ")[0];
  const parts = uniq.map((n, i) => (i > 0 && n.split(" ")[0] === first ? n.split(" ").slice(1).join(" ") : n));
  return parts.length > 1 ? `${parts.slice(0, -1).join(", ")} e ${parts[parts.length - 1]}` : parts[0] ?? "";
}

/** Round difference per match, oldest to newest (last 12): green = won the map, red = lost. */
function TrendChart({ points }: { points: TrendPoint[] }) {
  const pts = points.slice(-12);
  const w = 518, h = 230, zero = 125, unit = 95 / 13, bw = 26, step = pts.length > 1 ? (w - bw - 12) / (pts.length - 1) : 0;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Diferença de rounds por partida">
      <line x1="0" x2={w} y1={zero} y2={zero} stroke="var(--color-border-strong)" />
      {pts.map((p, i) => {
        const x = 6 + i * step;
        const bh = Math.max(Math.min(Math.abs(p.round_diff), 13) * unit, 2);
        const up = p.round_diff >= 0;
        return (
          <g key={p.match_id}>
            <rect x={x} width={bw} y={up ? zero - bh : zero} height={bh} fill={up ? "var(--color-green)" : "var(--color-accent)"}>
              <title>{`${dateShort(p.date)} · ${p.map_name ?? ""}: ${p.round_diff > 0 ? "+" : ""}${p.round_diff} rounds`}</title>
            </rect>
            <text x={x + bw / 2} y={up ? zero - bh - 6 : zero + bh + 14} textAnchor="middle" fontSize="11" fontFamily="var(--font-mono)" fill={up ? "var(--color-green)" : "var(--color-accent)"}>
              {p.round_diff > 0 ? "+" : ""}{p.round_diff}
            </text>
            <text x={x + bw / 2} y={220} textAnchor="middle" fontSize="11" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)">
              {(p.map_name ?? "").slice(0, 3).toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function TeamPage() {
  const { teamName = "" } = useParams();
  const navigate = useNavigate();
  const [mode, setMode] = useState<InsightMode>("rules");
  const { data: t, isLoading, isFetching, error } = useTeam(teamName, mode);

  if (isLoading) return <p className="text-fg-muted">Carregando…</p>;
  if (error || !t) return <EmptyState title="Time não encontrado" message="Não há dados deste time para os filtros atuais." />;

  const { record: r, economy: e } = t;
  const initials = t.team.name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
  const roundsWon = Math.round((r.round_win_rate.value ?? 0) * r.round_win_rate.sample_size);
  const pistolWon = Math.round((e.pistol_win_rate.value ?? 0) * e.pistol_win_rate.sample_size);
  const site = Object.entries(e.plant_site_preference).sort((a, b) => (b[1].value ?? 0) - (a[1].value ?? 0))[0];

  return (
    <>
      <p className="text-xs leading-4 text-fg-muted">
        <Link to="/times" className="hover:text-fg">Times</Link> › {t.team.name}
      </p>

      <div className="flex items-center gap-5 rounded-md border border-border bg-surface px-6 py-5">
        <div className="flex size-[72px] shrink-0 items-center justify-center rounded-sm border border-border-strong bg-surface-raised font-display text-[32px] font-bold leading-10 text-accent">{initials}</div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 className="truncate font-display text-[32px] font-bold leading-10 text-fg">{t.team.name}</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm leading-5">
            <Badge tone="green">{r.wins} V · {r.losses} D</Badge>
            <span className="text-fg-secondary">{r.matches} partidas · {tournamentsText(t.matches.map((m) => m.tournament))}</span>
          </div>
        </div>
        <Link to={`/plano?teamA=${encodeURIComponent(t.team.name)}`} className="shrink-0 font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">
          Comparar com outro time →
        </Link>
      </div>

      <div className="flex gap-4">
        <StatCard label="Partidas" value={String(r.matches)} footnote={`${t.by_map.length} mapas diferentes`} />
        <StatCard label="% Rounds vencidos" value={pct(r.round_win_rate.value)} lowSample={r.round_win_rate.low_sample} footnote={`${int(roundsWon)} de ${int(r.round_win_rate.sample_size)} rounds`} />
        <StatCard label="Ataque" value={pct(r.attack_win_rate.value)} lowSample={r.attack_win_rate.low_sample} footnote="rounds como atacante" />
        <StatCard label="Defesa" value={pct(r.defense_win_rate.value)} lowSample={r.defense_win_rate.low_sample} footnote="rounds como defensor" />
        <StatCard label="Pistol rounds" value={pct(e.pistol_win_rate.value)} lowSample={e.pistol_win_rate.low_sample} footnote={`${pistolWon} de ${e.pistol_win_rate.sample_size} vencidos`} />
        <StatCard label={site ? `Plante no site ${site[0]}` : "Plante"} value={site ? pct(site[1].value) : "—"} lowSample={site?.[1].low_sample} footnote="dos plantes realizados" />
      </div>

      <div className="flex items-start gap-4">
        <Panel className="flex-1" title="Elenco" subtitle="Função comportamental de cada jogador">
          <DataTable
            rows={t.roster.slice(0, 8)}
            rowKey={(m) => m.player.puuid}
            columns={[
              { key: "p", header: "Jogador", width: 210, className: "font-semibold text-fg", render: (m) => <Link className="truncate hover:text-accent" to={`/jogador/${m.player.puuid}`}>{m.player.riot_id}</Link> },
              { key: "f", header: "Função", width: 110, render: (m) => (m.top_role ? <Badge tone={ROLE_TONE[m.top_role.role]}>{ROLE_PT[m.top_role.role].split(" ")[0]}</Badge> : "—") },
              { key: "m", header: "Mapas", width: 50, align: "right", className: mono, render: (m) => m.matches },
              { key: "kd", header: "K/D", width: 50, align: "right", className: `${mono} text-green`, render: (m) => num(m.kd) },
              { key: "adr", header: "ADR", width: 50, align: "right", className: mono, render: (m) => num(m.adr, 0) },
            ]}
          />
        </Panel>
        <Panel className="flex-1" title="Desempenho por partida" subtitle="Diferença de rounds (positivo = vitória)">
          <TrendChart points={t.trend} />
        </Panel>
      </div>

      <div className="flex items-start gap-4">
        <Panel className="flex-[690]" title="Desempenho por mapa" subtitle="Rounds vencidos por lado">
          <DataTable
            rows={t.by_map}
            rowKey={(m) => m.map.codename}
            columns={[
              { key: "m", header: "Mapa", className: "font-semibold text-fg", render: (m) => <Link className="inline-flex items-center hover:text-accent" to={`/mapa/${m.map.name}`}><MapIcon map={m.map} showName /></Link> },
              { key: "vd", header: "V–D", width: 56, align: "right", className: mono, render: (m) => {
                const w = Math.round((m.win_rate.value ?? 0) * m.matches);
                return `${w}–${m.matches - w}`;
              } },
              { key: "a", header: "Ataque", width: 150, render: (m) => <Meter width={106} color="bg-accent" value={m.attack_win_rate.value} label={pct(m.attack_win_rate.value)} /> },
              { key: "d", header: "Defesa", width: 150, render: (m) => <Meter width={106} color="bg-violet" value={m.defense_win_rate.value} label={pct(m.defense_win_rate.value)} /> },
            ]}
          />
        </Panel>
        <Panel className="flex-[430]" title="Economia" subtitle="Rounds por tipo de compra">
          <DataTable
            rows={RT}
            rowKey={(x) => x}
            columns={[
              { key: "t", header: "Tipo", className: "font-semibold text-fg", render: (x) => ROUND_TYPE_PT[x] },
              { key: "n", header: "Rounds", width: 60, align: "right", className: mono, render: (x) => e.win_rate_by_round_type[x].sample_size },
              { key: "w", header: "Vitórias", width: 140, render: (x) => <Meter width={96} color="bg-amber" value={e.win_rate_by_round_type[x].value} label={pct(e.win_rate_by_round_type[x].value)} /> },
            ]}
          />
        </Panel>
      </div>

      <Panel title="Todas as partidas" subtitle="Clique para abrir o relatório">
        <DataTable
          rows={t.matches}
          rowKey={(m) => m.match_id}
          onRowClick={(m) => navigate(`/partida/${m.match_id}`)}
          columns={[
            { key: "d", header: "Data", width: 90, className: `${mono} text-fg-muted`, render: (m) => dateShort(m.date) },
            { key: "o", header: "Adversário", className: "font-semibold text-fg", render: (m) => (m.team_a.team.name === t.team.name ? m.team_b.team.name : m.team_a.team.name) },
            { key: "m", header: "Mapa", width: 130, render: (m) => <MapIcon map={m.map} showName /> },
            { key: "s", header: "Placar", width: 90, align: "center", className: `${mono} text-fg`, render: (m) => (m.team_a.team.name === t.team.name ? `${m.team_a.score} × ${m.team_b.score}` : `${m.team_b.score} × ${m.team_a.score}`) },
            { key: "r", header: "Resultado", width: 100, render: (m) => {
              const win = m.winner === (m.team_a.team.name === t.team.name ? "a" : "b");
              return <Badge tone={win ? "green" : "red"}>{win ? "Vitória" : "Derrota"}</Badge>;
            } },
            { key: "v", header: "", width: 120, align: "right", className: "text-accent", render: () => "Ver relatório →" },
          ]}
        />
      </Panel>

      <InsightModeBar mode={mode} onChange={setMode} loading={isFetching && mode === "llm" && t.insights_source !== "llm"} source={t.insights_source} />
      <div className="grid grid-cols-3 gap-4">
        <Panel title="Pontos fortes"><InsightList insights={t.insights} kinds={["strength"]} /></Panel>
        <Panel title="Pontos fracos"><InsightList insights={t.insights} kinds={["weakness"]} /></Panel>
        <Panel title="Sugestões de melhoria"><InsightList insights={t.insights} kinds={["tip", "strategy"]} /></Panel>
      </div>
    </>
  );
}
