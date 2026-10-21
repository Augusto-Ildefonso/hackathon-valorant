// Player Profile (/jogador/:puuid). Owner: Stream B.
import { Link, useParams } from "react-router-dom";
import { usePlayer } from "@/api/hooks";
import type { RoleScore } from "@/api/types";
import { AgentIcon, WeaponIcon } from "@/components/ui/AgentIcon";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { InsightList } from "@/components/ui/InsightList";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel, StatValue } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { ROLE_PT, ROUND_TYPE_PT, SIGNAL_PT, num, pct, statNum } from "@/lib/format";

function RoleCard({ role }: { role: RoleScore }) {
  return (
    <div className="border border-border bg-surface-raised p-3">
      <p className="font-display text-lg text-fg">
        {ROLE_PT[role.role]}
        {role.inferred && <span className="ml-2 text-xs text-amber">inferido</span>}
      </p>
      <p className="mt-1 font-mono text-sm text-fg-secondary">
        pontuação {pct(role.score)} · confiança {pct(role.confidence)}
      </p>
      <ul className="mt-2 space-y-0.5 text-xs text-fg-muted">
        {role.signals.map((s) => (
          <li key={s.name}>
            {SIGNAL_PT[s.name] ?? s.name}: <span className="font-mono text-fg-secondary">{num(s.value, 2)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function PlayerPage() {
  const { puuid = "" } = useParams();
  const { data, isLoading, error } = usePlayer(puuid);

  if (isLoading) return <p className="text-fg-muted">Carregando…</p>;
  if (error || !data) return <EmptyState title="Jogador não encontrado" message={String(error ?? "")} />;
  const { stats } = data;

  return (
    <>
      <PageHeader
        title={data.player.riot_id}
        subtitle={data.teams.map((t) => t.name).join(" · ") || undefined}
        actions={data.favorite_agent && <AgentIcon agent={data.favorite_agent} size={48} showName />}
      />
      <div className="mb-3 flex flex-wrap gap-2 text-sm">
        {data.teams.map((t) => (
          <Link key={t.name} to={`/time/${encodeURIComponent(t.name)}`} className="border border-border px-2 py-1 text-cyan hover:bg-surface-raised">
            {t.name}
          </Link>
        ))}
      </div>

      <div className="space-y-4">
        <Panel title="Funções (comportamento)">
          {data.roles.length ? (
            <div className="grid gap-3 md:grid-cols-2">{data.roles.map((r) => <RoleCard key={r.role} role={r} />)}</div>
          ) : (
            <p className="text-sm text-fg-muted">Sem dados suficientes.</p>
          )}
          <p className="mt-2 text-xs text-fg-muted">
            Calculada pelo comportamento em jogo (duelos de abertura, distância do time, assistências, presença no site), nunca só pelo agente.
          </p>
        </Panel>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          <StatCard label="Partidas" value={String(stats.matches)} />
          <StatCard label="Rounds" value={String(stats.rounds)} />
          <StatCard label="K/D" stat={stats.kd} format={(v) => num(v)} />
          <StatCard label="ADR" stat={stats.adr} format={(v) => num(v, 1)} />
          <StatCard label="HS%" stat={stats.hs_pct} format={(v) => pct(v)} />
          <StatCard label="Abertura (vitória)" stat={stats.opening_duel_win_pct} format={(v) => pct(v)} />
          <StatCard label="First kill / round" stat={stats.first_kill_rate} format={(v) => pct(v, 1)} />
          <StatCard label="First death / round" stat={stats.first_death_rate} format={(v) => pct(v, 1)} />
          <StatCard label="Kills / Mortes / Assist." value={`${stats.kills} / ${stats.deaths} / ${stats.assists}`} />
          <StatCard label="Clutches vencidos" value={String(stats.clutches)} />
          <StatCard label="Multi-kills" value={`${stats.multikills.k2}×2K ${stats.multikills.k3}×3K ${stats.multikills.k4}×4K ${stats.multikills.k5}×5K`} />
        </div>

        <Panel title="Desempenho por arma comprada">
          <DataTable
            rows={data.weapons}
            rowKey={(w) => `${w.weapon.id}-${w.buy_type}`}
            emptyText="Poucos rounds por arma para exibir."
            columns={[
              { key: "w", header: "Arma", render: (w) => <WeaponIcon weapon={w.weapon} size={22} showName /> },
              { key: "b", header: "Compra", render: (w) => (w.buy_type ? ROUND_TYPE_PT[w.buy_type] : "Todas") },
              { key: "r", header: "Rounds", align: "right", render: (w) => w.rounds },
              { key: "v", header: "Vitórias", align: "right", render: (w) => <StatValue stat={w.round_win_rate} format={(v) => pct(v)} /> },
              { key: "k", header: "Kills", align: "right", render: (w) => w.kills },
              { key: "kd", header: "K/D", align: "right", render: (w) => statNum(w.kd) },
              { key: "hs", header: "HS%", align: "right", render: (w) => <StatValue stat={w.hs_pct} format={(v) => pct(v)} /> },
              { key: "d", header: "Dano/round", align: "right", render: (w) => statNum(w.damage_per_round, 0) },
            ]}
          />
        </Panel>

        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Kills e mortes por mapa">
            <DataTable
              rows={data.by_map}
              rowKey={(m) => m.map.codename}
              columns={[
                { key: "m", header: "Mapa", render: (m) => <Link className="text-cyan hover:underline" to={`/mapa/${m.map.name}`}>{m.map.name}</Link> },
                { key: "n", header: "Partidas", align: "right", render: (m) => m.matches },
                { key: "k", header: "Kills", align: "right", render: (m) => m.kills },
                { key: "d", header: "Mortes", align: "right", render: (m) => m.deaths },
                { key: "kd", header: "K/D", align: "right", render: (m) => <StatValue stat={m.kd} format={(v) => num(v)} /> },
              ]}
            />
          </Panel>
          <Panel title="Agentes jogados">
            <DataTable
              rows={data.agents}
              rowKey={(a) => a.agent.id}
              columns={[
                { key: "a", header: "Agente", render: (a) => <AgentIcon agent={a.agent} size={24} showName /> },
                { key: "n", header: "Partidas", align: "right", render: (a) => a.matches },
                { key: "kd", header: "K/D", align: "right", render: (a) => num(a.kd.value) },
                { key: "adr", header: "ADR", align: "right", render: (a) => num(a.adr.value, 0) },
                { key: "w", header: "Vitórias", align: "right", render: (a) => <StatValue stat={a.win_rate} format={(v) => pct(v)} /> },
              ]}
            />
          </Panel>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Panel title="Pontos fortes"><InsightList insights={data.insights} kinds={["strength"]} /></Panel>
          <Panel title="Pontos fracos"><InsightList insights={data.insights} kinds={["weakness"]} /></Panel>
          <Panel title="Recomendações de treino"><InsightList insights={data.insights} kinds={["tip"]} /></Panel>
        </div>
      </div>
    </>
  );
}
