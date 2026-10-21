// Figma table (header row: Chakra caps muted; rows: 12px padding, bottom border). Owner: Stream E. Props are frozen;
// `width` / `className` are optional additions: a column without `width` is flexible.
import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
  /** px width; omit for a flexible column */
  width?: number;
  className?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

const JUSTIFY = { left: "justify-start", right: "justify-end", center: "justify-center" } as const;

export function DataTable<T>({ columns, rows, rowKey, onRowClick, emptyText = "Nenhum dado." }: DataTableProps<T>) {
  if (rows.length === 0) return <p className="text-sm text-fg-muted">{emptyText}</p>;
  const cell = (c: Column<T>) => ({
    className: `flex min-w-0 items-center overflow-hidden ${JUSTIFY[c.align ?? (c.width ? "left" : "left")]} ${c.width ? "shrink-0" : "flex-1"}`,
    style: c.width ? { width: c.width } : undefined,
  });
  return (
    <div className="flex w-full flex-col">
      <div className="flex items-center gap-3 border-b border-border-strong py-2">
        {columns.map((c) => (
          <div key={c.key} {...cell(c)}>
            <span className="font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] whitespace-nowrap text-fg-muted">{c.header}</span>
          </div>
        ))}
      </div>
      {rows.map((r) => (
        <div
          key={rowKey(r)}
          onClick={onRowClick ? () => onRowClick(r) : undefined}
          className={`flex items-center gap-3 border-b border-border py-3 text-sm leading-5 ${onRowClick ? "cursor-pointer hover:bg-surface-raised" : ""}`}
        >
          {columns.map((c) => (
            <div key={c.key} {...cell(c)} className={`${cell(c).className} ${c.className ?? "text-fg-secondary"}`}>
              {c.render(r)}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
