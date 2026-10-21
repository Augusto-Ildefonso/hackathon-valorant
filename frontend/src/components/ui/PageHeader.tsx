// Figma "Title" block (Display H1 28/34 + body subtitle). Owner: Stream E. Props are frozen; styling may change.
import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="flex items-end justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        <h1 className="font-display text-[28px] font-bold leading-[34px] text-fg">{title}</h1>
        {subtitle && <p className="text-sm leading-5 text-fg-secondary">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}
