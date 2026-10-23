// Map Profile (Figma "Screen / Map Profile", 26:80). Owner: Stream C (layout from the design by Stream E).
// Data comes from /api/maps/{name} and /api/maps/{name}/heatmap (stubs return fixtures until Stream C ships them).
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useHeatmap, useMap, useMaps, useMeta } from "@/api/hooks";
import type { HeatLayer, InsightMode } from "@/api/types";
import { MinimapCanvas } from "@/components/map/MinimapCanvas";
import { CatalogIcon } from "@/components/ui/AgentIcon";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterChip } from "@/components/ui/FilterChip";
import { InsightCard } from "@/components/ui/InsightList";
import { InsightModeBar } from "@/components/ui/InsightModeBar";
import { Meter } from "@/components/ui/Meter";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { int, pct } from "@/lib/format";

type Side = "both" | "attack" | "defense";
type Layer = "deaths" | "kills" | "danger" | "uncovered" | "plants";
const SIDES: Array<[Side, string]> = [["both", "Ambos"], ["attack", "Ataque"], ["defense", "Defesa"]];
const LAYERS: Array<[Layer, string]> = [["deaths", "Mortes"], ["kills", "Abates"], ["danger", "Zonas perigosas"], ["uncovered", "Zonas descobertas"], ["plants", "Plantes"]];

