// Owner: Stream E. Props are frozen; styling may change.
import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  message?: string;
  action?: ReactNode;
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="border border-dashed border-border-strong bg-surface p-6 text-center">
      <p className="font-display text-lg text-fg">{title}</p>
      {message && <p className="mt-1 text-sm text-fg-secondary">{message}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
