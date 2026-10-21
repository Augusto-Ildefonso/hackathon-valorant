// Stub. Owner: Stream D. Round-by-round plan for the whole match (see project-details §5.6).
import { usePlan } from "@/api/hooks";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ActionPlanPage() {
  const plan = usePlan();
  return (
    <>
      <PageHeader title="Plano de ação" subtitle="Plano rodada a rodada para a partida inteira (em construção)" />
      <button
        className="bg-accent px-4 py-2 font-display text-sm font-semibold uppercase text-on-accent hover:bg-accent-hover"
        onClick={() =>
          plan.mutate({ team_a: "Fatec PG", team_b: "Panterão Gaming", map: "Ascent", perspective: "a", rounds_per_half: 12, starting_side: "attack" })
        }
      >
        Gerar plano
      </button>
      {plan.data && <p className="mt-4 text-fg-secondary">{plan.data.rounds.length} rounds planejados.</p>}
      {plan.error && <p className="mt-4 text-accent">Erro: {String(plan.error)}</p>}
    </>
  );
}
