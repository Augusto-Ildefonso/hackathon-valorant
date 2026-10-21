// Global filters (tournament/phase, map, period) shared by every screen and persisted in localStorage. Owner: Stream E.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export interface Filters {
  /** tournament id, optionally with a phase prefix: "UNIVAVA" or "UNIVAVA/Classificat" */
  tournament?: string;
  /** public map name, e.g. "Lotus" */
  map?: string;
  /** "YYYY-MM" month, or undefined for everything */
  period?: string;
}

const KEY = "vavagym.filters";

function load(): Filters {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}") as Filters;
  } catch {
    return {};
  }
}

interface Ctx {
  filters: Filters;
  set: (patch: Partial<Filters>) => void;
  reset: () => void;
}
const FiltersContext = createContext<Ctx>({ filters: {}, set: () => {}, reset: () => {} });

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<Filters>(load);
  const persist = (f: Filters) => {
    setFilters(f);
    try {
      localStorage.setItem(KEY, JSON.stringify(f));
    } catch {
      /* storage unavailable: filters just stay in memory */
    }
  };
  const set = useCallback((patch: Partial<Filters>) => persist({ ...filters, ...patch }), [filters]);
  const value = useMemo(() => ({ filters, set, reset: () => persist({}) }), [filters, set]);
  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export const useFilters = () => useContext(FiltersContext);

/** Query params understood by the API for the current filters. */
export function filterQuery(f: Filters, keys: Array<"tournament" | "map" | "dates"> = ["tournament", "map", "dates"]) {
  const q: Record<string, string | undefined> = {};
  if (keys.includes("tournament")) q.tournament = f.tournament;
  if (keys.includes("map")) q.map = f.map;
  if (keys.includes("dates") && f.period) {
    const [y, m] = f.period.split("-").map(Number);
    const last = new Date(y, m, 0).getDate();
    q.date_from = `${f.period}-01`;
    q.date_to = `${f.period}-${String(last).padStart(2, "0")}`;
  }
  return q;
}
