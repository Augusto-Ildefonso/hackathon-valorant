// Figma "Panel / Top jogadores" and "Panel / Top times" (Home). Owner: Stream E.
import { useState } from "react";
import { Link } from "react-router-dom";
import { useLeaderboards } from "@/api/hooks";
import type { PlayerLeaderRow } from "@/api/types";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { FilterChip } from "@/components/ui/FilterChip";
import { Panel } from "@/components/ui/Panel";
import { num, pct } from "@/lib/format";

type Metric = "kd" | "adr" | "hs_pct" | "first_kills";
const METRICS: Array<{ id: Metric; label: string }> = [
  { id: "kd", label: "K/D" },
  { id: "adr", label: "ADR" },
  { id: "hs_pct", label: "HS%" },
  { id: "first_kills", label: "First kills" },
];
const mono = "font-mono font-medium";

export function TopPlayersPanel({ limit = 5, title = "Top jogadores" }: { limit?: number; title?: string }) {
  const [metric, setMetric] = useState<Metric>("kd");
  const { data, isLoading } = useLeaderboards();
  const rows = (data?.players[metric] ?? []).slice(0, limit);
  const hi = (m: Metric) => (metric === m ? `${mono} text-green` : mono);
  const cols: Column<PlayerLeaderRow>[] = [
    { key: "#", header: "#", width: 32, className: `${mono} text-fg-muted`, render: (r) => r.rank },
    { key: "p", header: "Jogador", className: "font-semibold text-fg", render: (r) => <Link className="hover:text-accent" to={`/jogador/${r.player.puuid}`}>{r.player.riot_id}</Link> },
    { key: "t", header: "Time", width: 170, render: (r) => (r.team ? <Link className="truncate hover:text-fg" to={`/time/${encodeURIComponent(r.team.name)}`}>{r.team.name}</Link> : "—") },
    { key: "m", header: "Mapas", width: 60, align: "right", className: mono, render: (r) => r.matches },
    { key: "kd", header: "K/D", width: 60, align: "right", className: hi("kd"), render: (r) => num(r.kd) },
    { key: "adr", header: "ADR", width: 60, align: "right", className: hi("adr"), render: (r) => num(r.adr, 0) },
    { key: "hs", header: "HS%", width: 60, align: "right", className: hi("hs_pct"), render: (r) => pct(r.hs_pct) },
    ...(metric === "first_kills"
      ? [{ key: "fk", header: "FK", width: 50, align: "right" as const, className: hi("first_kills"), render: (r: PlayerLeaderRow) => r.first_kills }]
      : []),
  ];
  return (
    <Panel
      className="flex-1"
      title={title}
      subtitle={`Mínimo de 5 mapas · ordenado por ${METRICS.find((m) => m.id === metric)?.label}`}
      aside={
        <div className="flex gap-2">
          {METRICS.map((m) => (
            <FilterChip key={m.id} on={metric === m.id} onClick={() => setMetric(m.id)}>{m.label}</FilterChip>
          ))}
        </div>
      }
    >
      {isLoading ? <p className="text-fg-muted">Carregando…</p> : (
        <DataTable rows={rows} rowKey={(r) => r.player.puuid} columns={cols} emptyText="Sem jogadores com 5 mapas neste filtro." />
      )}
    </Panel>
  );
}

export function TopTeamsPanel({ limit = 5 }: { limit?: number }) {
  const { data, isLoading } = useLeaderboards();
  const rows = (data?.teams.win_rate ?? []).slice(0, limit);
  return (
    <Panel className="w-[430px] shrink-0" title="Top times" subtitle="Taxa de vitória de mapas">
      {isLoading ? <p className="text-fg-muted">Carregando…</p> : (
        <DataTable
          rows={rows}
          rowKey={(r) => r.team.name}
          emptyText="Sem times com 3 mapas neste filtro."
          columns={[
            { key: "#", header: "#", width: 28, className: `${mono} text-fg-muted`, render: (r) => r.rank },
            { key: "t", header: "Time", className: "font-semibold text-fg", render: (r) => <Link className="truncate hover:text-accent" to={`/time/${encodeURIComponent(r.team.name)}`}>{r.team.name}</Link> },
            { key: "vd", header: "V–D", width: 50, align: "right", className: mono, render: (r) => `${r.wins}–${r.losses}` },
            { key: "w", header: "% Vitórias", width: 140, className: mono, render: (r) => (
              <span className="flex items-center gap-2">
                <span className="h-[6px] w-24 overflow-hidden rounded-sm bg-surface-raised">
                  <span className="block h-full bg-cyan" style={{ width: `${r.value * 100}%` }} />
                </span>
                {pct(r.value)}
              </span>
            ) },
          ]}
        />
      )}
    </Panel>
  );
}
