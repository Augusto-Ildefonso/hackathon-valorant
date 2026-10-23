// Figma "Title" block (Display H1 28/34 + body subtitle). Owner: Stream E. Props are frozen; styling may change.
import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
      <div className="flex min-w-0 flex-col gap-1">
        <h1 className="font-display text-2xl font-bold leading-[30px] text-fg sm:text-[28px] sm:leading-[34px]">{title}</h1>
        {subtitle && <p className="text-sm leading-5 text-fg-secondary">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}
