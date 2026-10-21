// Renders Insight[] with evidence + low-sample badge. Owner: Stream E. Props are frozen; styling may change.
import type { Insight, InsightKind } from "@/api/types";

export interface InsightListProps {
  insights: Insight[];
  /** Show only these kinds (default: all). */
  kinds?: InsightKind[];
  emptyText?: string;
}

const KIND_LABEL: Record<InsightKind, string> = {
  strength: "Ponto forte",
  weakness: "Ponto fraco",
  tip: "Recomendação",
  strategy: "Estratégia",
};
const KIND_COLOR: Record<InsightKind, string> = {
  strength: "text-green",
  weakness: "text-accent",
  tip: "text-cyan",
  strategy: "text-violet",
};

export function InsightList({ insights, kinds, emptyText = "Sem dados suficientes para sugerir." }: InsightListProps) {
  const items = kinds ? insights.filter((i) => kinds.includes(i.kind)) : insights;
  if (items.length === 0) return <p className="text-sm text-fg-muted">{emptyText}</p>;
  return (
    <ul className="space-y-2">
      {items.map((i) => (
        <li key={i.id} className="border border-border bg-surface p-3">
          <p className={`text-xs font-semibold uppercase tracking-widest ${KIND_COLOR[i.kind]}`}>{KIND_LABEL[i.kind]}</p>
          <p className="mt-1 text-sm text-fg">{i.text_pt}</p>
          <p className="mt-1 font-mono text-xs text-fg-muted">
            {i.evidence.metric}: {i.evidence.value}
            {i.evidence.baseline != null && ` (média ${i.evidence.baseline})`} · n={i.evidence.sample_size}
            {i.low_sample && <span className="ml-2 text-amber">amostra pequena</span>}
          </p>
        </li>
      ))}
    </ul>
  );
}
