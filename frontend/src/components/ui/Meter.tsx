// Horizontal bar used in the tables of the Figma design (6px track + fill + optional % label). Owner: Stream E.
export function Meter({ value, color = "bg-cyan", width = 96, label }: { value: number | null | undefined; color?: string; width?: number; label?: string }) {
  const v = Math.max(0, Math.min(1, value ?? 0));
  return (
    <span className="flex items-center gap-2">
      <span className="h-[6px] overflow-hidden rounded-sm bg-surface-raised" style={{ width }}>
        <span className={`block h-full ${color}`} style={{ width: `${v * 100}%` }} />
      </span>
      {label !== undefined && <span className="font-mono font-medium text-fg-secondary">{label}</span>}
    </span>
  );
}
