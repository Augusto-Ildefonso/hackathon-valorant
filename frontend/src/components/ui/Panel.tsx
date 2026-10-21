// Titled content block + a stat cell that always shows its sample size. Added by Stream B; E may restyle (props stay).
import type { ReactNode } from "react";
import type { Stat } from "@/api/types";

export function Panel({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold uppercase tracking-widest text-fg-secondary">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

/** A formatted stat value followed by `n=` and a low-sample flag. */
export function StatValue({ stat, format }: { stat: Stat; format: (v: number | null) => string }) {
  return (
    <span className="font-mono">
      {format(stat.value)}
      <span className="ml-1 text-xs text-fg-muted">n={stat.sample_size}</span>
      {stat.low_sample && <span className="ml-1 text-xs text-amber" title="Amostra pequena">⚠</span>}
    </span>
  );
}
