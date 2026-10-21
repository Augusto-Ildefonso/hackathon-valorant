# Implementation Plan: VALORANT Analytics Dashboard (parallel build)

> After approval, copy this file to `.claude/plans/mvp-plan.md` in the repo (per global CLAUDE.md) and keep it updated as streams complete.

## Progress tracker (update in EVERY commit; format: `[x] item (YYYY-MM-DD, note)`)
- [x] Phase 0: repo skeleton (backend + frontend, `make dev`) (2026-10-21, FastAPI + Vite/React/Tailwind; `make setup`, `make dev`, `make dev-mock`, `make test`; Vite proxies `/api` and `/assets`)
- [x] Phase 0: Pydantic schemas + contract fixtures + mock layer (2026-10-21, 13 endpoints in `schemas/`, fixtures in `contract/fixtures/` via `contract/make_fixtures.py`, `frontend/src/api/{types,client,hooks,mock}.ts`, contract test; every router already answers with its fixture)
- [x] Phase 0: data SCHEMA.md + metrics SPEC.md + mini test store (2026-10-21, `Store` in `data/store.py`, `tests/fixtures/mini_store.py` builds from 3 real files, 6 invariant tests)
- [x] Phase 0: design-system stubs + CONTRIBUTING.md (2026-10-21, `components/ui/*`, `MinimapCanvas` with frozen props, 6 page stubs, Tailwind tokens from the Figma variables)
- [ ] A: filenames parser (tested on all files)
- [ ] A: loader + cache + team/colour mapping
- [ ] A: catalog + coords (validated on minimaps)
- [ ] A: metrics implementation
- [ ] A: meta/search/leaderboards/matches endpoints
- [ ] B: players analytics + roles + endpoint + PlayerPage
- [ ] B: teams analytics + endpoint + TeamPage
- [ ] C: maps + heatmaps + blind-spot layers + endpoints
- [ ] C: match report + kill replay + endpoints
- [ ] C: MinimapCanvas + MapPage + MatchPage
- [ ] D: insight engine + rules (player/team/match)
- [ ] A: round-type transition, projected economy and round win probability metrics (needed by D)
- [ ] D: action plan backend (round-by-round, predicted round type per round, contingencies) + endpoint + ActionPlanPage
- [x] Design: initial Figma frontend (6 screens + components), Action Plan redesigned to round-by-round (2026-10-20)
- [ ] D: optional LLM polish (flagged)
- [ ] E: app shell, filters, API client, design system styling
- [ ] E: HomePage (search, KPIs, leaderboards, recent matches)
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
