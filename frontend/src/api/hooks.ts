// react-query hooks, one per endpoint; global filters (tournament / map / period) are applied where the API supports
// them. Owner: Stream E (add hooks here via one-line PR; pages call only these).
import { useMutation, useQuery } from "@tanstack/react-query";
import { filterQuery, useFilters } from "@/lib/filters";
import { api, type Query } from "./client";
import type {
  HeatmapResponse, KillsResponse, LeaderboardsResponse, MapListResponse, MapProfile, MatchListResponse,
  MatchReport, MetaResponse, PlanRequest, PlanResponse, PlayerProfile, SearchResponse, TeamListResponse, TeamProfile,
} from "./types";

const useGet = <T,>(key: unknown[], path: string, query?: Query, enabled = true) =>
  useQuery({ queryKey: [...key, query], queryFn: () => api<T>(path, { query }), enabled });

type FilterKeys = Array<"tournament" | "map" | "dates">;
/** Filter query params for the current global filters, restricted to the ones this endpoint supports. */
const useFq = (keys: FilterKeys) => filterQuery(useFilters().filters, keys);

export const useMeta = () => useGet<MetaResponse>(["meta"], "/api/meta");
export const useSearch = (q: string) => useGet<SearchResponse>(["search", q], "/api/search", { q }, q.trim().length > 1);
export const useLeaderboards = () => {
  const fq = useFq(["tournament"]);
  return useGet<LeaderboardsResponse>(["leaderboards"], "/api/leaderboards", fq);
};
export const useMatches = (query?: Query) => {
  const fq = useFq(["tournament", "map", "dates"]);
  return useGet<MatchListResponse>(["matches"], "/api/matches", { ...fq, ...query });
};
export const usePlayer = (puuid: string) => {
  const fq = useFq(["tournament", "map"]);
  return useGet<PlayerProfile>(["player", puuid], `/api/players/${puuid}`, fq);
};
export const useTeams = () => {
  const fq = useFq(["tournament"]);
  return useGet<TeamListResponse>(["teams"], "/api/teams", fq);
};
export const useTeam = (name: string) => {
  const fq = useFq(["tournament", "map"]);
  return useGet<TeamProfile>(["team", name], `/api/teams/${encodeURIComponent(name)}`, fq);
};
export const useMaps = () => {
  const fq = useFq(["tournament"]);
  return useGet<MapListResponse>(["maps"], "/api/maps", fq);
};
export const useMap = (name: string) => {
  const fq = useFq(["tournament"]);
  return useGet<MapProfile>(["map", name], `/api/maps/${encodeURIComponent(name)}`, fq);
};
export const useHeatmap = (name: string, query?: Query) => {
  const fq = useFq(["tournament"]);
  return useGet<HeatmapResponse>(["heatmap", name], `/api/maps/${encodeURIComponent(name)}/heatmap`, { ...fq, ...query });
};
export const useMatch = (id: string) => useGet<MatchReport>(["match", id], `/api/matches/${id}`);
export const useMatchKills = (id: string, query?: Query) => useGet<KillsResponse>(["kills", id], `/api/matches/${id}/kills`, query);
export const usePlan = () =>
  useMutation({ mutationFn: (body: PlanRequest) => api<PlanResponse>("/api/plan", { body }) });
