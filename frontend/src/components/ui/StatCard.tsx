// Owner: Stream E. Props are frozen; styling may change.
import type { Stat } from "@/api/types";

export interface StatCardProps {
  label: string;
  /** Pre-formatted value, e.g. "1,52" or "64%". Ignored when `stat` is given together with `format`. */
  value?: string;
  /** A Stat from the API; sample size and the low-sample flag are rendered automatically. */
  stat?: Stat;
  format?: (v: number) => string;
  hint?: string;
}

export function StatCard({ label, value, stat, format, hint }: StatCardProps) {
  const shown = value ?? (stat?.value != null ? (format ? format(stat.value) : String(stat.value)) : "—");
  return (
    <div className="border border-border bg-surface p-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-fg-muted">{label}</p>
      <p className="mt-1 font-mono text-2xl text-fg">{shown}</p>
      <p className="mt-1 text-xs text-fg-secondary">
        {stat && <span>n={stat.sample_size}</span>}
        {stat?.low_sample && <span className="ml-2 text-amber">amostra pequena</span>}
        {hint && <span className="ml-2">{hint}</span>}
      </p>
    </div>
  );
}
