// App shell and routes (Figma "Screen / *": sidebar + top bar + content). Owner: Stream E; each page file is owned by its stream.
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import ActionPlanPage from "@/pages/ActionPlanPage";
import HomePage from "@/pages/HomePage";
import { MapsListPage, MatchesListPage, PlayersListPage, TeamsListPage } from "@/pages/ListPages";
import MapPage from "@/pages/MapPage";
import MatchPage from "@/pages/MatchPage";
import PlayerPage from "@/pages/PlayerPage";
import TeamPage from "@/pages/TeamPage";

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex flex-col gap-6 p-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/jogadores" element={<PlayersListPage />} />
            <Route path="/times" element={<TeamsListPage />} />
            <Route path="/mapas" element={<MapsListPage />} />
            <Route path="/partidas" element={<MatchesListPage />} />
            <Route path="/jogador/:puuid" element={<PlayerPage />} />
            <Route path="/time/:teamName" element={<TeamPage />} />
            <Route path="/mapa/:mapName" element={<MapPage />} />
            <Route path="/partida/:matchId" element={<MatchPage />} />
            <Route path="/plano" element={<ActionPlanPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
