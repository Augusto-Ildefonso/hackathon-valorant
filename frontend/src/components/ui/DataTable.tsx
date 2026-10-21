// Owner: Stream E. Props are frozen; styling may change.
import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

export function DataTable<T>({ columns, rows, rowKey, onRowClick, emptyText = "Nenhum dado." }: DataTableProps<T>) {
  if (rows.length === 0) return <p className="text-sm text-fg-muted">{emptyText}</p>;
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-border-strong text-xs uppercase tracking-widest text-fg-muted">
          {columns.map((c) => (
            <th key={c.key} className={`px-3 py-2 font-semibold ${c.align === "right" ? "text-right" : "text-left"}`}>
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr
            key={rowKey(r)}
            onClick={onRowClick ? () => onRowClick(r) : undefined}
            className={`border-b border-border ${onRowClick ? "cursor-pointer hover:bg-surface-raised" : ""}`}
          >
            {columns.map((c) => (
              <td key={c.key} className={`px-3 py-2 ${c.align === "right" ? "text-right font-mono" : ""}`}>
                {c.render(r)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
