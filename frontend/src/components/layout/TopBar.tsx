// Figma "Top Bar" (24:75): global search + Torneio / Mapa / Período filters. Owner: Stream E.
import { useState } from "react";
import { Link } from "react-router-dom";
import { useMeta, useSearch } from "@/api/hooks";
import { useFilters } from "@/lib/filters";
import { periodOptions, tournamentOptions, type Option } from "@/lib/tournaments";

/** Chip that looks like the Figma "Filter Chip" and opens a native select (accessible, no custom popover needed). */
function ChipSelect({ label, value, options, onChange }: { label: string; value: string; options: Option[]; onChange: (v: string) => void }) {
  const current = options.find((o) => o.value === value)?.label ?? options[0]?.label ?? "…";
  return (
    <label className="relative flex shrink-0 items-center gap-2 rounded-sm border border-border bg-surface px-3 py-2 text-sm font-medium leading-5 whitespace-nowrap text-fg-secondary hover:border-border-strong">
      {label}: {current} ▾
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} className="absolute inset-0 w-full cursor-pointer opacity-0">
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}

function SearchBox() {
  const [q, setQ] = useState("");
  const { data } = useSearch(q);
  const close = () => setQ("");
  const none = data && !data.players.length && !data.teams.length && !data.maps.length;
  return (
    <div className="relative w-[420px] max-w-full">
      <div className="flex h-10 items-center gap-2 rounded-sm border border-border bg-surface px-4 text-fg-muted">
        <span className="font-display text-base font-semibold">⌕</span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar jogador, time ou mapa…"
          className="w-full bg-transparent text-sm text-fg outline-none placeholder:text-fg-muted"
        />
      </div>
      {q.trim().length > 1 && data && (
        <div className="absolute left-0 right-0 top-11 z-20 max-h-96 space-y-3 overflow-auto rounded-sm border border-border-strong bg-surface-raised p-3 text-sm shadow-lg">
          {none && <p className="text-fg-muted">Nada encontrado.</p>}
          {data.players.length > 0 && (
            <div>
              <p className="mb-1 font-display text-xs uppercase tracking-[0.96px] text-fg-muted">Jogadores</p>
              {data.players.map((p) => (
                <Link key={p.player.puuid} onClick={close} to={`/jogador/${p.player.puuid}`} className="flex justify-between py-1 text-fg hover:text-accent">
                  <span>{p.player.riot_id}</span><span className="text-fg-muted">{p.team?.name}</span>
                </Link>
              ))}
            </div>
          )}
          {data.teams.length > 0 && (
            <div>
              <p className="mb-1 font-display text-xs uppercase tracking-[0.96px] text-fg-muted">Times</p>
              {data.teams.map((t) => (
                <Link key={t.team.name} onClick={close} to={`/time/${encodeURIComponent(t.team.name)}`} className="flex justify-between py-1 text-fg hover:text-accent">
                  <span>{t.team.name}</span><span className="text-fg-muted">{t.matches} partidas</span>
                </Link>
              ))}
            </div>
          )}
          {data.maps.length > 0 && (
            <div>
              <p className="mb-1 font-display text-xs uppercase tracking-[0.96px] text-fg-muted">Mapas</p>
              {data.maps.map((m) => (
                <Link key={m.map.name} onClick={close} to={`/mapa/${m.map.name}`} className="block py-1 text-fg hover:text-accent">{m.map.name}</Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TopBar() {
  const { data: meta } = useMeta();
  const { filters, set } = useFilters();
  const maps: Option[] = [{ value: "", label: "Todos" }, ...(meta?.maps ?? []).map((m) => ({ value: m.name, label: m.name }))];
  return (
    <div className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-bg-app px-8">
      <SearchBox />
      <div className="flex-1" />
      <ChipSelect label="Torneio" value={filters.tournament ?? ""} options={tournamentOptions(meta)} onChange={(v) => set({ tournament: v || undefined })} />
      <ChipSelect label="Mapa" value={filters.map ?? ""} options={maps} onChange={(v) => set({ map: v || undefined })} />
      <ChipSelect label="Período" value={filters.period ?? ""} options={periodOptions(meta)} onChange={(v) => set({ period: v || undefined })} />
    </div>
  );
}
