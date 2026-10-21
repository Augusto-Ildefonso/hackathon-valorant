# Implementation Plan: VALORANT Analytics Dashboard (parallel build)

> After approval, copy this file to `.claude/plans/mvp-plan.md` in the repo (per global CLAUDE.md) and keep it updated as streams complete.

## Progress tracker (update in EVERY commit; format: `[x] item (YYYY-MM-DD, note)`)
- [x] Phase 0: repo skeleton (backend + frontend, `make dev`) (2026-10-21, FastAPI + Vite/React/Tailwind; `make setup`, `make dev`, `make dev-mock`, `make test`; Vite proxies `/api` and `/assets`)
- [x] Phase 0: Pydantic schemas + contract fixtures + mock layer (2026-10-21, 13 endpoints in `schemas/`, fixtures in `contract/fixtures/` via `contract/make_fixtures.py`, `frontend/src/api/{types,client,hooks,mock}.ts`, contract test; every router already answers with its fixture)
- [x] Phase 0: data SCHEMA.md + metrics SPEC.md + mini test store (2026-10-21, `Store` in `data/store.py`, `tests/fixtures/mini_store.py` builds from 3 real files, 6 invariant tests)
- [x] Phase 0: design-system stubs + CONTRIBUTING.md (2026-10-21, `components/ui/*`, `MinimapCanvas` with frozen props, 6 page stubs, Tailwind tokens from the Figma variables)
- [x] A: filenames parser (tested on all files) (2026-10-21, all 336 parse incl. `a/b/c` series suffixes and `RUSH_INCLUSIVO`/`UNIVAVA_C1` prefixes; `data/filenames.py`)
- [x] A: loader + cache + team/colour mapping (2026-10-21, `data/loader.py`: parallel parse, roster-vote fallback, pickle cache in `.cache/`; cold load ~1 s, cached 0.2 s; totals equal data-report: 336 maps / 6,618 rounds / 46,753 kills / 80,071 damage; 411 distinct playing puuids (413 in the report includes observers))
- [x] A: catalog + coords (validated on minimaps) (2026-10-21, `data/catalog.py`, `data/coords.py`; plants fall inside the bombsites on Ascent/Lotus/Haven/Split, image in `docs/coords-check.png`, script `backend/scripts/check_coords.py`)
- [x] A: metrics implementation (2026-10-21, `app.metrics`: events, players, rounds, objective; see SPEC.md "Where each metric lives"; buy-type thresholds calibrated)
- [x] A: meta/search/leaderboards/matches endpoints (2026-10-21, real implementations in `routers/meta.py`, store preloaded at startup)
- [x] B: players analytics + roles + endpoint + PlayerPage (2026-10-21, `analytics/players.py`, `analytics/roles.py`, real `/api/players/{puuid}` with tournament/map filters + 404, `PlayerPage`; roles = percentile of behavioral signals vs the whole dataset, top-2 + confidence + signals; IGL deliberately not produced; sanity-checked: duelist mains score higher on entry)
- [x] B: teams analytics + endpoint + TeamPage (2026-10-21, `analytics/teams.py`, real `/api/teams` and `/api/teams/{name}`, `TeamPage` with roster/roles, record, trend chart (SVG), per-map, economy, matches; insights wired to `engine.for_team`)
- [x] C: maps + heatmaps + blind-spot layers + endpoints (2026-10-21, `analytics/maps.py`, `analytics/heatmaps.py`, real `/api/maps`, `/api/maps/{name}` (case-insensitive, 404s) and `/api/maps/{name}/heatmap` (cached); method in `metrics/SPEC.md`; heatmap ~60 ms cold, ~3 ms cached)
- [x] C: match report + kill replay + endpoints (2026-10-21, `analytics/matches.py`, `analytics/replay.py`, real `/api/matches/{id}` and `/kills` with round/player/team filters; view angles verified: killers look at their victims, median error < 10 degrees in tests)
- [x] C: MinimapCanvas + MapPage + MatchPage (2026-10-21, smoothed heat, "DESCOBERTA n" zone boxes from the uncovered layer via optional `zoneLayer` prop, selector ordered by usage; verified against Figma frames on Ascent, Haven, Abyss and a real match)
- [x] D: insight engine + rules (player/team/match/map) (2026-10-21, `insights/{thresholds,baselines,core,rules_*,zones,engine}.py`; thresholds are the 20th/80th percentiles of the qualified population, see "Stream D notes")
- [x] A: round-type transition, projected economy and round win probability metrics (needed by D) (2026-10-21, `metrics/rounds.py`: `team_rounds`, `next_type_distribution`, `projected_economy`, `round_win_probability`; economy model checked against real credits, median error < 400)
- [x] D: action plan backend (round-by-round, predicted round type per round, contingencies) + endpoint + ActionPlanPage (2026-10-21, `insights/action_plan.py`, `routers/plan.py`; page shows data notes and an active narrative button)
- [x] Design: initial Figma frontend (6 screens + components), Action Plan redesigned to round-by-round (2026-10-20)
- [x] D: optional LLM narrator, flagged (layer 3) (2026-10-21, `insights/llm.py`; off by default; tested only with a fake client, never run against the real API in this session)
- [x] D: scouting report + candidate play scoring + coach text templates (layer 1) (2026-10-21, `scouting.py`, `plays.py`, `map_intel.py`)
- [x] D: win-probability model validated on held-out matches (layer 2) (2026-10-21, `play_model.py`; adopted: log-loss 0.623 vs 0.640 baseline on 93 unseen matches). Play ranking itself uses shrunk empirical site rates, not a trained model
- [x] D: `map_plan` backend (2026-10-21, `insights/map_plan.py`, additive `RoundPlan.map_plan`: per-player attack arrows, defender holds + retake arrows, enemy route, zones; evidence = snapshots, low_sample when thin)
- [x] D: strategy variety (2026-10-21, `plays.History`: site rotation after a loss/repeat, momentum lines, early tempo on eco/force/pistol, rotating focus on enemy weak players, enemy site rotation; base scenario now spreads wins by probability instead of always the most probable result)
- [x] D: Action Plan minimap drawing in the frontend (2026-10-21, user approved the Figma change: panel "Mapa tático do round", node 45:549 in frame 32:432). `MinimapCanvas` got arrowheads, dashed routes, width, labels (leader column for player arrows) and `boxes` for zones (props stay compatible); `RoundMapPanel` in `ActionPlanPage` has toggles Meu plano/Inimigo/Zonas, legend and the who-does-what list with sample sizes. Defense rounds show hold circles + retake arrows (the header says "reforço no site X · inimigo provável no Y"). Deviation from the mock: defense layout added (the Figma shows an attack round). Screenshot helper: `frontend/scripts/shot-map.mjs <round> out.png`
- [x] E: app shell, filters, API client, design system styling (2026-10-21, Sidebar + TopBar from Figma, global filter context (tournament/phase, map, period) persisted in localStorage and applied by the hooks, global search dropdown, tokens/Badge/Meter/FilterChip/Panel/DataTable/StatCard/InsightCard restyled to the design)
- [x] E: HomePage (search, KPIs, leaderboards, recent matches) (2026-10-21, matches Figma; plus simple list pages `/jogadores /times /mapas /partidas` for the sidebar, which have no Figma frame)
- [x] All six screens rebuilt from Figma (2026-10-21): Player and Team verified on real data; Map, Match Report and Action Plan are built to the design on top of Stream C/D's fixture stubs and will fill in as those streams replace their routers (visual check: `frontend/scripts/shot.mjs`)
- [ ] E: Playwright smoke tests + UX polish
- [ ] F: pitch script, showcase entities, recording, submission
- [ ] Catalog-usage confirmation from organizers (Discord ticket)

