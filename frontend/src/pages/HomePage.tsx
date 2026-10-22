// Home / Visão Geral (Figma "Screen / Home", 25:17). Owner: Stream E.
import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMaps, useMatches, useMeta } from "@/api/hooks";
import { MatchesTable } from "@/components/home/MatchesTable";
import { TopPlayersPanel, TopTeamsPanel } from "@/components/home/Leaderboards";
import { FilterChip } from "@/components/ui/FilterChip";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { dateBR, int, num } from "@/lib/format";
import { useFilters } from "@/lib/filters";
import { tournamentOptions } from "@/lib/tournaments";

export default function HomePage() {
  const navigate = useNavigate();
  const { data: meta, error } = useMeta();
  const maps = useMaps();
  const recent = useMatches({ limit: 4 });
  const { filters, set } = useFilters();
  const [params] = useSearchParams();
  const wanted = params.get("tournament");  // deep link from the chat: /campeonatos?tournament=ID
  useEffect(() => { if (wanted) set({ tournament: wanted }); }, [wanted]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <p className="text-accent">Erro ao carregar os dados: {String(error)}</p>;
  const k = meta?.kpis;
  const top = [...(maps.data?.items ?? [])].sort((a, b) => b.matches - a.matches)[0];
  const phases = meta?.tournaments.reduce((n, t) => n + Math.max(1, t.phases.length), 0);
  const names = [...new Set((meta?.tournaments ?? []).map((t) => (t.name.startsWith("Rush Series") ? "Rush Series" : t.name)))].join(" e ");

  return (
    <>
      <PageHeader
        title="Campeonatos"
        subtitle={meta ? `Partidas customizadas de VALORANT · ${names} · ${dateBR(meta.date_from)} – ${dateBR(meta.date_to)}` : "Carregando…"}
      />
      <div className="flex gap-4">
        <StatCard label="Partidas" value={k ? int(k.matches) : "—"} footnote="mapas jogados" />
        <StatCard label="Rounds" value={k ? int(k.rounds) : "—"} footnote={phases ? `em ${phases} torneios/fases` : undefined} />
        <StatCard label="Abates" value={k ? int(k.kills) : "—"} footnote={k ? `média ${num(k.kills / k.rounds, 1)} por round` : undefined} />
        <StatCard label="Jogadores" value={k ? int(k.players) : "—"} footnote="identificados por puuid" />
        <StatCard label="Times" value={k ? int(k.teams) : "—"} footnote="nomes extraídos dos arquivos" />
        <StatCard label="Mapas" value={meta ? String(meta.maps.length) : "—"} footnote={top ? `${top.map.name} lidera com ${top.matches}` : undefined} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] text-fg-muted">Torneio</span>
        {tournamentOptions(meta).map((o) => (
          <FilterChip key={o.value} on={(filters.tournament ?? "") === o.value} onClick={() => set({ tournament: o.value || undefined })}>
            {o.label}
          </FilterChip>
        ))}
      </div>

      <div className="flex items-start gap-4">
        <TopPlayersPanel />
        <TopTeamsPanel />
      </div>

      <Panel
        title="Partidas recentes"
        subtitle="Clique para abrir o relatório da partida"
        aside={<Link to="/partidas" className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">Ver todas →</Link>}
      >
        <MatchesTable items={recent.data?.items ?? []} onOpen={(m) => navigate(`/partida/${m.match_id}`)} />
      </Panel>
    </>
  );
}
