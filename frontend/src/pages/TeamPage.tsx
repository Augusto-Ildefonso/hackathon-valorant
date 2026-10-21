// Stub. Owner: Stream B.
import { useParams } from "react-router-dom";
import { useTeam } from "@/api/hooks";
import { InsightList } from "@/components/ui/InsightList";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";

export default function TeamPage() {
  const { teamName = "" } = useParams();
  const { data, isLoading, error } = useTeam(teamName);
  return (
    <>
      <PageHeader title={data?.team.name ?? teamName} subtitle="Perfil do time (em construção)" />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Partidas" value={String(data.record.matches)} />
            <StatCard label="Rounds vencidos" stat={data.record.round_win_rate} format={(v) => `${Math.round(v * 100)}%`} />
          </div>
          <InsightList insights={data.insights} />
        </div>
      )}
    </>
  );
}
