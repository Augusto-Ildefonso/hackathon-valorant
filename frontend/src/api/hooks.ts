// react-query hooks, one per endpoint; global filters (tournament / map / period) are applied where the API supports
// them. Owner: Stream E (add hooks here via one-line PR; pages call only these).
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { filterQuery, useFilters } from "@/lib/filters";
import { api, type Query } from "./client";
import type {
  HeatmapResponse, InsightMode, KillsResponse, LeaderboardsResponse, MapListResponse, MapProfile, MatchListResponse,
  MatchReport, MetaResponse, PlanCapabilities, PlanRequest, PlanResponse, PlayerProfile, SearchResponse, TeamListResponse, TeamProfile,
} from "./types";

const useGet = <T,>(key: unknown[], path: string, query?: Query, enabled = true, keep = false) =>
  useQuery({ queryKey: [...key, query], queryFn: () => api<T>(path, { query }), enabled, placeholderData: keep ? keepPreviousData : undefined });

/** `insights=llm` asks the backend for the AI analysis (Stream D); the default rule-based insights send no param.
 *  The previous data stays on screen while the slow AI answer loads (`keep`), so the page never collapses. */
const aiQuery = (mode: InsightMode): Query => (mode === "llm" ? { insights: "llm" } : {});

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
export const usePlayer = (puuid: string, insights: InsightMode = "rules") => {
  const fq = useFq(["tournament", "map"]);
  return useGet<PlayerProfile>(["player", puuid, insights], `/api/players/${puuid}`, { ...fq, ...aiQuery(insights) }, true, true);
};
export const useTeams = () => {
  const fq = useFq(["tournament"]);
  return useGet<TeamListResponse>(["teams"], "/api/teams", fq);
};
export const useTeam = (name: string, insights: InsightMode = "rules") => {
  const fq = useFq(["tournament", "map"]);
  return useGet<TeamProfile>(["team", name, insights], `/api/teams/${encodeURIComponent(name)}`, { ...fq, ...aiQuery(insights) }, true, true);
};
export const useMaps = () => {
  const fq = useFq(["tournament"]);
  return useGet<MapListResponse>(["maps"], "/api/maps", fq);
};
export const useMap = (name: string, insights: InsightMode = "rules") => {
  const fq = useFq(["tournament"]);
  return useGet<MapProfile>(["map", name, insights], `/api/maps/${encodeURIComponent(name)}`, { ...fq, ...aiQuery(insights) }, true, true);
};
export const useHeatmap = (name: string, query?: Query) => {
  const fq = useFq(["tournament"]);
  return useGet<HeatmapResponse>(["heatmap", name], `/api/maps/${encodeURIComponent(name)}/heatmap`, { ...fq, ...query });
};
export const useMatch = (id: string, insights: InsightMode = "rules") =>
  useGet<MatchReport>(["match", id, insights], `/api/matches/${id}`, aiQuery(insights), true, true);
export const useMatchKills = (id: string, query?: Query) => useGet<KillsResponse>(["kills", id], `/api/matches/${id}/kills`, query);
export const usePlanCapabilities = () => useGet<PlanCapabilities>(["plan-capabilities"], "/api/plan/capabilities");
export const usePlan = () =>
  useMutation({ mutationFn: (body: PlanRequest) => api<PlanResponse>("/api/plan", { body }) });
