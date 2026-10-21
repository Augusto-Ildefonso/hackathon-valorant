# Hackathon Valorant

An interactive dashboard that analyses real VALORANT match data (Brazilian university tournaments) for players, coaches/analysts and teams. Built for the SEMCOMP/AcadArena hackathon; final delivery **23/10/2026 23h59** (5-minute pitch video + working prototype).

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
- Recommendations are rule-based and cite their evidence. An LLM may optionally polish the text but must never invent numbers, and the app must work without it.

## Screens
Home (search, KPIs, leaderboards, recent matches) · Player Profile · Team Profile · Map Profile (heatmaps, blind spots, attack/defense) · Match Report (scoreboard, round timeline, kill replay map) · Action Plan (Team A vs Team B + map). Details in `project-details.md`.

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

## Conventions
- Persist plans and roadmaps in `.claude/plans/<feature>-plan.md` and keep them updated.
