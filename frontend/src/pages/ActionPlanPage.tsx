// Action Plan (Figma "Screen / Action Plan", 32:432): round-by-round plan for the whole match. Owner: Stream D
// (layout from the design by Stream E). Data: POST /api/plan (stub returns a fixture until Stream D ships it).
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useMaps, useMeta, usePlan, usePlanCapabilities, useTeams } from "@/api/hooks";
import type { PlanRequest, PlanResponse, RoundPlan, RoundType, Side } from "@/api/types";
import { MinimapCanvas } from "@/components/map/MinimapCanvas";
import { AgentIcon, MapIcon, WeaponIcon } from "@/components/ui/AgentIcon";
import { Badge, type Tone } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { FilterChip } from "@/components/ui/FilterChip";
import { InsightCard } from "@/components/ui/InsightList";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { ROUND_TYPE_PT, pct, seconds } from "@/lib/format";

const TYPE_TONE: Record<RoundType, Tone> = { pistol: "violet", eco: "amber", semi_eco: "neutral", force: "red", full_buy: "green" };
const TYPE_SHORT: Record<RoundType, string> = { pistol: "PISTOL", eco: "ECO", semi_eco: "SEMI", force: "FORCE", full_buy: "FULL" };
const SIDE_PT: Record<Side, string> = { attack: "Ataque", defense: "Defesa" };
const SIDE_SHORT: Record<Side, string> = { attack: "ATQ", defense: "DEF" };
const ROUND_SECTION = "plano-round-detalhe";
const TIMING_PT: Record<string, string> = { early: "cedo", default: "padrão", late: "tardio" };
const label = "font-display text-xs font-semibold uppercase leading-4 tracking-[0.96px] text-fg-muted";
const mono = "font-mono font-medium";

function Picker({ title, value, sub, options, onChange, ring, icon }: {
  title: string; value: string; sub?: string; options: Array<[string, string]>; onChange: (v: string) => void; ring?: string; icon?: ReactNode;
}) {
  return (
    <label className={`relative flex min-w-0 flex-1 cursor-pointer flex-col gap-[2px] rounded-sm border bg-surface px-4 py-3 ${ring ?? "border-border"}`}>
      <span className={label}>{title}</span>
      <span className="flex items-center justify-between gap-2 text-sm font-medium text-fg"><span className="flex min-w-0 items-center gap-2">{icon}<span className="truncate">{options.find(([v]) => v === value)?.[1] ?? value}</span></span><span className="text-[10px] text-fg-muted">▾</span></span>
      <span className="text-[11px] leading-[14px] text-fg-muted">{sub ?? " "}</span>
      <select aria-label={title} value={value} onChange={(e) => onChange(e.target.value)} className="absolute inset-0 w-full cursor-pointer opacity-0">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}

/** Weapons of the round's buy as pictures with their counts (Figma: "[Vandal] ×3 [Operator] ×1 [Phantom]"). */
function BuyIcons({ r }: { r: RoundPlan }) {
  const counts = new Map<string, { weapon: RoundPlan["buy"][number]["weapon"]; n: number }>();
  for (const b of r.buy) {
    if (!b.weapon) continue;
    const e = counts.get(b.weapon.id) ?? { weapon: b.weapon, n: 0 };
    e.n++;
    counts.set(b.weapon.id, e);
  }
  if (!counts.size) return <span>—</span>;
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
      {[...counts.values()].map(({ weapon, n }) => (
        <span key={weapon!.id} className="inline-flex items-center gap-1">
          <WeaponIcon weapon={weapon} size={14} />
          {n > 1 && <span className="font-mono text-xs text-fg-secondary">×{n}</span>}
        </span>
      ))}
    </span>
  );
}