## Phase 0 outcome and decisions (2026-10-21; streams can start from here)
What exists now: runnable backend + frontend skeletons, the frozen contract, fixtures, the `Store` schema with a mini store, metric specs and UI stubs. Every endpoint **already returns its fixture**, so each stream replaces its router body instead of creating routes.
- **How to start a stream:** `make setup`, then `make dev` (or `make dev-mock` for frontend-only). Backend tests: `make test`.
- **Routers:** `routers/meta.py` (A: meta, search, leaderboards, `/api/matches` list), `players.py`+`teams.py` (B), `maps.py` (C), `matches.py` (C: detail + kills), `plan.py` (D). Keep `response_model` as is; the contract test fails if a body drifts.
- **Insight engine:** entry points `for_player / for_team / for_match / for_map` exist in `insights/engine.py` returning `[]`; D owns the file from now on, signatures are frozen.
- **Store:** analytics code uses `app.data.store.Store` only. `tests/fixtures/mini_store.py::build_mini_store()` gives a real 3-match store (a few seconds to build; cache it in a module-scoped fixture). Stream A's `loader.py` must produce identical tables (`SCHEMA.md`).
- **Buy-type thresholds** in `metrics/SPEC.md` are defaults (eco < 1600, semi-eco < 2900, force < 3900 or spent > 80%, full buy ≥ 3900); A calibrates on the data and updates that table.
- **Frontend:** Tailwind v4 pinned at 4.1.18 (4.0.0 crashes the Vite production build). Design tokens in `src/index.css` mirror the Figma variables. `MinimapCanvas` props are frozen (stub draws heat/points/lines/routes; C owns the body).
- **Fixtures** are shape examples (made-up numbers on real team/map names). Regenerate with `make fixtures`; changing a shape is a contract PR.
- **Stream A hand-off (2026-10-21):** the real Store and metrics are ready. Replace `build_mini_store` in your tests with the session fixture `full_store` (`tests/conftest.py`, cached load) or keep the mini store for fast unit tests; use `from app.deps import get_store` in routers and `store.where(...)` for the global filters. Metrics: `from app.metrics import ...` (SPEC.md lists them). Contract additions are additive only (`matches.tournament_code/series_no/winner_team`, `rounds.defender_color`, `round_player_stats.team_name`, `Store.skipped`, `Store.where/subset`). `team_name` is the display name derived from the filename slug (`ufg_gc_eagles` -> `UFG GC Eagles`); the same team spelled differently across tournaments is NOT merged.
- **Stream B notes (2026-10-21):** `analytics.roles.role_model(full_store)` is cached per store and always relative to the whole dataset (filters do not change role percentiles). Spatial role signals (isolation, site presence) are snapshots at kill moments only. Weapon rows are per (weapon, buy type) with >= 5 rounds, top 20; `kd` = kills / deaths in rounds with that purchase. Player/team routers call `engine.for_player` / `for_team`, so D's rules appear automatically. Shared frontend additions by B: `lib/format.ts` (pt-BR labels, number/percent formatting) and `components/ui/Panel.tsx` (`Panel`, `StatValue`); E may restyle but keep props. Pages are not yet connected to the global filter context (E).
- **Screens follow Figma (2026-10-21):** all pages are built from the Figma frames. Left out on purpose because the data/contract has no source: "patches" text (Map), individual death dots and dashed "descoberta" boxes (Map, API gives grids), per-player agent handles / item prices / loss bonus / trade rate (Action Plan), "Comparar com outro time" opens the Action Plan with team A preset. Insight panels (strengths, weaknesses, tips, blind spots) show "Sem dados suficientes" until Stream D's rules exist.
- **Pictures beside names (2026-10-21, approved Figma change):** every list showing an agent, weapon or map has its catalog picture next to the name (Home/Partidas, Player, Team, Map, Match scoreboard + kill list, Action Plan agent cards/buy list/plan table/map picker, Mapas list). Use `AgentIcon`, `WeaponIcon`, `MapIcon` / `CatalogIcon` from `components/ui/AgentIcon.tsx` (they fall back to a "?" tile) and never hand-roll `<img>`. The API serves cached thumbnails at `/api/thumb/...` (`routers/assets.py`); `MapRef.thumb_url` is new. Map selector chips on the Map page stay text-only (they are Figma component instances).
- **Product name (2026-10-21): VaváGym** (was the placeholder "Spike Lab"). Sidebar shows "VAVÁGYM" with a "V" mark, page title "VaváGym", API title "VaváGym API"; Figma sidebar updated. Use it in the pitch, slides and README-style text.
- **Stream C notes (2026-10-21):** Map and Match screens run on real data. Decisions: classification = "balanced" when attack/defense win rates are within 3 p.p.; MVP = highest game score on the winning team; `KillEvent.headshot` is always null (not derivable per kill); spike deaths show as killer == victim with `damage_type: bomb` (the UI does not count them as kills). Heat rendering (2026-10-21): intensities are scaled to the layer's 95th percentile with a gamma 0.8 curve, opacities 0.7-0.9 and the minimap is dimmed (brightness 0.55) while heat is on, so hot zones are clearly visible. Known limits: death/kill layers are density grids (no individual dots); "descoberta" boxes are the top blobs of the uncovered layer; pan/zoom was not added; map selector chips stay text-only. The Insight panels ("Pontos cegos", match improvements) stay empty until Stream D's rules exist (`engine.for_map` / `for_match`).
- **For C and D:** `MinimapCanvas` now also draws view cones (`player`/`kill` points with `viewRadians`), killer ring, victim ✕, square plant markers with a site letter, dashed lines and green/violet heat colors (props unchanged). `MapPage`, `MatchPage` and `ActionPlanPage` are complete UIs against the frozen contract: replace your router stub and the screen fills in; change a page only if the contract needs it. Match replay uses `GET /api/matches/{id}/kills?round=N` (1-based) and the view-angle formula in `metrics/SPEC.md`.
- **Stream D notes (2026-10-21):**
  - Insights: a fact fires when it is in the top/bottom 20% of the qualified population (`baselines.py`: players >= 100 rounds, teams >= 3 matches; `thresholds.py` holds every cutoff). Below the hard minimums a rule stays silent; below `LOW_SAMPLE` it fires with `low_sample`. Evidence values are in display units (percentages 0-100, `unit: "%"`); `InsightCard` prints them accordingly. `engine.for_player/for_team` take an optional `base`, `for_map` an optional `store` (the maps router passes it) for the blind-spot zones. Calibration on the real data: K/D strong/weak flags land on roughly 20% of players each (tested).
  - Action Plan: deterministic base scenario per round (side, type from the transition model downgraded when the projected credits cannot pay for it, economy, win probability from the logistic model), scouting report (rosters, sites, roles assigned to named players), candidate plays scored by shrunk rates. Contract additions (additive): `PlanRequest.use_llm`, `PlanResponse.text_source` and `notes_pt`, `GET /api/plan/capabilities`.
  - Static game metadata (not in the catalog) lives in `insights/agents_meta.py`: agent class table and armor-id levels. Armor ids are INFERRED from loadout values (822bcab2 = heavy, others = light); the UI says "escudo leve/pesado".
  - LLM: env `VAVAGYM_LLM=1` + `GEMINI_API_KEY` (Google AI Studio; tried in order `gemini-flash-latest`, `gemini-3.5-flash`, `gemini-3-flash-preview`, moving on after 429/5xx/404/timeouts; `gemini-2.5-flash` returns 404 for new keys; 2 retries with backoff per model; calls are chunks of 6 rounds in parallel with a 32k output limit because thinking tokens count against it; failures and rejected fields are reported in `notes_pt` and failed attempts are not cached; verified end to end on 2026-10-21, ~1 to 2.5 min when Gemini is overloaded); Gemini is the only provider (the Anthropic path was removed on 2026-10-21); `VAVAGYM_LLM_MODEL` forces one model and disables the fallback chain; keys may live in the git-ignored repo-root `.env` (see `.env.example`, loaded by `llm.py`, real env vars win); plain HTTPS via httpx; every number in a rewritten field must appear in that round's facts, else the template text stays; cache in `.cache/llm/`. Not exercised against the real API yet.
  - Known limits: no utility/lineup/callout data; the enemy route is a coarse centroid path (positions exist only at kill moments); per-player arrows and drawn zones (`map_plan`) need the Figma update; enemy weak points are often empty against strong teams; plans for rounds beyond the first of each type reuse the same sites, so per-round variety comes from side, type, economy and contingencies.
