// Figma component "Badge" (Tone=Red/Cyan/Amber/Violet/Green/Neutral, 23:75). Owner: Stream E.
import type { ReactNode } from "react";

export type Tone = "red" | "cyan" | "amber" | "violet" | "green" | "neutral";

const TONE: Record<Tone, string> = {
  red: "bg-tint-red text-accent",
  cyan: "bg-tint-cyan text-cyan",
  amber: "bg-tint-amber text-amber",
  violet: "bg-tint-violet text-violet",
  green: "bg-tint-green text-green",
  neutral: "bg-tint-neutral text-fg-secondary",
};

export function Badge({ tone = "red", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-sm px-2 py-1 font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] whitespace-nowrap ${TONE[tone]} ${className}`}>
      {children}
    </span>
  );
}
