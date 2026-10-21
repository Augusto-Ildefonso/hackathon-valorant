// Sidebar destinations that have no Figma frame (Jogadores, Times, Mapas, Partidas): simple lists in the same visual
// language, built only from existing endpoints. Owner: Stream E.
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMaps, useMatches, useTeams } from "@/api/hooks";
import { MatchesTable } from "@/components/home/MatchesTable";
import { TopPlayersPanel } from "@/components/home/Leaderboards";
import { DataTable } from "@/components/ui/DataTable";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { dateShort, int, pct } from "@/lib/format";

const mono = "font-mono font-medium";

export function PlayersListPage() {
  return (
    <>
      <PageHeader title="Jogadores" subtitle="Rankings por desempenho. Use a busca no topo para achar qualquer jogador." />
      <div className="flex"><TopPlayersPanel limit={25} title="Ranking de jogadores" /></div>
    </>
  );
}

export function TeamsListPage() {
  const { data, isLoading } = useTeams();
  return (
    <>
      <PageHeader title="Times" subtitle="Todos os times encontrados nos arquivos de partidas" />
      <Panel title="Times" subtitle="Ordenado por número de partidas">
        {isLoading ? <p className="text-fg-muted">Carregando…</p> : (
          <DataTable
            rows={data?.items ?? []}
            rowKey={(t) => t.team.name}
            columns={[
              { key: "t", header: "Time", className: "font-semibold text-fg", render: (t) => <Link className="hover:text-accent" to={`/time/${encodeURIComponent(t.team.name)}`}>{t.team.name}</Link> },
              { key: "m", header: "Partidas", width: 80, align: "right", className: mono, render: (t) => t.matches },
              { key: "w", header: "% Vitórias", width: 100, align: "right", className: mono, render: (t) => pct(t.win_rate.value) },
              { key: "r", header: "% Rounds", width: 100, align: "right", className: mono, render: (t) => pct(t.round_win_rate.value) },
              { key: "d", header: "Última", width: 90, className: `${mono} text-fg-muted`, render: (t) => dateShort(t.last_match_date) },
            ]}
          />
        )}
      </Panel>
    </>
  );
}

export function MapsListPage() {
  const { data, isLoading } = useMaps();
  return (
    <>
      <PageHeader title="Mapas" subtitle="Escolha um mapa para ver zonas de risco, plants e lados favorecidos" />
      <Panel title="Mapas" subtitle="Ordenado por partidas jogadas">
        {isLoading ? <p className="text-fg-muted">Carregando…</p> : (
          <DataTable
            rows={[...(data?.items ?? [])].sort((a, b) => b.matches - a.matches)}
            rowKey={(m) => m.map.codename}
            columns={[
              { key: "m", header: "Mapa", className: "font-semibold text-fg", render: (m) => (
                <Link className="hover:text-accent" to={`/mapa/${m.map.name}`}>
                  {m.map.name}{!m.map.has_minimap && <span className="ml-2 text-xs font-normal text-fg-muted">(sem minimapa)</span>}
                </Link>
              ) },
              { key: "n", header: "Partidas", width: 90, align: "right", className: mono, render: (m) => m.matches },
              { key: "r", header: "Rounds", width: 90, align: "right", className: mono, render: (m) => int(m.rounds) },
              { key: "a", header: "Vitória no ataque", width: 140, align: "right", className: mono, render: (m) => pct(m.attack_win_rate.value) },
            ]}
          />
        )}
      </Panel>
    </>
  );
}

export function MatchesListPage() {
  const navigate = useNavigate();
  const [limit, setLimit] = useState(50);
  const { data, isLoading } = useMatches({ limit });
  return (
    <>
      <PageHeader title="Partidas" subtitle="Clique em uma partida para abrir o relatório" />
      <Panel title="Todas as partidas" subtitle={data ? `${data.items.length} de ${data.total}` : undefined}>
        {isLoading ? <p className="text-fg-muted">Carregando…</p> : <MatchesTable items={data?.items ?? []} onOpen={(m) => navigate(`/partida/${m.match_id}`)} />}
        {data && data.items.length < data.total && (
          <button onClick={() => setLimit(limit + 50)} className="self-start font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">
            Carregar mais →
          </button>
        )}
      </Panel>
    </>
  );
}