- **Known data limits:** 3 observer-only puuids and 68 team names (the same club can appear as separate team names, e.g. `Azure Bears Black/Golden/Silver/White` are distinct teams on purpose). Armor IDs have no names (use loadout value to tell light vs heavy if needed).
- **Not done in Phase 0 (by design):** real loader, filenames parser, catalog/coords, metrics code, Playwright, global filter context (E).

## Context
Hackathon deadline is **Fri 23/10/2026 23h59** (today is Tue 20/10, so ~3.5 working days). Scope is fixed in `.claude/docs/project-details.md`: 6 screens (Home, Player, Team, Map, Match Report, Action Plan), impartial (no "our team"), FastAPI + pandas in-memory backend, React/Vite/Tailwind dark frontend, rule-based insights with evidence. The repo started with docs, `data/` and `public_catalog/` only; Phase 0 added the skeletons and contract (see above).

Builders are a mix of humans and Claude sessions working at the same time. The plan therefore minimizes coupling with three rules:
1. **Contract first:** a short Phase 0 freezes the API contract, fixtures, data-frame schema and folder layout, so every stream can work against mocks from hour one.
2. **Vertical slices with strict file ownership:** each stream owns its backend module, its router and its frontend screen. No two streams edit the same file.
3. **Integrate early and often:** small PRs to `main`, an integration checkpoint every day.

