// Global filters (tournament, map, date range). Owner: Stream E. Props are frozen; styling may change.
import type { MapRef, TournamentInfo } from "@/api/types";

export interface Filters {
  tournament?: string; // tournament id
  map?: string; // public map name
  date_from?: string;
  date_to?: string;
}

export interface FilterBarProps {
  value: Filters;
  onChange: (next: Filters) => void;
  tournaments: TournamentInfo[];
  maps: MapRef[];
}

const field = "border border-border bg-surface px-2 py-1 text-sm text-fg";

export function FilterBar({ value, onChange, tournaments, maps }: FilterBarProps) {
  const set = (patch: Filters) => onChange({ ...value, ...patch });
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select className={field} value={value.tournament ?? ""} onChange={(e) => set({ tournament: e.target.value || undefined })}>
        <option value="">Todos os torneios</option>
        {tournaments.map((t) => (
          <option key={t.id} value={t.id}>{t.name}</option>
        ))}
      </select>
      <select className={field} value={value.map ?? ""} onChange={(e) => set({ map: e.target.value || undefined })}>
        <option value="">Todos os mapas</option>
        {maps.map((m) => (
          <option key={m.codename} value={m.name}>{m.name}</option>
        ))}
      </select>
      <input type="date" className={field} value={value.date_from ?? ""} onChange={(e) => set({ date_from: e.target.value || undefined })} />
      <input type="date" className={field} value={value.date_to ?? ""} onChange={(e) => set({ date_to: e.target.value || undefined })} />
    </div>
  );
}
