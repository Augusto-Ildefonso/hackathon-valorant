// Figma component "Insight Card" (Kind=Strength/Weakness/Tip/Strategy, 24:46): colored bar, label, text, mono evidence.
// Renders Insight[] with evidence + low-sample badge. Owner: Stream E. Props are frozen; styling may change.
import type { Insight, InsightKind } from "@/api/types";
import { num } from "@/lib/format";

export interface InsightListProps {
  insights: Insight[];
  /** Show only these kinds (default: all). */
  kinds?: InsightKind[];
  emptyText?: string;
}

const KIND: Record<InsightKind, { label: string; bar: string; text: string }> = {
  strength: { label: "Ponto forte", bar: "bg-green", text: "text-green" },
  weakness: { label: "Ponto fraco", bar: "bg-accent", text: "text-accent" },
  tip: { label: "Recomendação", bar: "bg-cyan", text: "text-cyan" },
  strategy: { label: "Estratégia", bar: "bg-violet", text: "text-violet" },
};

/** Evidence values already come in display units (percentages as 0-100); `unit` tells how to print them. */
const shown = (v: number, unit?: string | null) => (unit === "%" ? `${num(v, 0)}%` : num(v));

export function InsightCard({ insight }: { insight: Insight }) {
  const k = KIND[insight.kind];
  const ev = insight.evidence;
  return (
    <div className="flex items-stretch overflow-hidden rounded-md border border-border bg-surface">
      <div className={`w-[3px] shrink-0 ${k.bar}`} />
      <div className="flex min-w-0 flex-1 flex-col gap-[6px] px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] ${k.text}`}>{k.label}</span>
          {insight.low_sample && <span className="rounded-sm bg-tint-amber px-2 text-[11px] font-medium leading-[14px] text-amber">AMOSTRA BAIXA</span>}
        </div>
        <p className="text-sm leading-5 text-fg">{insight.text_pt}</p>
        <p className="font-mono text-xs font-medium leading-5 text-fg-muted">
          {ev.metric} {shown(ev.value, ev.unit)}
          {ev.baseline != null && ` · base ${shown(ev.baseline, ev.unit)}`} · n = {ev.sample_size}
        </p>
      </div>
    </div>
  );
}

export function InsightList({ insights, kinds, emptyText = "Sem dados suficientes para sugerir." }: InsightListProps) {
  const items = kinds ? insights.filter((i) => kinds.includes(i.kind)) : insights;
  if (items.length === 0) return <p className="text-sm text-fg-muted">{emptyText}</p>;
  return (
    <div className="flex flex-col gap-3">
      {items.map((i) => <InsightCard key={i.id} insight={i} />)}
    </div>
  );
}