## Phase 0: Contract freeze (single owner, target ≤ 3-4 h, everyone else waits or reads docs)
Owner: Stream A (platform). Deliverables, all merged to `main` before streams start coding:

1. **Repo layout** (below) with empty runnable skeletons: `backend/` (FastAPI app + `/api/health`, pytest) and `frontend/` (Vite + React + Tailwind + router with 6 empty routes). One-command dev: `make dev` (or two documented commands) and Vite proxy `/api` → `:8000`.
2. **`contract/openapi.md` + Pydantic response models** in `backend/app/schemas/` (one file per domain: `meta.py`, `player.py`, `team.py`, `map.py`, `match.py`, `plan.py`, `common.py`). Shared types: `Insight {id, kind: strength|weakness|tip|strategy, text_pt, evidence: {metric, value, baseline?, sample_size}, low_sample: bool}`, `Point {x, y}` already in minimap-normalized 0..1 coordinates, `Side = attack|defense`.
3. **Fixtures:** `contract/fixtures/<endpoint>.json`, one realistic example per endpoint, derived from 2-3 real matches. The frontend consumes these through a mock layer (`frontend/src/api/mock.ts`, toggled by `VITE_USE_MOCKS=1`) so UI work needs no backend.
4. **Data-frame schema doc** `backend/app/data/SCHEMA.md`: the normalized tables (matches, match_players, rounds, round_player_stats, kills, damage) with column names and dtypes, plus the `Store` interface (`store.matches`, `store.kills`, …, `store.team_of(match_id, puuid)`, `store.side(match_id, round, team)`). Analytics streams code against this and use a tiny **test store** (`backend/tests/fixtures/mini_store.py`, built from 3 real files) until the real loader lands.
5. **Shared metric definitions** `backend/app/metrics/SPEC.md` (from §6 of project-details: HS%, ADR, first kill, trade window, buy-type thresholds, clutch, side per round). Stream A implements them in `backend/app/metrics/` by end of Day 1 (Wed AM); others can call them via the interface or stub.
6. **Frontend design system stubs** (owned by Stream E): Tailwind theme tokens (dark/red palette), `StatCard`, `InsightList` (renders `Insight` with evidence + low-sample badge), `DataTable`, `FilterBar`, `PageHeader`, `AgentIcon`/`WeaponIcon` (catalog URLs), `EmptyState`. Stubs with the final props signature are enough; styling is refined later.
7. **Branch/PR rules** in `CONTRIBUTING.md` (short): branch per stream `stream-x/<topic>`, PRs to `main`, squash-merge, rebase before merging, never edit files you do not own (open a PR comment or ask the owner), contract changes only through a PR that touches `contract/` + `schemas/` and is announced to all streams. Claude sessions use one git worktree each.