export default function MapPage() {
  const { mapName = "" } = useParams();
  const navigate = useNavigate();
  const { data: meta } = useMeta();
  const maps = useMaps();
  const [mode, setMode] = useState<InsightMode>("rules");
  const { data: m, isLoading, isFetching, error } = useMap(mapName, mode);
  const [side, setSide] = useState<Side>("both");
  const [layers, setLayers] = useState<Set<Layer>>(new Set(["deaths", "danger", "uncovered", "plants"]));
  const { data: heat } = useHeatmap(mapName, { side });
  const toggle = (l: Layer) => setLayers((s) => { const n = new Set(s); n.has(l) ? n.delete(l) : n.add(l); return n; });

  if (error) return <EmptyState title="Mapa não encontrado" message="Não há dados deste mapa para os filtros atuais." />;
  const gap = m ? Math.abs((m.defense_win_rate.value ?? 0) - (m.attack_win_rate.value ?? 0)) * 100 : 0;
  const layerOf = (k: "kills" | "deaths" | "danger" | "uncovered"): HeatLayer | null => (layers.has(k) ? heat?.[k] ?? null : null);
  const heatLayers = [
    [layerOf("deaths"), "red", 0.7], [layerOf("kills"), "green", 0.7], [layerOf("danger"), "red", 0.9], [layerOf("uncovered"), "cyan", 0.75],
  ].flatMap(([layer, color, opacity]) => (layer ? [{ layer: layer as HeatLayer, color: color as "red", opacity: opacity as number }] : []));

  return (
    <>
      <PageHeader
        title={`Mapa · ${m?.map.name ?? mapName}`}
        subtitle={m ? `${m.matches} partidas · ${int(m.rounds)} rounds analisados` : isLoading ? "Carregando…" : undefined}
      />
      <div className="flex flex-wrap gap-2">
        {/* most played first (rounds from /api/maps), maps without a minimap last */}
        {(maps.data ? maps.data.items.map((i) => i.map) : [...(meta?.maps ?? [])])
          .sort((a, b) => Number(b.has_minimap) - Number(a.has_minimap)).map((x) => (
          <FilterChip key={x.codename} on={x.name === mapName} onClick={() => navigate(`/mapa/${x.name}`)} className={x.has_minimap ? "" : "text-fg-muted"}>
            {x.name}{x.has_minimap ? "" : " · sem minimapa"}
          </FilterChip>
        ))}
      </div>

      {m && (
        <>
          <div className="flex items-start gap-4 stack">
            <Panel
              className="flex-[680]"
              title="Mapa tático"
              subtitle="Mortes e abates agregados no minimapa"
              aside={<div className="flex gap-2">{SIDES.map(([v, l]) => <FilterChip key={v} on={side === v} onClick={() => setSide(v)}>{l}</FilterChip>)}</div>}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="mr-1 font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-muted">Camadas</span>
                {LAYERS.map(([v, l]) => <FilterChip key={v} on={layers.has(v)} onClick={() => toggle(v)}>{l}</FilterChip>)}
              </div>
              <div className="flex flex-col gap-2">
                <MinimapCanvas
                  map={m.map}
                  size={580}
                  heat={heatLayers}
                  zoneLayer={layers.has("uncovered") ? heat?.uncovered : null}
                  points={layers.has("plants") ? m.plants.map((p) => ({ point: p.point, kind: "plant" as const, label: p.site })) : []}
                />
                {m.map.has_minimap && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-fg-secondary">
                    <span><span className="mr-1 inline-block size-2 rounded-full bg-accent" />Morte</span>
                    <span><span className="mr-1 inline-block size-2 rounded-full bg-amber" />Plante</span>
                    <span><span className="mr-1 inline-block size-2 rounded-full bg-cyan" />Zona descoberta</span>
                  </div>
                )}
              </div>
            </Panel>

            <div className="flex flex-[440] flex-col gap-4">
              <Panel title="Classificação" subtitle="Quem vence mais rounds neste mapa">
                <div className="flex items-center gap-2">
                  <Badge tone={m.classification === "attack" ? "red" : m.classification === "defense" ? "violet" : "neutral"}>
                    {m.classification === "balanced" ? "Equilibrado" : `Favorece ${m.classification === "attack" ? "ataque" : "defesa"}`}
                  </Badge>
                  {m.classification !== "balanced" && (
                    <span className="text-sm text-fg-secondary">+{Math.round(gap)} p.p. sobre {m.classification === "attack" ? "a defesa" : "o ataque"}</span>
                  )}
                </div>
                <div className="flex h-[14px] overflow-hidden rounded-sm">
                  <div className="bg-accent" style={{ width: `${(m.attack_win_rate.value ?? 0.5) * 100}%` }} />
                  <div className="flex-1 bg-violet" />
                </div>
                <div className="flex justify-between">
                  <div>
                    <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-accent">Ataque</p>
                    <p className="font-display text-[32px] font-bold leading-10 text-fg">{pct(m.attack_win_rate.value)}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-violet">Defesa</p>
                    <p className="font-display text-[32px] font-bold leading-10 text-fg">{pct(m.defense_win_rate.value)}</p>
                  </div>
                </div>
                <p className="text-[11px] leading-[14px] text-fg-muted">Amostra: {int(m.attack_win_rate.sample_size)} rounds · {m.matches} partidas</p>
              </Panel>

              <Panel title="Agentes mais usados" subtitle="% de jogadores por partida">
                <Usage rows={m.top_agents.slice(0, 5)} color="bg-cyan" unknown="Agente desconhecido" kind="agent" />
              </Panel>
              <Panel title="Armas mais usadas" subtitle="% de rounds com a arma comprada">
                <Usage rows={m.top_weapons.slice(0, 5)} color="bg-amber" unknown="Arma desconhecida" kind="weapon" />
              </Panel>
            </div>
          </div>

          <InsightModeBar mode={mode} onChange={setMode} loading={isFetching && mode === "llm" && m.insights_source !== "llm"} source={m.insights_source} />
          <Panel title="Pontos cegos" subtitle="Duas camadas: zonas perigosas (mortes ≫ abates) e zonas descobertas (pouco cobertas, mas de onde saem abates inimigos)">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {m.insights.length === 0 && <p className="col-span-3 text-sm text-fg-muted">Sem dados suficientes para sugerir.</p>}
              {m.insights.map((i) => <InsightCard key={i.id} insight={i} />)}
            </div>
          </Panel>
        </>
      )}
    </>
  );
}

function Usage({ rows, color, unknown, kind }: {
  rows: Array<{ id: string; name: string | null; icon_url: string | null; share: number }>; color: string; unknown: string; kind: "agent" | "weapon";
}) {
  return (
    <div className="flex flex-col">
      {rows.map((r) => (
        <div key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border py-3 text-sm">
          <span className="flex w-[186px] shrink-0 items-center gap-2 font-semibold text-fg">
            <CatalogIcon url={r.icon_url} name={r.name ?? unknown} kind={kind} w={kind === "agent" ? 24 : 40} h={kind === "agent" ? 24 : 16} />
            <span className="truncate">{r.name ?? unknown}</span>
          </span>
          <Meter width={156} color={color} value={r.share} label={pct(r.share)} />
        </div>
      ))}
      {rows.length === 0 && <p className="text-sm text-fg-muted">Sem dados.</p>}
    </div>
  );
}
