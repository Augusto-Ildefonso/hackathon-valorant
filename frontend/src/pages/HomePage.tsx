// Stub. Owner: Stream E.
import { useMeta } from "@/api/hooks";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";

export default function HomePage() {
  const { data, isLoading, error } = useMeta();
  return (
    <>
      <PageHeader title="Visão geral" subtitle="Busca, KPIs, rankings e partidas recentes (em construção)" />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
      {data && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <StatCard label="Partidas" value={String(data.kpis.matches)} />
          <StatCard label="Rounds" value={String(data.kpis.rounds)} />
          <StatCard label="Kills" value={String(data.kpis.kills)} />
          <StatCard label="Jogadores" value={String(data.kpis.players)} />
          <StatCard label="Times" value={String(data.kpis.teams)} />
          <StatCard label="Torneios" value={String(data.kpis.tournaments)} />
        </div>
      )}
    </>
  );
}