### Repo layout and ownership
```
backend/app/
  main.py, deps.py                      A   app wiring, router registration (A adds a line per router once)
  schemas/*.py                          A (frozen after Phase 0; changes by PR)
  data/   loader.py, filenames.py, catalog.py, coords.py, store.py   A
  metrics/                              A
  analytics/players.py, roles.py        B
  analytics/teams.py                    B
  analytics/maps.py, heatmaps.py        C
  analytics/matches.py, replay.py       C
  insights/rules_*.py, engine.py        D   (reads metrics outputs, never raw JSON)
  insights/action_plan.py, llm.py       D
  routers/{meta,players,teams}.py       A (meta) / B
  routers/{maps,matches}.py             C
  routers/plan.py                       D
frontend/src/
  api/ (client, types, mock)            E
  components/ui/*                       E
  components/map/MinimapCanvas.tsx      C   (layers: heat, kills, trajectories, plants)
  pages/Home*                           E
  pages/Player*, pages/Team*            B
  pages/Map*, pages/Match*              C
  pages/ActionPlan*                     D
contract/ fixtures + openapi.md         A
```

## Workstreams (run in parallel after Phase 0)

### Stream A: Platform + data layer (the only "critical path" stream, finishes core by Wed noon)
- `filenames.py`: parse tournament, match no., date, team A/B, scores, map from filenames (incl. `a`/`b` suffixes, names with underscores like `fatec_pg`, `azure_bears_golden`). Unit-test against **every** file in `data/`.
- `loader.py`: parse all JSON in `data/` (recursive, skip `.DS_Store`) into the normalized tables; exclude observers; normalize empty encodings (`null`/`""`/`(0,0)`) to `None`; cast `viewRadians` to float; use orjson and a pickle/parquet cache keyed by file mtime so restarts stay fast (193 MB).
- Team mapping: match filename score to `teams[].roundsWon` to map team name → Red/Blue; handle ties by player rosters; log unmapped matches rather than failing.
- `catalog.py`: load `PublicContentCatalog.json`; agent/weapon name lookups with explicit "unknown" fallback and `inferred` flag; map codename → public name; asset URL helpers; mount `public_catalog/` as static `/assets`.
- `coords.py`: game→minimap transform (swapped axes) normalized to 0..1; discard outliers; per-map `has_minimap`. Validate by plotting plant positions on 2-3 minimaps (saved check image in `docs/`).
- `metrics/`: implement SPEC.md functions once (HS%, ADR, first kill/death, trade, buy type, clutch, side per round with halftime/overtime, plus round-type transition probabilities, projected economy and round win probability used by the Action Plan).
- `routers/meta.py`: `/api/meta` (KPIs, tournaments, maps, date range), `/api/search`, `/api/leaderboards`, `/api/matches` (list with filters). Home screen data.
- Hand-off milestone: **Wed 21 12:00** real `Store` + metrics merged; B/C/D swap the mini test store for the real one with no code changes.

