// App shell and routes. Owner: Stream E (one route per screen; each page file is owned by its stream).
import { NavLink, Route, Routes } from "react-router-dom";
import ActionPlanPage from "@/pages/ActionPlanPage";
import HomePage from "@/pages/HomePage";
import MapPage from "@/pages/MapPage";
import MatchPage from "@/pages/MatchPage";
import PlayerPage from "@/pages/PlayerPage";
import TeamPage from "@/pages/TeamPage";

const NAV = [
  { to: "/", label: "Visão geral" },
  { to: "/mapa/Ascent", label: "Mapas" },
  { to: "/plano", label: "Plano de ação" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <nav className="w-56 shrink-0 border-r border-border bg-bg-nav p-4">
        <p className="mb-6 font-display text-xl font-bold uppercase tracking-widest text-accent">Spike Lab</p>
        <ul className="space-y-1">
          {NAV.map((n) => (
            <li key={n.to}>
              <NavLink
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `block px-3 py-2 text-sm ${isActive ? "bg-surface-accent text-fg" : "text-fg-secondary hover:text-fg"}`
                }
              >
                {n.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main className="min-w-0 flex-1 p-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/jogador/:puuid" element={<PlayerPage />} />
          <Route path="/time/:teamName" element={<TeamPage />} />
          <Route path="/mapa/:mapName" element={<MapPage />} />
          <Route path="/partida/:matchId" element={<MatchPage />} />
          <Route path="/plano" element={<ActionPlanPage />} />
        </Routes>
      </main>
    </div>
  );
}
