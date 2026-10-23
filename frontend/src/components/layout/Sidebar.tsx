// Figma "Sidebar" (24:48) with "Nav Item" states. Owner: Stream E.
// Desktop (lg+): fixed column. Phone: a drawer opened from the top bar button (closes on navigation, backdrop tap or Esc).
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Logo } from "../ui/Logo";

// `match` = path prefixes that keep the item highlighted (detail screens belong to their list entry)
const NAV = [
  { to: "/", label: "Início", match: [] as string[] },
  { to: "/campeonatos", label: "Campeonatos", match: ["/campeonatos"] },
  { to: "/jogadores", label: "Jogadores", match: ["/jogadores", "/jogador/"] },
  { to: "/times", label: "Times", match: ["/times", "/time/"] },
  { to: "/mapas", label: "Mapas", match: ["/mapas", "/mapa/"] },
  { to: "/partidas", label: "Partidas", match: ["/partidas", "/partida/"] },
  { to: "/plano", label: "Plano de Ação", match: ["/plano"] },
];

export function Sidebar({ open = false, onClose }: { open?: boolean; onClose?: () => void }) {
  const { pathname } = useLocation();
  useEffect(() => { onClose?.(); }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [open, onClose]);
  return (
    <>
      {open && <button aria-label="Fechar menu" onClick={onClose} className="fixed inset-0 z-30 bg-black/60 lg:hidden" />}
      <nav
        aria-label="Menu principal"
        className={`${open ? "flex" : "hidden"} fixed inset-y-0 left-0 z-40 w-64 shrink-0 flex-col gap-1 overflow-y-auto border-r border-border bg-bg-nav px-3 py-5 lg:sticky lg:top-0 lg:z-auto lg:flex lg:h-screen lg:w-60`}
      >
        <div className="flex items-center gap-[10px] p-3">
          <Logo size={32} />
          <span className="font-display text-base font-semibold tracking-[0.96px] text-fg">VAVÁGYM</span>
        </div>
        <div className="h-3" />
        {NAV.map((n) => {
          const active = n.to === "/" ? pathname === "/" : n.match.some((m) => pathname.startsWith(m));
          return (
            <Link
              key={n.to}
              to={n.to}
              className={`flex h-11 shrink-0 items-center gap-3 rounded-sm px-4 text-sm font-medium lg:h-10 ${active ? "bg-surface-accent text-fg" : "text-fg-secondary hover:text-fg"}`}
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
    </>
  );
}
