// Interim Home: KPIs, search and leaderboards so every profile is reachable. Owner: Stream E (will replace/restyle).
import { useState } from "react";
import { Link } from "react-router-dom";
import { useLeaderboards, useMeta, useSearch } from "@/api/hooks";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatCard } from "@/components/ui/StatCard";
import { num, pct } from "@/lib/format";

const link = "text-cyan hover:underline";

export default function HomePage() {
  const { data, isLoading, error } = useMeta();
  const [q, setQ] = useState("");
  const search = useSearch(q);
  const boards = useLeaderboards();

  return (
    <>
      <PageHeader title="Visão geral" subtitle="Busca, KPIs e rankings (versão provisória)" />
      {isLoading && <p className="text-fg-muted">Carregando…</p>}
      {error && <p className="text-accent">Erro: {String(error)}</p>}
      {data && (
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-6">
          <StatCard label="Partidas" value={String(data.kpis.matches)} />
          <StatCard label="Rounds" value={String(data.kpis.rounds)} />
          <StatCard label="Kills" value={String(data.kpis.kills)} />
          <StatCard label="Jogadores" value={String(data.kpis.players)} />
          <StatCard label="Times" value={String(data.kpis.teams)} />
          <StatCard label="Torneios" value={String(data.kpis.tournaments)} />
        </div>
      )}

      <div className="space-y-4">
        <Panel title="Buscar jogador, time ou mapa">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Digite um Riot ID, time ou mapa…"
            className="w-full border border-border bg-bg-app px-3 py-2 text-sm text-fg"
          />
          {search.data && (
            <div className="mt-3 grid gap-4 md:grid-cols-3 text-sm">
              <ul className="space-y-1">
                {search.data.players.map((p) => (
                  <li key={p.player.puuid}><Link className={link} to={`/jogador/${p.player.puuid}`}>{p.player.riot_id}</Link> <span className="text-fg-muted">{p.team?.name}</span></li>
                ))}
              </ul>
              <ul className="space-y-1">
                {search.data.teams.map((t) => (
                  <li key={t.team.name}><Link className={link} to={`/time/${encodeURIComponent(t.team.name)}`}>{t.team.name}</Link></li>
                ))}
              </ul>
              <ul className="space-y-1">
                {search.data.maps.map((m) => (
                  <li key={m.map.name}><Link className={link} to={`/mapa/${m.map.name}`}>{m.map.name}</Link></li>
                ))}
              </ul>
            </div>
          )}
        </Panel>

        {boards.data && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Melhores jogadores (K/D)">
              <ol className="space-y-1 text-sm">
                {boards.data.players.kd.map((r) => (
                  <li key={r.player.puuid} className="flex justify-between">
                    <span><span className="mr-2 text-fg-muted">{r.rank}</span><Link className={link} to={`/jogador/${r.player.puuid}`}>{r.player.riot_id}</Link> <span className="text-fg-muted">{r.team?.name}</span></span>
                    <span className="font-mono">{num(r.value)} <span className="text-xs text-fg-muted">n={r.rounds}</span></span>
                  </li>
                ))}
              </ol>
            </Panel>
            <Panel title="Melhores times (% de rounds)">
              <ol className="space-y-1 text-sm">
                {boards.data.teams.round_win_rate.map((r) => (
                  <li key={r.team.name} className="flex justify-between">
                    <span><span className="mr-2 text-fg-muted">{r.rank}</span><Link className={link} to={`/time/${encodeURIComponent(r.team.name)}`}>{r.team.name}</Link></span>
                    <span className="font-mono">{pct(r.value)} <span className="text-xs text-fg-muted">n={r.rounds}</span></span>
                  </li>
                ))}
              </ol>
            </Panel>
          </div>
        )}
      </div>
    </>
  );
}
