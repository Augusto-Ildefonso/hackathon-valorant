// App shell and routes (Figma "Screen / *": sidebar + top bar + content). Owner: Stream E; each page file is owned by its stream.
import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import ActionPlanPage from "@/pages/ActionPlanPage";
import ChatPage from "@/pages/ChatPage";
import HomePage from "@/pages/HomePage";
import { MapsListPage, MatchesListPage, PlayersListPage, TeamsListPage } from "@/pages/ListPages";
import MapPage from "@/pages/MapPage";
import MatchPage from "@/pages/MatchPage";
import PlayerPage from "@/pages/PlayerPage";
import TeamPage from "@/pages/TeamPage";

export default function App() {
  const [menu, setMenu] = useState(false);
  return (
    <div className="flex min-h-screen">
      <Sidebar open={menu} onClose={() => setMenu(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMenu(true)} />
        <main className="flex flex-col gap-4 p-4 sm:p-6 lg:gap-6 lg:p-8">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/campeonatos" element={<HomePage />} />
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
