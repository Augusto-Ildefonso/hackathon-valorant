// react-query hooks, one per endpoint. Owner: Stream E (add hooks here via one-line PR; pages call only these).
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Query } from "./client";
import type {
  HeatmapResponse, KillsResponse, LeaderboardsResponse, MapListResponse, MapProfile, MatchListResponse,
  MatchReport, MetaResponse, PlanRequest, PlanResponse, PlayerProfile, SearchResponse, TeamListResponse, TeamProfile,
} from "./types";

const useGet = <T,>(key: unknown[], path: string, query?: Query, enabled = true) =>
  useQuery({ queryKey: [...key, query], queryFn: () => api<T>(path, { query }), enabled });

export const useMeta = () => useGet<MetaResponse>(["meta"], "/api/meta");
export const useSearch = (q: string) => useGet<SearchResponse>(["search", q], "/api/search", { q }, q.trim().length > 1);
export const useLeaderboards = (query?: Query) => useGet<LeaderboardsResponse>(["leaderboards"], "/api/leaderboards", query);
export const useMatches = (query?: Query) => useGet<MatchListResponse>(["matches"], "/api/matches", query);
export const usePlayer = (puuid: string, query?: Query) => useGet<PlayerProfile>(["player", puuid], `/api/players/${puuid}`, query);
export const useTeams = (query?: Query) => useGet<TeamListResponse>(["teams"], "/api/teams", query);
export const useTeam = (name: string, query?: Query) =>
  useGet<TeamProfile>(["team", name], `/api/teams/${encodeURIComponent(name)}`, query);
export const useMaps = (query?: Query) => useGet<MapListResponse>(["maps"], "/api/maps", query);
export const useMap = (name: string, query?: Query) => useGet<MapProfile>(["map", name], `/api/maps/${encodeURIComponent(name)}`, query);
export const useHeatmap = (name: string, query?: Query) =>
  useGet<HeatmapResponse>(["heatmap", name], `/api/maps/${encodeURIComponent(name)}/heatmap`, query);
export const useMatch = (id: string) => useGet<MatchReport>(["match", id], `/api/matches/${id}`);
export const useMatchKills = (id: string, query?: Query) => useGet<KillsResponse>(["kills", id], `/api/matches/${id}/kills`, query);
export const usePlan = () =>
  useMutation({ mutationFn: (body: PlanRequest) => api<PlanResponse>("/api/plan", { body }) });