### Stream B: Players and teams (backend + screens)
- `analytics/players.py`: K/D, assists, HS%, ADR, rounds, opening-duel stats, weapon performance by buy type, per-map kills/deaths, agents played + favorite, clutches and multi-kills.
- `analytics/roles.py`: behavioral role scores (Entry, Lurker, Suporte, Anchor, Flex; IGL inferred/omitted) using first-duel share, distance to teammates (`playerLocations`), assists + ability casts, defense-side site presence, agent variety; returns top-2 roles + confidence + the signals used. Calibrate on the data and sanity-check with known players.
- `analytics/teams.py`: roster, record, per-match and per-map performance, attack/defense split, economy, plant-site tendencies, role composition.
- Routers: `/api/players/{puuid}`, `/api/teams`, `/api/teams/{name}`.
- Pages: `PlayerPage`, `TeamPage` (charts via Recharts or similar, `InsightList` for strengths/weaknesses/tips).
- Insights consumption: until D ships, return B's own `strengths/weaknesses` as empty list; D's engine is called by the router once available (single function `insights.engine.for_player(stats)` / `for_team(stats)`; the signature is frozen in Phase 0 and D provides a stub returning `[]` on Day 1).

### Stream C: Maps and matches (backend + screens + the minimap component)
- `analytics/maps.py`: most used agents/weapons, attack vs defense win rate classification, per-site plant/defuse/retake stats.
- `analytics/heatmaps.py`: kill/death grids per side; **blind-spot layers**: (a) dangerous zones (deaths ≫ kills per cell), (b) uncovered zones (low occupancy/look coverage from `playerLocations` + `viewRadians` yet later enemy kills originate there). Output normalized grids (e.g. 64×64) + plant points.
- `analytics/matches.py`: match report (score, round timeline with side/plant/defuse/ceremony/economy, scoreboard, MVP), match-level improvement suggestions via D's `engine.for_match` stub.
- `analytics/replay.py`: per-kill payload: killer, victim, trajectory, positions + view angles of alive players, weapon, round time.
- Routers: `/api/maps`, `/api/maps/{name}`, `/api/maps/{name}/heatmap`, `/api/matches/{id}`, `/api/matches/{id}/kills`.
- `MinimapCanvas.tsx`: canvas component with layered rendering (heat grid, points, killer→victim trajectories, view cones, plant markers), pan/zoom, round/player/team filters; graceful state for Abyss/Summit (no minimap). Props frozen in Phase 0 so B (player kills per map) and D (enemy position hints) can reuse it later.
- Pages: `MapPage`, `MatchPage` (scoreboard, round timeline, kill replay).

