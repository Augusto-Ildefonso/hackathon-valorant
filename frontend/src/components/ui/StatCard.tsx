// Figma component "Stat Card" (24:4). Owner: Stream E. Props are frozen; `hint` is kept as an alias of `footnote`.
import type { Stat } from "@/api/types";

export interface StatCardProps {
  label: string;
  /** Pre-formatted value, e.g. "1,52" or "64%". */
  value?: string;
  /** A Stat from the API; the sample size is appended to the footnote and a low-sample flag is shown. */
  stat?: Stat;
  format?: (v: number) => string;
  footnote?: string;
  hint?: string;
  /** Shows the "amostra pequena" flag (use with pre-formatted `value`; `stat` sets it automatically). */
  lowSample?: boolean;
  className?: string;
}

export function StatCard({ label, value, stat, format, footnote, hint, lowSample, className = "" }: StatCardProps) {
  const shown = value ?? (stat?.value != null ? (format ? format(stat.value) : String(stat.value)) : "—");
  const note = footnote ?? hint;
  return (
    <div className={`flex min-w-0 flex-1 flex-col gap-1 rounded-md border border-border bg-surface p-4 ${className}`}>
      <p className="font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] text-fg-muted">{label}</p>
      <p className="font-display text-[32px] font-bold leading-10 text-fg">{shown}</p>
      <p className="text-[11px] font-medium leading-[14px] text-fg-muted">
        {note}
        {stat && <span>{note ? " · " : ""}n = {stat.sample_size}</span>}
        {(stat?.low_sample || lowSample) && <span className="ml-1 text-amber">⚠ amostra pequena</span>}
      </p>
    </div>
  );
}
