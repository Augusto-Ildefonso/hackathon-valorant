// Figma "Sidebar" (24:48) with "Nav Item" states. Owner: Stream E.
import { Link, useLocation } from "react-router-dom";

// `match` = path prefixes that keep the item highlighted (detail screens belong to their list entry)
const NAV = [
  { to: "/", label: "Início", match: [] as string[] },
  { to: "/jogadores", label: "Jogadores", match: ["/jogadores", "/jogador/"] },
  { to: "/times", label: "Times", match: ["/times", "/time/"] },
  { to: "/mapas", label: "Mapas", match: ["/mapas", "/mapa/"] },
  { to: "/partidas", label: "Partidas", match: ["/partidas", "/partida/"] },
  { to: "/plano", label: "Plano de Ação", match: ["/plano"] },
];

export function Sidebar() {
  const { pathname } = useLocation();
  return (
    <nav className="sticky top-0 flex h-screen w-60 shrink-0 flex-col gap-1 border-r border-border bg-bg-nav px-3 py-5">
      <div className="flex items-center gap-[10px] p-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-accent font-display text-base font-semibold text-on-accent">V</div>
        <span className="font-display text-base font-semibold tracking-[0.96px] text-fg">VAVÁGYM</span>
      </div>
      <div className="h-3" />
      {NAV.map((n) => {
        const active = n.to === "/" ? pathname === "/" : n.match.some((m) => pathname.startsWith(m));
        return (
          <Link
            key={n.to}
            to={n.to}
            className={`flex h-10 items-center gap-3 rounded-sm px-4 text-sm font-medium ${active ? "bg-surface-accent text-fg" : "text-fg-secondary hover:text-fg"}`}
          >
            <span className={`h-4 w-[3px] ${active ? "bg-accent" : "bg-transparent"}`} />
            {n.label}
          </Link>
        );
      })}
      <div className="flex-1" />
      <p className="text-[11px] font-medium leading-[14px] text-fg-muted">
        Dados: Rush Series · Univavá
        <br />
        Análise pós-partida
      </p>
    </nav>
  );
}