### Stream D: Insight engine + Action Plan (backend + screen)
- `insights/engine.py` + `rules_player.py`, `rules_team.py`, `rules_match.py`: declarative rules `condition(stats) → Insight` with threshold config in one `thresholds.py`; every insight carries evidence + sample size, `low_sample` flag below thresholds; texts in pt-BR from templates. Works from the **stats dicts** B/C return (schema frozen), so D never touches raw JSON and can develop against fixtures.
- `action_plan.py`: given Team A, Team B, map, perspective, **rounds per half** (default 12) and **starting side**, builds a **round-by-round plan for the whole match** (see project-details §5.6). Steps: (1) agent recommendations (team history on the map + opponent tendencies) and opponent summary; (2) a **base-scenario simulation** that walks the rounds in order, assigns the side of each round, **predicts the round type** (pistol/eco/semi-eco/force/full buy) from the round-type transition model + projected economy, and picks the most probable result of each round from the round win probability per side/map/type; (3) for each round: buy recommendation per role, attack/defense strategy, enemy weak points, probable enemy strategy and move, and a **contingency** (what changes if the previous round is won vs lost). Every item carries evidence + `low_sample`. Reads team/map aggregates through the stats functions from B and C (via the frozen `schemas`), with fixtures until they land. The round-type transition and projected-economy functions live in `metrics/` (A) per SPEC.md; D only consumes them.
- `llm.py` (optional, last): Claude API call that rewrites the structured plan as narrative; feature-flagged by env var, strictly given the structured facts, with a post-check that no number in the output is absent from the input; always falls back to the rules output.
- Router `/api/plan` (POST; body: team A, team B, map, perspective, rounds_per_half, starting_side; response: agents, opponent summary and an ordered `rounds[]` each with `number`, `half`, `side`, `round_type`, `projected_economy`, `buy`, `strategy`, `enemy_weak_points`, `enemy_probable_strategy`, `contingency`, `insights[]`). Page `ActionPlanPage`: selector bar (team A/B, swap, map, rounds per half, starting side), perspective toggle, match timeline of round chips (side + predicted type), selected-round detail with route minimap, full plan table, evidence badges.
- D owns `thresholds.py`; B/C do not edit it.
- **Coach-style strategy: three layers (decided 2026-10-21, user approved "use all three").** The goal is advice a coach would give: personalized to the two rosters, the map, side and round type, not a classification against a global cutoff. Each layer works without the next one.
  1. **Statistics / scouting report (deterministic, required).** `insights/scouting.py` builds per-player profiles for both rosters (shrunk estimates + sample size: opening win %, first-death rate, trade rate, K/D, ADR, HS%, best weapon, best agent/role on the map) and team form (overall vs on this map, by side and round type, pistol/eco/post-plant/retake), plus map facts (side bias, plant sites and timing, danger/uncovered zones). Output = ranked matchup facts, e.g. our opening strength against their opening weakness. Roles are assigned to named players from their own numbers (entry = best opening win %, trade = best trader, anchor = best impact on the target site). Template pt-BR coach text: plan in one line, why (2-3 facts with numbers), who does what, risk and fallback; fills `strategy`, `contingency`, `enemy_weak_points`. Rules in `rules_*.py` use `thresholds.py` for "this fact is notable"; candidate plays (execute on the conceded site, split with lurker, default for the plant, stack the weak lane, reinforce their favourite site, retake setup, save/force/eco rush) are scored by supporting fact edges, down-weighted by sample size and flagged `low_sample`.
  2. **ML (small, validated, optional).** `insights/play_model.py`: a round win-probability model (logistic regression / gradient boosting; features: side, map, round type, both economies, both teams' strength on the map, roster opening/trade rates) and a "site + timing -> win probability" estimate per side and map, shrunk toward the dataset. Used only to rank the candidate plays and to explain them (coefficients / feature contributions). Must beat the empirical shrunk baseline on held-out matches (split by match, not by round); if it does not, ship the empirical rates and record that here. Small dataset: keep it simple, flag `low_sample`, never present it as an oracle.
  3. **LLM narrator (optional, flagged).** `insights/llm.py` receives the scouting report and the chosen play with its scores and reasons, and only rewrites them as a coach would (why this play, who does what, risk, fallback). It never decides the strategy or computes numbers; every figure in the output must appear in its input (post-check), otherwise that field keeps the template text. Env flag `VAVAGYM_LLM=1` + `ANTHROPIC_API_KEY`; disk cache; the app is complete without it.
- **Map drawing (proposed, needs approval: update Figma frame `32:432` first, per the Figma rule).** Additive optional `map_plan` per round: `routes[{label, kind, role, agent, handle, points, t0, t1}]`, `zones[{box, label, kind}]`, `markers[]`, computed from clustered real positions (enemy `player_locations` by site and time bucket 0-30/30-60/60+ s; our winning rounds to the target site for each player's position at about 10/25/40 s and the plant; defender hold positions in the first 20 s; retake route; enemy opening-loss zones and our danger zones). Verify the snapshot rate before promising per-second paths. `MinimapCanvas` gets arrowheads, dashed routes and per-route colour/time labels (props stay compatible). Falls back to low-sample badges when the history is thin (widen to all teams on the map and say so).
- Known limits to state in the app: no utility/lineup/callout data, so plans cover positioning, timing, roles and economy only; player-level reasoning falls back to overall stats below the sample threshold.

### Stream E: Frontend shell, design system and Home
- App shell: routing, layout, nav, global `FilterBar` (tournament, map, date range) in a context persisted to URL/localStorage, API client with react-query, error/loading/empty states, mock toggle.
- Design system components listed in Phase 0, final styling (angular dark/red VALORANT-inspired theme, original assets only), icons from catalog, responsive laptop layout.
- `HomePage`: global search (debounced), KPI cards, leaderboards, tournament filter + recent matches.
- Owns the shared TS types generated from the contract (`frontend/src/api/types.ts`); regenerate when `schemas/` changes.
- After Home: UX polish pass over all pages (consistency, copy in pt-BR, accessibility basics), and the Playwright smoke tests.

### Stream F (can be 1-2 people, mostly human): Demo, pitch, QA
- Writes the pitch script around the judging criteria (Innovation, Impact, Analysis quality, Feasibility, Usability, Prototype/Pitch) and the 5-minute storyline: one concrete scenario per audience (coach prep with Action Plan, player review, post-match report with the kill replay).
- Picks 2-3 showcase entities (teams, a match with a great kill-replay, a map with a clear blind spot) and verifies they render well; reports bugs to owners.
- Slides, recording, upload as unlisted YouTube, submission form with team names. Starts the Discord ticket to confirm catalog usage is allowed (Day 1).
- Runs the end-to-end checklist (Verification below) at each checkpoint.

## Timeline and checkpoints
| When | Goal |
|---|---|
| Tue 20 (rest of day) | Phase 0 merged; streams start; catalog-rules ticket sent |
| Wed 21 12:00 | **CP1:** real Store + metrics + `/api/meta` merged; each stream has its page rendering from fixtures |
| Wed 21 end | Each stream: first real endpoint wired (B player, C match report, D engine v1, E shell + Home) |
| Thu 22 12:00 | **CP2:** all 6 pages on real data (even if rough); mocks off by default |
| Thu 22 end | Feature-complete: blind spots, replay, roles, Action Plan; D's optional LLM stays behind flag |
| Fri 23 12:00 | **Code freeze for features**; only bug fixes/polish; demo dataset picked |
| Fri 23 17:00 | Pitch recorded (needs a stable build); fallback: screen recording from the Thu build |
| Fri 23 22:00 | Submitted (1h40 buffer before 23h59) |

## Dependency map and mitigations
- **A → B, C, D (data/metrics):** mitigated by the schema doc + mini test store; A's core lands by CP1.
- **C → B, D (MinimapCanvas, heatmap helpers):** props/API frozen in Phase 0; B and D only use it for optional features (player kills per map, enemy positions) after CP2.
- **B, C → D (stats for insights/plan):** D codes against frozen stats schemas + fixtures; engine entry points stubbed on Day 1.
- **Everything → E (types/components):** E publishes component stubs in Phase 0; styling changes never alter props.
- Shared files (`main.py` router registration, `package.json`, `requirements.txt`): all owned by A; others request additions via a one-line PR, merged within the hour.

## Risks
- **Team/colour mapping errors** (names only in filenames): A tests on every file, logs unmapped ones; fallback by roster overlap.
- **Coordinate transform unverified:** validated visually on Day 1; if wrong, only `coords.py` changes.
- **Abyss/Summit lack minimaps:** explicit `has_minimap` flag drives UI fallbacks from the start.
- **Role heuristics subjective:** show top-2 + signals; present as "behavioral" in the pitch.
- **Low sample sizes:** `low_sample` flag is part of the contract so no screen can forget it.
- **Startup time with 193 MB:** disk cache; measure on Day 1; if > 20 s, precompute aggregates.
- **Scope vs 3.5 days:** if behind at CP2, cut order: (1) LLM polish, (2) uncovered-zones blind-spot layer, (3) per-round plan depth, (4) IGL role. Core of every screen stays.

## Verification
- **Backend:** `pytest` per module (filename parser over all files in `data/`, metrics vs hand-computed values from one match, role scores sanity, heatmap shapes, insight evidence always present); a contract test that every fixture validates against its Pydantic model and every router returns a body that validates too.
- **Cross-check:** total kills/rounds/players from the Store equals the numbers in `data-report.md` (336 maps, 6,618 rounds, 46,753 kills, 413 players) when the full dataset is present.
- **Frontend:** `tsc` + lint + Playwright smoke test visiting all 6 routes with mocks, then with the real backend (`make dev`), asserting no console errors and key elements visible.
- **Visual check:** plant markers on minimap for Ascent/Lotus/Haven/Split; kill replay on one known match.
- **End-to-end demo script (Stream F, run at each checkpoint):** Home search → Player → Team → Map (toggle blind-spot layers) → Match Report (open a kill replay) → Action Plan (Team A vs B + map, flip perspective, step through the round-by-round plan and show a round whose type changes with the contingency).
- **Rules compliance:** no external data sources; no Riot assets beyond the supplied catalog; LLM off by default and never invents numbers.
