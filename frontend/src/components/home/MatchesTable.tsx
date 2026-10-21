// Match list table used by Home ("Partidas recentes") and the Partidas page. Owner: Stream E.
import { Link } from "react-router-dom";
import type { MatchListItem } from "@/api/types";
import { MapIcon } from "@/components/ui/AgentIcon";
import { DataTable } from "@/components/ui/DataTable";
import { dateShort } from "@/lib/format";
import { tournamentLabel } from "@/lib/tournaments";

const mono = "font-mono font-medium";
const team = (name: string) => (
  <Link to={`/time/${encodeURIComponent(name)}`} className="truncate hover:text-accent" onClick={(e) => e.stopPropagation()}>{name}</Link>
);

export function MatchesTable({ items, onOpen }: { items: MatchListItem[]; onOpen: (m: MatchListItem) => void }) {
  return (
    <DataTable
      rows={items}
      rowKey={(m) => m.match_id}
      onRowClick={onOpen}
      emptyText="Nenhuma partida neste filtro."
      columns={[
        { key: "d", header: "Data", width: 90, className: `${mono} text-fg-muted`, render: (m) => dateShort(m.date) },
        { key: "t", header: "Torneio", width: 170, render: (m) => tournamentLabel(m.tournament, m.phase) },
        { key: "a", header: "Time A", align: "right", className: "font-semibold text-fg", render: (m) => team(m.team_a.team.name) },
        { key: "s", header: "Placar", width: 90, align: "center", className: `${mono} text-fg`, render: (m) => `${m.team_a.score} × ${m.team_b.score}` },
        { key: "b", header: "Time B", className: "font-semibold text-fg", render: (m) => team(m.team_b.team.name) },
        { key: "m", header: "Mapa", width: 130, render: (m) => <MapIcon map={m.map} showName /> },
        { key: "r", header: "", width: 110, align: "right", className: "text-accent", render: () => "Ver relatório →" },
      ]}
    />
  );
}
