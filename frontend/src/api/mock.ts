// Mock layer: serves the contract fixtures so UI work needs no backend. Enabled with VITE_USE_MOCKS=1. Owner: Stream E.
import map from "@contract/fixtures/map.json";
import map_heatmap from "@contract/fixtures/map_heatmap.json";
import maps from "@contract/fixtures/maps.json";
import match from "@contract/fixtures/match.json";
import match_kills from "@contract/fixtures/match_kills.json";
import matches from "@contract/fixtures/matches.json";
import leaderboards from "@contract/fixtures/leaderboards.json";
import meta from "@contract/fixtures/meta.json";
import plan from "@contract/fixtures/plan.json";
import player from "@contract/fixtures/player.json";
import search from "@contract/fixtures/search.json";
import team from "@contract/fixtures/team.json";
import teams from "@contract/fixtures/teams.json";

const routes: Array<[RegExp, unknown]> = [
  [/^\/api\/meta$/, meta],
  [/^\/api\/search$/, search],
  [/^\/api\/leaderboards$/, leaderboards],
  [/^\/api\/matches$/, matches],
  [/^\/api\/matches\/[^/]+\/kills$/, match_kills],
  [/^\/api\/matches\/[^/]+$/, match],
  [/^\/api\/players\/[^/]+$/, player],
  [/^\/api\/teams$/, teams],
  [/^\/api\/teams\/[^/]+$/, team],
  [/^\/api\/maps$/, maps],
  [/^\/api\/maps\/[^/]+\/heatmap$/, map_heatmap],
  [/^\/api\/maps\/[^/]+$/, map],
  [/^\/api\/plan$/, plan],
];

export function mockResponse(path: string): unknown {
  const pathname = path.split("?")[0];
  const hit = routes.find(([re]) => re.test(pathname));
  if (!hit) throw new Error(`No mock for ${path}`);
  return structuredClone(hit[1]);
}
