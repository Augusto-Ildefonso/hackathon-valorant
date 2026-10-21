// Figma component "Filter Chip" (State=Off/On, 23:91). Owner: Stream E.
import type { ButtonHTMLAttributes } from "react";

export function FilterChip({ on = false, className = "", children, ...rest }: { on?: boolean } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={`flex shrink-0 items-center gap-2 rounded-sm border px-3 py-2 text-sm font-medium leading-5 whitespace-nowrap ${
        on ? "border-accent bg-surface-accent text-fg" : "border-border bg-surface text-fg-secondary hover:border-border-strong"
      } ${className}`}
    >
      {children}
    </button>
  );
}
