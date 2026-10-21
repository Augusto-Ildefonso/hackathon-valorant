// Team Profile (/time/:teamName). Owner: Stream B.
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTeam } from "@/api/hooks";
import type { RoundType, TrendPoint } from "@/api/types";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InsightList } from "@/components/ui/InsightList";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel, StatValue } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { ROLE_PT, ROUND_TYPE_PT, dateBR, pct, seconds } from "@/lib/format";

/** Round difference per match, oldest to newest (green = won the map, red = lost). */
function TrendChart({ points }: { points: TrendPoint[] }) {
  const w = 520, h = 140, mid = h / 2;
  const max = Math.max(13, ...points.map((p) => Math.abs(p.round_diff)));
  const bw = Math.max(4, Math.min(24, (w - 20) / Math.max(points.length, 1) - 2));
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Diferença de rounds por partida">
      <line x1="0" x2={w} y1={mid} y2={mid} stroke="var(--color-border-strong)" />
      {points.map((p, i) => {
        const bh = (Math.abs(p.round_diff) / max) * (mid - 6);
        const x = 10 + i * ((w - 20) / Math.max(points.length, 1));
        return (
          <rect key={p.match_id} x={x} width={bw} y={p.round_diff >= 0 ? mid - bh : mid} height={Math.max(bh, 1)}
            fill={p.round_diff > 0 ? "var(--color-green)" : "var(--color-accent)"}>
            <title>{`${dateBR(p.date)}: ${p.round_diff > 0 ? "+" : ""}${p.round_diff} rounds`}</title>
          </rect>
        );
      })}
    </svg>
  );
}

const RT_ORDER: RoundType[] = ["pistol", "eco", "semi_eco", "force", "full_buy"];

export default function TeamPage() {
  const { teamName = "" } = useParams();
  const navigate = useNavigate();
  const { data, isLoading, error } = useTeam(teamName);

  if (isLoading) return <p className="text-fg-muted">Carregando…</p>;
  if (error || !data) return <EmptyState title="Time não encontrado" message={String(error ?? "")} />;
  const { record, economy } = data;

  return (
    <>
      <PageHeader title={data.team.name} subtitle={`${record.matches} partidas · ${record.series} séries · ${record.wins}V ${record.losses}D`} />
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          <StatCard label="Partidas" value={String(record.matches)} />
          <StatCard label="Séries" value={String(record.series)} />
          <StatCard label="Vitórias / Derrotas" value={`${record.wins} / ${record.losses}`} />
          <StatCard label="Rounds vencidos" stat={record.round_win_rate} format={(v) => pct(v)} />
          <StatCard label="Ataque" stat={record.attack_win_rate} format={(v) => pct(v)} />
          <StatCard label="Defesa" stat={record.defense_win_rate} format={(v) => pct(v)} />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Elenco">
            <DataTable
              rows={data.roster}
              rowKey={(m) => m.player.puuid}
              columns={[
                { key: "p", header: "Jogador", render: (m) => <Link className="text-cyan hover:underline" to={`/jogador/${m.player.puuid}`}>{m.player.riot_id}</Link> },
                { key: "n", header: "Partidas", align: "right", render: (m) => m.matches },
                { key: "r", header: "Função", render: (m) => (m.top_role ? `${ROLE_PT[m.top_role.role]} (${pct(m.top_role.confidence)})` : "—") },
              ]}
            />
            {data.role_composition.length > 0 && (
              <p className="mt-3 text-sm text-fg-secondary">
                Composição atual:{" "}
                {data.role_composition.map((r) => `${r.count}× ${ROLE_PT[r.role]}`).join(" · ")}
              </p>
            )}
          </Panel>
          <Panel title="Tendência (diferença de rounds por partida)">
            <TrendChart points={data.trend} />
          </Panel>
        </div>

        <Panel title="Desempenho por mapa">
          <DataTable
            rows={data.by_map}
            rowKey={(m) => m.map.codename}
            columns={[
              { key: "m", header: "Mapa", render: (m) => <Link className="text-cyan hover:underline" to={`/mapa/${m.map.name}`}>{m.map.name}</Link> },
              { key: "n", header: "Partidas", align: "right", render: (m) => m.matches },
              { key: "w", header: "Vitórias", align: "right", render: (m) => <StatValue stat={m.win_rate} format={(v) => pct(v)} /> },
              { key: "a", header: "Ataque", align: "right", render: (m) => <StatValue stat={m.attack_win_rate} format={(v) => pct(v)} /> },
              { key: "d", header: "Defesa", align: "right", render: (m) => <StatValue stat={m.defense_win_rate} format={(v) => pct(v)} /> },
            ]}
          />
        </Panel>

        <Panel title="Economia e tendências">
          <div className="grid gap-4 lg:grid-cols-2">
            <DataTable
              rows={RT_ORDER}
              rowKey={(t) => t}
              columns={[
                { key: "t", header: "Tipo de round", render: (t) => ROUND_TYPE_PT[t] },
                { key: "w", header: "Vitórias", align: "right", render: (t) => <StatValue stat={economy.win_rate_by_round_type[t]} format={(v) => pct(v)} /> },
              ]}
            />
            <ul className="space-y-1 text-sm text-fg-secondary">
              <li>Pistol: <StatValue stat={economy.pistol_win_rate} format={(v) => pct(v)} /></li>
              <li>Tempo até plantar: <StatValue stat={economy.avg_time_to_plant_ms} format={seconds} /></li>
              <li>Vitória pós-plant: <StatValue stat={economy.post_plant_win_rate} format={(v) => pct(v)} /></li>
              <li>Retomada de site (defesa): <StatValue stat={economy.retake_success_rate} format={(v) => pct(v)} /></li>
              {Object.entries(economy.plant_site_preference).map(([site, st]) => (
                <li key={site}>Plant no site {site}: <StatValue stat={st} format={(v) => pct(v)} /></li>
              ))}
            </ul>
          </div>
        </Panel>

        <Panel title="Partidas">
          <DataTable
            rows={data.matches}
            rowKey={(m) => m.match_id}
            onRowClick={(m) => navigate(`/partida/${m.match_id}`)}
            columns={[
              { key: "d", header: "Data", render: (m) => dateBR(m.date) },
              { key: "m", header: "Mapa", render: (m) => m.map.name },
              { key: "o", header: "Confronto", render: (m) => `${m.team_a.team.name} ${m.team_a.score} x ${m.team_b.score} ${m.team_b.team.name}` },
              { key: "t", header: "Torneio", render: (m) => m.tournament },
              { key: "r", header: "Resultado", render: (m) => {
                const mine = m.team_a.team.name === data.team.name ? "a" : "b";
                return <span className={m.winner === mine ? "text-green" : "text-accent"}>{m.winner === mine ? "Vitória" : "Derrota"}</span>;
              } },
            ]}
          />
        </Panel>

        <div className="grid gap-4 lg:grid-cols-3">
          <Panel title="Pontos fortes"><InsightList insights={data.insights} kinds={["strength"]} /></Panel>
          <Panel title="Pontos fracos"><InsightList insights={data.insights} kinds={["weakness"]} /></Panel>
          <Panel title="Sugestões de melhoria"><InsightList insights={data.insights} kinds={["tip", "strategy"]} /></Panel>
        </div>
      </div>
    </>
  );
}