function RoundChip({ r, selected, onClick }: { r: RoundPlan; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex h-[78px] w-[88px] shrink-0 flex-col items-center justify-center gap-1 border ${selected ? "border-accent bg-surface-accent" : "border-border bg-surface-raised/40 hover:border-border-strong"}`}
    >
      <span className="flex items-center gap-1 text-xs font-medium text-fg-secondary">
        R{r.number}<span className={`size-[6px] rounded-full ${r.base_scenario_result === "win" ? "bg-green" : "bg-accent"}`} />
      </span>
      <span className={`font-display text-[11px] font-semibold ${r.side === "attack" ? "text-accent" : "text-violet"}`}>{SIDE_SHORT[r.side]}</span>
      <Badge tone={TYPE_TONE[r.round_type]} className="!px-2 !py-0 text-[11px]">{TYPE_SHORT[r.round_type]}</Badge>
    </button>
  );
}

function RoundDetail({ plan, round, prev }: { plan: PlanResponse; round: RoundPlan; prev?: RoundPlan }) {
  const c = round.contingency;
  const baseWon = prev?.base_scenario_result === "win";
  return (
    <Panel
      title={`Round ${round.number} · ${SIDE_PT[round.side]} · ${ROUND_TYPE_PT[round.round_type]}`}
      subtitle="Detalhe do plano para o round selecionado"
      aside={
        <div className="flex gap-2">
          <Badge tone={TYPE_TONE[round.round_type]}>{ROUND_TYPE_PT[round.round_type]}</Badge>
          <Badge tone={round.side === "attack" ? "red" : "violet"}>{SIDE_PT[round.side]}</Badge>
          <Badge tone="neutral">Cenário base: {round.base_scenario_result === "win" ? "vitória" : "derrota"}</Badge>
        </div>
      }
    >
      <div className="grid grid-cols-3 gap-5">
        <div className="flex flex-col gap-4">
          <p className={label}>Economia projetada</p>
          <div className="flex flex-col">
            <div className="flex justify-between border-b border-border py-3 text-sm"><span className="text-fg-secondary">Créditos do time</span><span className={`${mono} text-amber`}>{round.projected_economy.team_credits.toLocaleString("pt-BR")}</span></div>
            <div className="flex justify-between border-b border-border py-3 text-sm"><span className="text-fg-secondary">Créditos do inimigo</span><span className={`${mono} text-accent`}>{round.projected_economy.enemy_credits.toLocaleString("pt-BR")}</span></div>
          </div>
          <p className="text-xs leading-4 text-fg-muted">{round.projected_economy.reasoning_pt}</p>
          <p className={label}>Compra recomendada</p>
          <div className="flex flex-col gap-2">
            {round.buy.map((b, i) => (
              <div key={i} className="rounded-sm border border-border bg-surface-raised/50 px-3 py-2">
                <p className="text-sm font-semibold capitalize text-fg">{b.role}</p>
                <p className="flex items-center gap-[6px] text-[11px] leading-4 text-fg-secondary">
                  {b.weapon && <WeaponIcon weapon={b.weapon} size={16} />}
                  {b.weapon?.name ?? "Guardar"}{b.armor !== "none" ? ` + escudo ${b.armor === "light" ? "leve" : "pesado"}` : ""}
                </p>
                <p className="text-[11px] leading-[14px] text-fg-muted">{b.reason_pt}</p>
              </div>
            ))}
          </div>
          <p className={label}>Contingência</p>
          {(!prev || round.round_type === "pistol") && (
            <p className="text-xs leading-4 text-fg-muted">Round de pistol: a economia reinicia, então não há contingência do round anterior.</p>
          )}
          <div className={`grid grid-cols-2 gap-2 ${!prev || round.round_type === "pistol" ? "hidden" : ""}`}>
            {([["vencer", c.if_previous_won, prev ? baseWon : false], ["perder", c.if_previous_lost, prev ? !baseWon : false]] as const).map(([k, o, base]) => (
              <div key={k} className="rounded-sm border border-border bg-surface-raised/50 p-3">
                <p className={label}>Se {k} R{round.number - 1}{base ? " (base)" : ""}</p>
                <Badge tone={TYPE_TONE[o.round_type]} className="my-2">{ROUND_TYPE_PT[o.round_type]}</Badge>
                <p className="text-[11px] leading-[14px] text-fg-secondary">{o.summary_pt}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <p className={label}>Estratégia de {round.side === "attack" ? "ataque" : "defesa"} · {ROUND_TYPE_PT[round.round_type]}</p>
          <div className="flex items-stretch overflow-hidden rounded-md border border-border bg-surface">
            <div className="w-[3px] shrink-0 bg-violet" />
            <div className="flex flex-col gap-[6px] px-4 py-3">
              <span className="font-display text-xs font-semibold uppercase tracking-[0.96px] text-violet">Estratégia</span>
              <p className="text-sm leading-5 text-fg">{round.strategy.summary_pt}</p>
              {round.strategy.steps_pt.length > 0 && (
                <ul className="list-disc pl-4 text-sm text-fg-secondary">{round.strategy.steps_pt.map((s) => <li key={s}>{s}</li>)}</ul>
              )}
              <p className="font-mono text-xs text-fg-muted">
                {round.strategy.site ? `site ${round.strategy.site}` : ""}{round.strategy.timing ? ` · ${TIMING_PT[round.strategy.timing] ?? round.strategy.timing}` : ""} · vitória estimada {pct(round.win_probability.value)} · n = {round.win_probability.sample_size}
                {round.win_probability.low_sample ? " ⚠" : ""}
              </p>
            </div>
          </div>
          <p className={label}>Pontos fracos do adversário neste round</p>
          <div className="flex flex-col gap-3">
            {round.enemy_weak_points.length ? round.enemy_weak_points.map((i) => <InsightCard key={i.id} insight={i} />) : <p className="text-sm text-fg-muted">Sem dados suficientes.</p>}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <p className={label}>Movimento provável do adversário</p>
          <MinimapCanvas
            map={plan.map}
            size={260}
            routes={round.enemy_probable_strategy.route.length > 1 ? [{ points: round.enemy_probable_strategy.route, color: "#ffb547" }] : []}
          />
          <p className="text-xs leading-4 text-fg-secondary">
            {round.enemy_probable_strategy.summary_pt}
            <span className="ml-1 font-mono text-fg-muted">n = {round.enemy_probable_strategy.evidence.sample_size}{round.enemy_probable_strategy.evidence.low_sample ? " ⚠" : ""}</span>
          </p>
          {round.insights.map((i) => <InsightCard key={i.id} insight={i} />)}
        </div>
      </div>
    </Panel>
  );
}

const C = { cyan: "#2ee6d0", amber: "#ffb547", green: "#3ddc84", red: "#ff3b52", violet: "#a07bff" };
const ZONE_COLOR = { enemy_weak: C.green, danger: C.red, uncovered: C.cyan } as const;

/** Figma "Panel / Mapa tático do round" (32:432): the round's plan drawn on the minimap from real positions. */
function RoundMapPanel({ plan, round }: { plan: PlanResponse; round: RoundPlan }) {
  const [show, setShow] = useState({ mine: true, enemy: true, zones: true });
  const mp = round.map_plan;
  const attack = round.side === "attack";
  const routes = useMemo(() => (mp?.routes ?? []).filter((r) => (r.kind === "enemy" ? show.enemy : show.mine)).map((r) => ({
    points: r.points, arrow: true, dashed: r.kind !== "attack", width: r.role === "entry" ? 4 : 2.5,
    color: r.kind === "attack" ? C.cyan : r.kind === "retake" ? C.violet : C.amber, leader: r.kind === "attack",
    label: r.kind === "enemy" ? `${attack ? "Defesa" : "Ataque"} provável do inimigo · n = ${r.evidence.sample_size}` : r.kind === "attack" ? r.label : undefined,
  })), [mp, show.mine, show.enemy, attack]);
  const points = useMemo(() => (mp?.markers ?? []).filter((m) => m.kind === "site" || show.mine).map((m) => (
    m.kind === "site" ? { point: m.point, kind: "plant" as const, label: m.label } : { point: m.point, kind: "player" as const, team: "a" as const, label: m.label }
  )), [mp, show.mine]);
  const boxes = useMemo(() => (show.zones ? mp?.zones ?? [] : []).map((z) => ({ box: z.box, color: ZONE_COLOR[z.kind], label: z.label, below: z.kind === "uncovered" })), [mp, show.zones]);
  const mine = (mp?.routes ?? []).filter((r) => r.kind !== "enemy");
  const holds = (mp?.markers ?? []).filter((m) => m.kind === "hold");
  const retakeSite = round.enemy_probable_strategy.site;  // where the enemy is expected to plant: the retake arrows go there
  const empty = !mp || (!mp.routes.length && !mp.zones.length && !holds.length);
  type Row = [string, string, "line" | "dash" | "box" | "square"];
  const own: Row[] = attack
    ? [["Seta ciano: caminho típico de cada jogador do time (do início ao plante)", C.cyan, "line"]]
    : [["Círculo: posição típica de cada defensor nos primeiros 25 s", C.cyan, "square"], ["Tracejado violeta: retake do anchor/suporte até o plante", C.violet, "dash"]];
  const legend: Row[] = [
    ...own,
    ["Tracejado âmbar: rota provável do inimigo", C.amber, "dash"],
    ["Caixa verde: onde o inimigo perde as aberturas · vermelha: zona perigosa · ciano: zona descoberta", C.green, "box"],
    ["Quadrado âmbar: bombsite", C.amber, "square"],
  ];
  return (
    <Panel
      title="Mapa tático do round"
      subtitle={`Round ${round.number} · ${SIDE_PT[round.side]}${round.strategy.site ? ` · ${attack ? "alvo" : "reforço no"} site ${round.strategy.site}` : ""}${!attack && retakeSite && retakeSite !== round.strategy.site ? ` · inimigo provável no ${retakeSite}` : ""}: caminhos típicos calculados de posições reais (cada seta mostra a amostra)`}
      aside={
        <div className="flex gap-2">
          {([["mine", "Meu plano"], ["enemy", "Inimigo"], ["zones", "Zonas"]] as const).map(([k, l]) => (
            <FilterChip key={k} on={show[k]} onClick={() => setShow((s) => ({ ...s, [k]: !s[k] }))}>{l}</FilterChip>
          ))}
        </div>
      }
    >
      <div className="flex items-start gap-6">
        <MinimapCanvas map={plan.map} size={540} routes={routes} points={points} boxes={boxes} />
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {empty && <p className="text-sm text-fg-muted">Sem dados de posição suficientes para desenhar este round{mp?.note_pt ? `: ${mp.note_pt}` : "."}</p>}
          {!empty && (
            <>
              {mp?.note_pt && <p className="text-xs leading-4 text-amber">{mp.note_pt}</p>}
              <p className={label}>Legenda</p>
              <div className="flex flex-col gap-3">
                {legend.map(([txt, color, kind]) => (
                  <div key={txt} className="flex items-center gap-[10px] text-xs text-fg-secondary">
                    <span className="flex w-7 shrink-0 items-center justify-center">
                      {kind === "line" && <span className="h-[3px] w-7" style={{ background: color }} />}
                      {kind === "dash" && <span className="w-7 border-t-[2.5px] border-dashed" style={{ borderColor: color }} />}
                      {kind === "box" && <span className="h-[10px] w-7 border-[1.5px] border-dashed" style={{ borderColor: color, background: `${color}26` }} />}
                      {kind === "square" && <span className="size-[10px] rounded-[2px]" style={{ background: color }} />}
                    </span>
                    {txt}
                  </div>
                ))}
              </div>
              <p className={label}>{attack ? "Quem faz o quê neste round" : "Posições e retake neste round"}</p>
              <div className="flex flex-col gap-2">
                {(attack ? mine : holds.map((m) => {
                  const rt = mine.find((r) => r.kind === "retake" && r.handle === m.handle);  // anchors/support also have a retake arrow
                  return { label: rt ? `${m.label} · retake ${retakeSite ?? ""}`.trim() : m.label, handle: m.handle, evidence: rt?.evidence ?? null, t0_s: null, t1_s: null };
                })).map((r, i) => {
                  const why = round.strategy.steps_pt.find((s) => r.handle && s.startsWith(r.handle));
                  const ev = r.evidence;
                  return (
                    <div key={`${r.label}-${i}`} className="rounded-sm border border-border bg-surface-raised/50 px-3 py-2">
                      <p className="text-[13px] font-medium text-fg">{r.label}</p>
                      {why && <p className="text-[11px] leading-[14px] text-fg-secondary">{why}</p>}
                      {ev && (
                        <p className="font-mono text-[10px] text-fg-muted">
                          n = {ev.sample_size} posições{r.t0_s != null && r.t1_s != null ? ` · ${r.t0_s}–${r.t1_s} s` : ""}{ev.low_sample ? " ⚠" : ""}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-[11px] leading-[14px] text-fg-muted">
                Cada caminho junta os centros das posições dos jogadores por faixa de tempo (0–20, 20–40 e 40+ s), medidas nos momentos de abate dos rounds do time no mapa. São jogadas típicas, não prescrições; não há dados de utilitários.
              </p>
            </>
          )}
        </div>
      </div>
    </Panel>
  );
}

export default function ActionPlanPage() {
  const [params] = useSearchParams();
  const { data: meta } = useMeta();
  const { data: teams } = useTeams();
  const { data: maps } = useMaps();
  const plan = usePlan();
  const caps = usePlanCapabilities();
  const names = useMemo(() => (teams?.items ?? []).map((t) => t.team.name), [teams]);
  const [a, setA] = useState(params.get("teamA") ?? "");
  const [b, setB] = useState("");
  const [map, setMap] = useState("Ascent");
  const [rph, setRph] = useState(12);
  const [start, setStart] = useState<Side>("attack");
  const [persp, setPersp] = useState<"a" | "b">("a");
  const [shown, setShown] = useState<PlanResponse | undefined>();
  const [sel, setSel] = useState(1);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {  // sensible defaults once the team list is known
    if (!names.length) return;
    setA((x) => x || names[0]);
    setB((x) => x || names.find((n) => n !== (params.get("teamA") ?? names[0])) || names[1] || "");
  }, [names, params]);

  const run = (p: "a" | "b" = persp, over?: Partial<PlanRequest>) => {
    if (!a || !b) return;
    // react-query clears `plan.data` when a new request starts, which would unmount the whole page (and jump to the top)
    // while the narrative is written: keep the last plan on screen until the new one arrives
    plan.mutate({ team_a: a, team_b: b, map, perspective: p, rounds_per_half: rph, starting_side: start, ...over }, { onSuccess: setShown });
    setSel((s) => (over?.use_llm ? s : 1));  // rewriting the same plan keeps the selected round
  };
  useEffect(() => { if (a && b && !shown && !plan.isPending && !plan.isError) run(); }, [a, b]); // eslint-disable-line react-hooks/exhaustive-deps

  const info = (n: string) => teams?.items.find((t) => t.team.name === n);
  const sub = (n: string) => { const t = info(n); return t ? `${t.matches} partidas · ${pct(t.win_rate.value)}` : undefined; };
  const mapInfo = maps?.items.find((m) => m.map.name === map);
  const teamOpts: Array<[string, string]> = names.map((n) => [n, n]);
  /** Selects a round and brings its detail section into view (chips and table rows both use it). */
  const goToRound = (n: number) => {
    setSel(n);
    requestAnimationFrame(() => document.getElementById(ROUND_SECTION)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };
  const data = shown;
  const writing = plan.isPending && Boolean((plan.variables as PlanRequest | undefined)?.use_llm);
  const rounds = data?.rounds ?? [];
  const round = rounds.find((r) => r.number === sel) ?? rounds[0];
  const forTeam = data ? (data.perspective === "a" ? data.team_a.name : data.team_b.name) : persp === "a" ? a : b;
  const enemy = data ? (data.perspective === "a" ? data.team_b.name : data.team_a.name) : "";
  const half = (h: 1 | 2) => rounds.filter((r) => r.half === h);
  const sideOf = (h: 1 | 2) => half(h)[0]?.side;

  return (
    <>
      <PageHeader title="Plano de Ação" subtitle="Planejamento pré-partida com base em dados históricos. Escolha dois times e um mapa; o plano é gerado para a perspectiva selecionada." />

      <div className="flex items-stretch gap-3 rounded-md border border-border bg-surface p-5">
        <Picker title="Time A" value={a} sub={sub(a)} options={teamOpts} onChange={setA} ring="border-cyan" />
        <button onClick={() => { setA(b); setB(a); }} aria-label="Trocar times" className="shrink-0 self-center rounded-sm border border-border bg-surface-raised px-3 py-2 text-fg-secondary hover:text-fg">⇄</button>
        <Picker title="Time B (inimigo)" value={b} sub={sub(b)} options={teamOpts} onChange={setB} ring="border-amber" />
        <Picker title="Mapa" value={map} icon={(() => { const mr = meta?.maps.find((x) => x.name === map); return mr ? <MapIcon map={mr} /> : null; })()} sub={mapInfo ? `${mapInfo.matches} partidas` : undefined} options={(meta?.maps ?? [{ name: "Ascent" }]).map((m) => [m.name, m.name])} onChange={setMap} />
        <Picker title="Rodadas/tempo" value={String(rph)} sub={`${rph * 2} rounds`} options={[5, 6, 8, 10, 12].map((n) => [String(n), String(n)])} onChange={(v) => setRph(Number(v))} />
        <Picker title="Começa em" value={start} sub={`troca no round ${rph + 1}`} options={[["attack", "Ataque"], ["defense", "Defesa"]]} onChange={(v) => setStart(v as Side)} />
        <button onClick={() => run()} disabled={!a || !b || plan.isPending} className="shrink-0 self-center rounded-sm bg-accent px-6 py-3 font-display text-xs font-semibold uppercase tracking-[0.96px] text-on-accent hover:bg-accent-hover disabled:opacity-50">
          {plan.isPending ? "Gerando…" : "Gerar plano"}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className={label}>Plano para</span>
        {([["a", a], ["b", b]] as const).map(([p, n]) => (
          <button key={p} onClick={() => { setPersp(p); run(p); }} className={`rounded-sm border px-4 py-2 text-sm font-medium ${persp === p ? "border-accent bg-surface-accent text-fg" : "border-border bg-surface text-fg-secondary"}`}>{n || "—"}</button>
        ))}
        <span className="ml-auto text-[11px] text-fg-muted">
          {info(a) && info(b) ? `Base de dados: ${info(a)!.matches} partidas do time · ${info(b)!.matches} do adversário${mapInfo ? ` · ${mapInfo.matches} no mapa` : ""} · ` : ""}
          {data?.text_source === "llm" ? "texto reescrito por IA a partir dos fatos calculados" : "gerado por regras com evidências"}
        </span>
      </div>
      {data?.notes_pt && data.notes_pt.length > 0 && (
        <ul className="flex flex-col gap-1 text-[11px] leading-[14px] text-fg-muted">
          {data.notes_pt.map((n) => <li key={n}>• {n}</li>)}
        </ul>
      )}

      {plan.isError && <p className="text-accent">Não foi possível gerar o plano: {String(plan.error)}</p>}
      {plan.isPending && !data && <p className="text-fg-muted">Gerando plano…</p>}

      {data && round && (
        <>
          <div className="flex items-stretch gap-4">
            <Panel className="flex-1" title="Agentes recomendados" subtitle={`Composição sugerida para ${forTeam} em ${data.map.name}`}>
              <div className="grid grid-cols-5 gap-3">
                {data.agents.map((g) => (
                  <div key={g.agent.id} className="flex flex-col gap-2 rounded-sm border border-border bg-surface-raised/50 p-3">
                    <AgentIcon agent={g.agent} size={48} />
                    <p className="text-sm font-semibold text-fg">{g.agent.name ?? "Agente desconhecido"}</p>
                    {g.role && <Badge tone="red" className="self-start">{g.role}</Badge>}
                    <p className="text-[11px] leading-[14px] text-fg-muted">{g.reason_pt} · n = {g.evidence.sample_size}{g.evidence.low_sample ? " ⚠" : ""}</p>
                  </div>
                ))}
                {data.agents.length === 0 && <p className="text-sm text-fg-muted">Sem histórico suficiente neste mapa.</p>}
              </div>
            </Panel>
            <Panel className="w-[340px] shrink-0" title="Perfil do adversário" subtitle={`${enemy} em ${data.map.name}`}>
              <div className="flex flex-col text-sm">
                {([
                  ["Site preferido no ataque", data.opponent.preferred_site ?? "—", "text-fg"],
                  ["Tempo médio até o plante", seconds(data.opponent.avg_time_to_plant_ms.value), "text-fg"],
                  ["Vitória no ataque", pct(data.opponent.attack_win_rate.value), "text-fg"],
                  ["Vitória na defesa", pct(data.opponent.defense_win_rate.value), "text-accent"],
                  ["Pistol rounds vencidos", pct(data.opponent.pistol_win_rate.value), "text-accent"],
                  ["Rounds de eco", pct(data.opponent.eco_win_rate.value), "text-amber"],
                ] as const).map(([l, v, c]) => (
                  <div key={l} className="flex justify-between border-b border-border py-3"><span className="text-fg-secondary">{l}</span><span className={`${mono} ${c}`}>{v}</span></div>
                ))}
              </div>
              {data.opponent.insights.map((i) => <InsightCard key={i.id} insight={i} />)}
            </Panel>
          </div>

          <Panel
            title="Linha do tempo da partida"
            subtitle={`Plano para ${forTeam} · cenário base: o resultado mais provável de cada round`}
            aside={<div className="flex gap-2">{(["pistol", "eco", "semi_eco", "force", "full_buy"] as RoundType[]).map((t) => <Badge key={t} tone={TYPE_TONE[t]}>{ROUND_TYPE_PT[t]}</Badge>)}</div>}
          >
            {([1, 2] as const).map((h) => half(h).length > 0 && (
              <div key={h} className="flex flex-col gap-2">
                <p className={label}>
                  {h}º tempo · {forTeam} {sideOf(h) === "attack" ? "ataca" : "defende"}
                  {h === 2 && ` · rounds ${half(2)[0].number}–${rounds[rounds.length - 1].number} (pistol no round ${half(2)[0].number})`}
                </p>
                <div className="flex flex-wrap gap-2">
                  {half(h).map((r) => <RoundChip key={r.number} r={r} selected={r.number === round.number} onClick={() => goToRound(r.number)} />)}
                </div>
              </div>
            ))}
            <p className="text-[11px] text-fg-muted">Ponto verde = vitória no cenário base · ponto vermelho = derrota. O tipo de cada round muda conforme o resultado: veja a contingência no detalhe do round.</p>
          </Panel>

          <div id={ROUND_SECTION} className="scroll-mt-20">
            <RoundDetail plan={data} round={round} prev={rounds.find((r) => r.number === round.number - 1)} />
          </div>
          <RoundMapPanel plan={data} round={round} />

          <Panel title="Plano completo" subtitle="Um registro por round · base para leitura rápida e exportação">
            <DataTable
              rows={showAll ? rounds : rounds.slice(0, 8)}
              rowKey={(r) => String(r.number)}
              onRowClick={(r) => goToRound(r.number)}
              columns={[
                { key: "n", header: "Rd", width: 32, className: `${mono} text-fg-muted`, render: (r) => r.number },
                { key: "s", header: "Lado", width: 50, className: `font-display text-xs font-semibold ${""}`, render: (r) => <span className={r.side === "attack" ? "text-accent" : "text-violet"}>{SIDE_SHORT[r.side]}</span> },
                { key: "t", header: "Tipo", width: 80, render: (r) => <Badge tone={TYPE_TONE[r.round_type]}>{TYPE_SHORT[r.round_type]}</Badge> },
                { key: "b", header: "Compra recomendada", width: 220, render: (r) => <BuyIcons r={r} /> },
                { key: "p", header: "Plano resumido", render: (r) => r.strategy.summary_pt },
                { key: "e", header: "Movimento provável do inimigo", width: 230, render: (r) => r.enemy_probable_strategy.summary_pt },
                { key: "w", header: "Base", width: 40, align: "center", render: (r) => <span className={`size-2 rounded-full ${r.base_scenario_result === "win" ? "bg-green" : "bg-accent"}`} /> },
              ]}
            />
            {rounds.length > 8 && (
              <button onClick={() => setShowAll(!showAll)} className="self-start rounded-sm border border-border bg-surface-raised px-4 py-2 font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-secondary hover:text-fg">
                {showAll ? "Mostrar menos" : `Mostrar rounds 9–${rounds.length}`}
              </button>
            )}
          </Panel>

          <div className="flex items-center gap-4 rounded-md border border-border bg-surface p-5">
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-base font-semibold text-fg">Narrativa de treinador (opcional)</h2>
              <p className="text-xs leading-4 text-fg-muted">Reescreve o plano em linguagem natural usando apenas os fatos e números acima. O plano estruturado continua visível.</p>
              {writing && <p className="mt-2 text-xs leading-4 text-cyan">Escrevendo a narrativa com IA… pode levar de 1 a 2 minutos; o plano abaixo continua disponível.</p>}
              {!writing && (data.notes_pt ?? []).filter((n) => n.startsWith("Narrativa por IA")).map((n) => <p key={n} className="mt-2 text-xs leading-4 text-amber">{n}</p>)}
              {plan.isError && <p className="mt-2 text-xs leading-4 text-accent">Não foi possível gerar a narrativa: {String(plan.error)}</p>}
              {data.narrative_pt && <p className="mt-3 whitespace-pre-line text-sm leading-5 text-fg-secondary">{data.narrative_pt}</p>}
            </div>
            <button
              onClick={() => run(data.perspective, { use_llm: true })}
              disabled={!caps.data?.llm || plan.isPending || data.text_source === "llm"}
              title={data.text_source === "llm" ? "Plano já reescrito" : caps.data?.llm ? "Reescrever o plano com IA, usando só os fatos acima" : "Narrativa desativada neste ambiente (defina GEMINI_API_KEY no arquivo .env do servidor)"}
              className={`rounded-sm border border-border bg-surface-raised px-4 py-2 font-display text-xs font-semibold uppercase tracking-[0.96px] ${caps.data?.llm && data.text_source !== "llm" ? "text-fg-secondary hover:text-fg" : "text-fg-muted opacity-60"}`}
            >
              {writing ? "Escrevendo…" : "Gerar narrativa"}
            </button>
            <button onClick={() => window.print()} className="rounded-sm border border-border bg-surface-raised px-4 py-2 font-display text-xs font-semibold uppercase tracking-[0.96px] text-fg-secondary hover:text-fg">Exportar PDF</button>
          </div>
        </>
      )}
      {!data && !plan.isPending && !plan.isError && <p className="text-fg-muted">Escolha os times e clique em “Gerar plano”.</p>}
    </>
  );
}
