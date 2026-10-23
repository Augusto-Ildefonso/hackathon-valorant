// Figma "Panel / ..." card: title + subtitle header with an optional right slot. Owner: Stream E (added by B).
import type { ReactNode } from "react";
import type { Stat } from "@/api/types";

export function Panel({ title, subtitle, aside, children, className = "" }: {
  title: string; subtitle?: string; aside?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`flex min-w-0 flex-col gap-4 rounded-md border border-border bg-surface p-4 sm:p-5 ${className}`}>
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-xl font-semibold leading-[26px] text-fg">{title}</h2>
          {subtitle && <p className="text-xs leading-4 text-fg-muted">{subtitle}</p>}
        </div>
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
