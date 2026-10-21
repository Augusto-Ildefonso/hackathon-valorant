// Stub. Owner: Stream B.
import { useParams } from "react-router-dom";
import { usePlayer } from "@/api/hooks";
import { InsightList } from "@/components/ui/InsightList";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";

export default function PlayerPage() {
  const { puuid = "" } = useParams();
  const { data, isLoading, error } = usePlayer(puuid);
  return (
    <>
      <PageHeader title={data?.player.riot_id ?? "Jogador"} subtitle="Perfil do jogador (em construção)" />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="K/D" stat={data.stats.kd} />
            <StatCard label="ADR" stat={data.stats.adr} />
            <StatCard label="HS%" stat={data.stats.hs_pct} format={(v) => `${Math.round(v * 100)}%`} />
          </div>
          <InsightList insights={data.insights} />
        </div>
      )}
    </>
  );
}
