// Owner: Stream E. Props are frozen; styling may change.
import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="mb-6 flex items-end justify-between gap-4 border-b border-border pb-4">
      <div>
        <h1 className="font-display text-3xl font-semibold uppercase tracking-wide text-fg">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-fg-secondary">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}
