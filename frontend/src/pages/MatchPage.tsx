// Stub. Owner: Stream C.
import { useParams } from "react-router-dom";
import { useMatch } from "@/api/hooks";
import { PageHeader } from "@/components/ui/PageHeader";

export default function MatchPage() {
  const { matchId = "" } = useParams();
  const { data, isLoading, error } = useMatch(matchId);
  return (
    <>
      <PageHeader
        title={data ? `${data.team_a.team.name} ${data.team_a.score} x ${data.team_b.score} ${data.team_b.team.name}` : "Partida"}
        subtitle={data ? `${data.map.name} · ${data.date}` : "Relatório da partida (em construção)"}
      />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
    </>
  );
}
