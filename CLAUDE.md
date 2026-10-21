# Hackathon Valorant

An interactive dashboard that analyses real VALORANT match data (Brazilian university tournaments) for players, coaches/analysts and teams. Built for the SEMCOMP/AcadArena hackathon; final delivery **23/10/2026 23h59** (5-minute pitch video + working prototype).

The product is called **VaváGym** (shown as "VAVÁGYM" in the sidebar; logo mark "V"). Use this name in UI, titles and docs.

The product is **impartial**: there is no fixed "our team". The user picks any player, team, map or match, and picks the perspective explicitly where needed (e.g. Action Plan).

## Where to read what
- `.claude/docs/project-details.md`: **full scope** (screens, metrics, behavior, data caveats). Read it before building or changing any feature.
- `RULES.md`: hackathon rules, judging criteria, deadline.
- `data-report.md`: schema and quirks of the JSON files in `data/`.
- `public_catalog-report.md`: what `public_catalog/` contains and how it maps to the match data.
- `data/`: match JSONs (one per map). `public_catalog/`: images and ID lookups (agents, weapons, maps, abilities).

## Language
- UI text: **Portuguese-BR**.
- Code, comments, API fields, commits and docs: **English**.

## Stack
- Frontend: React + Vite + Tailwind. Dark, VALORANT-inspired theme (original styling, no Riot logos or fonts).
- Backend: Python + FastAPI + pandas/numpy. Loads all JSON from `data/` into memory at startup (no database); the data folder can grow, so never hardcode file counts.
- Recommendations are rule-based and cite their evidence. An LLM may optionally polish the text but must never invent numbers, and the app must work without it (off unless `VAVAGYM_LLM=1` and `GEMINI_API_KEY` (Google AI Studio) or `ANTHROPIC_API_KEY` are set in the environment or the git-ignored `.env`, see `.env.example`).

## Commands
`make setup` (venv + npm install) · `make dev` (API :8000 + web :5173) · `make dev-mock` (web only, fixtures) · `make test` (pytest + tsc) · `make fixtures`. API contract: `contract/openapi.md`; data tables: `backend/app/data/SCHEMA.md`; metric definitions: `backend/app/metrics/SPEC.md`; rules for PRs: `CONTRIBUTING.md`.

## Screens
Home (search, KPIs, leaderboards, recent matches) · Player Profile · Team Profile · Map Profile (heatmaps, blind spots, attack/defense) · Match Report (scoreboard, round timeline, kill replay map) · Action Plan (Team A vs Team B + map → a round-by-round plan for the whole match, where each round gets a predicted round type, buy, strategy, enemy weak points and probable enemy move). Details in `project-details.md`.

## Frontend design rule (mandatory)
- **Every page and component in the frontend must be based on the Figma design**: file `nilg3f5kGOAgARvLbUf8ml` (https://www.figma.com/design/nilg3f5kGOAgARvLbUf8ml/Hackathon-Valorant), page "Frontend v0". Frames: Home `25:17`, Map Profile `26:80`, Player Profile `27:155`, Team Profile `29:254`, Match Report `31:360`, Action Plan `32:432`; shared components Sidebar `24:48`, Top Bar `24:75`, Stat Card `24:4`, Insight Card set `24:46`, Filter Chip set `23:91`, Badge set `23:75`.
- **Before building or changing any page, read its frame** (Figma MCP: `get_screenshot`, `get_metadata`, `get_design_context`), reuse the design tokens (colors, fonts, spacing, radii) and the existing UI components in `frontend/src/components/ui/`, and compare a screenshot of the result (`node frontend/scripts/shot.mjs <route> out.png`, dev server running) with the frame before finishing.
- **Only deviate when the design shows something the data/contract cannot provide** (omit it, never invent numbers) or when a screen has no frame (e.g. the sidebar list pages): keep the same visual language and say so in the plan. If a design change is needed, change the Figma first (or ask) and then the code.
- Record deviations and new screens in `.claude/plans/mvp-plan.md` ("Screens follow Figma" note).

## Hard constraints
- Match data comes **only** from the supplied JSON files. No scraping, no external stats APIs, no data from other sources.
- Analysis and post-match/preparation use only; nothing that helps during a live match.
- Respect licenses for any library, font or image used.

## Data gotchas (details in `data-report.md`)
- Team names and final scores exist **only in filenames**; map Red/Blue to team names by matching the filename score with `teams[].roundsWon`.
- Red/Blue is a color, not a side: attack/defense swaps at halftime (use `winningTeamRole`).
- Exclude observers (`isObserver`). Empty values appear as `null`, `""` and `(0,0)`: filter on `bombPlanter is not null`, not on coordinates.
- Map codenames differ from public names (Jam=Lotus, Triad=Haven, Bonsai=Split, Juliett=Sunset, Infinity=Abyss, Plummet=Summit, Foxtrot=Breeze, Pitt=Pearl, Canyon=Fracture). Abyss and Summit have no minimap in the catalog.
- The catalog is outdated: some agents/weapons/armors have no name. Show them as unknown (or clearly labeled as inferred), never invent names.
- Always show the sample size behind a stat and flag low-sample values.

## Plans (mandatory workflow)
- Plans live in `.claude/plans/` (current: `mvp-plan.md`, the parallel build plan with streams A-F, ownership and checkpoints).
- **Before starting any task, read `.claude/plans/`** and find the stream/item the work belongs to. Do not redo anything already marked done, and do not touch files owned by another stream.
- **Every commit must update the plan** in the same commit: mark finished items as done (`[x]` with date and short note), add newly discovered tasks, and record decisions or contract changes. A commit that changes code without updating the plan is incomplete.
- If the plan and the code disagree, fix the plan first so nobody repeats work.
- **The canonical plan is the one on `main`.** Worktrees and branches only hold copies.
  - Before reading or editing the plan, sync with `main` (`git fetch origin && git rebase origin/main`, or read `git show origin/main:.claude/plans/mvp-plan.md`).
  - Plan updates must reach `main` as soon as they exist: either inside the code commit/PR that is merged to `main` right after, or as a plan-only commit pushed straight to `main` (fast-forward, never force). Never leave a plan change only in a worktree or an unmerged branch.
  - After merging, `git pull` in the main checkout so everyone reads the same version.

## Conventions
- Persist new plans and roadmaps in `.claude/plans/<feature>-plan.md`.
