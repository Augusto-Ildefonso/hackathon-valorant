# Project Details

Full description of what the project must contain. `CLAUDE.md` holds the short version; this file is the source of truth for scope, screens and behavior.

## 1. Purpose

An interactive web dashboard that turns real VALORANT custom-game data (Brazilian university tournaments) into actionable insight for **players, coaches/analysts and teams**. All three audiences have equal weight; the app has a different entry point for each but one shared data layer.

- **Impartial by design:** there is no fixed "our team". The user can open any player, team, map or match. Wherever a perspective is needed (e.g. Action Plan), the user picks it explicitly.
- **Post-match / preparation use only:** analysis, reflection and pre-match preparation. Nothing that interferes with a live match (see `RULES.md`).
- **Hackathon context:** deadline 23/10/2026 23h59, judged on Innovation, Impact, Analysis/Data quality, Feasibility, Usability and Prototype/Pitch (equal weights, max 30). Deliverable is a 5-minute pitch video. All five main screens are in scope (no screen is demoted to "stretch"); polish and data correctness matter as much as breadth.

## 2. Data and constraints

Source of truth: JSON files in `data/` (one file per played map). Details in `data-report.md` and `public_catalog-report.md`. Key facts:

- 336 maps / 6,618 rounds / 46,753 kills / 413 players in the full dataset (the local `data/` may hold fewer files; the Univavá folders may be added later, so nothing may be hardcoded to the current file count).
- Match → Round → Player → Kill/Damage hierarchy. Join key for players is `puuid`.
- **Team names and final scores exist only in the filename** (`<TOURNAMENT>_<no.>_<dd-mm-yy>_<team A>_<score A>_x_<score B>_<team B>_<map>.json`). The backend must parse them and map each name to `Red`/`Blue` by matching the filename score against `teams[].roundsWon`. Suffix `a`/`b` on the match number = several maps of one series.
- `Red`/`Blue` is a color, not a side: attacker/defender swaps at halftime. Use `roundResults[].winningTeamRole` and round number to know the side in each round.
- Exclude observers (`isObserver`, `teamId = Neutral`).
- "Empty" is encoded as `null`, `""` and `(0,0)`/`0`. Filter on `bombPlanter is not null`, never on coordinates.
- Ability effects are always `null`; no mouse/crosshair traces; shots are aggregated per target.
- Data must come **only** from the supplied JSON. No scraping, no external APIs for match data.

### Catalog (`public_catalog/`)
Lookup table + images for agents, weapons, maps, abilities and role icons. Caveats:
- Catalog is older than the matches: 4 agent IDs (~6% of player slots), 1 heavily used weapon (`410B2E0B…`) and all armor IDs have no names. Show them as "Agente desconhecido" / "Arma desconhecida" and, if inferred (e.g. by price), label them as inferred.
- Map codename → name (derive from filenames, 1:1): Ascent→Ascent, Jam→Lotus, Triad→Haven, Bonsai→Split, Juliett→Sunset, Infinity→Abyss, Plummet→Summit, Foxtrot→Breeze, Pitt→Pearl, Canyon→Fracture.
- Abyss and Summit have no minimap/coordinate transform; the map-based views must degrade gracefully (message + non-map stats still shown).
- Coordinate transform (`xMultiplier`, `xScalarToAdd`, `yMultiplier`, `yScalarToAdd`) is undocumented: axes are swapped (`u = y·xMultiplier + xScalarToAdd`, `v = x·yMultiplier + yScalarToAdd`); validate by plotting plant positions on the minimap. Discard outliers (e.g. `x < -10000`).
- Agents have no role field; roles are handled in §5.1.
- Rules check pending: confirm with the organization (Discord ticket) that using the catalog is allowed.

## 3. Architecture

- **Backend (Python, FastAPI, pandas/numpy):** at startup, parse every JSON in `data/` into in-memory tables (matches, players, match_players, rounds, round_player_stats, kills, damage), derive team names and Red/Blue mapping from filenames, and cache aggregates. No database. New files dropped into `data/` are picked up on restart. Exposes a JSON REST API consumed by the frontend; also serves the catalog images.
- **Insight engine (backend):** deterministic, rule-based. Each insight (strength, weakness, training tip, strategy) is produced by a threshold on a stat and **must carry its evidence** (the number, sample size, and comparison baseline). Optional layer: an LLM may rewrite these facts as coach-style narrative (Claude API); the app must work fully without it and the LLM must never invent numbers.
- **Frontend (React + Vite + Tailwind):** SPA with client-side routing, one route per screen, global filter state shared across screens.

## 4. Global behavior (all screens)

- Language of the UI: **Portuguese-BR**. Code, comments, API field names and docs in English.
- **Visual style:** dark, VALORANT-inspired (dark background, red / off-white accents, angular shapes, agent/weapon/ability icons from the catalog). Original styling only: no Riot logos or proprietary fonts.
- **Global filters:** tournament/phase, map, date range. Filters persist across navigation.
- **Entity links:** every player, team, map and match name is a link to its screen.
- **Sample-size honesty:** show the number of matches/rounds behind every stat and flag low-sample values (e.g. < 3 maps or < 30 rounds) instead of presenting them as facts.
- **Empty/unknown states:** unknown agents/weapons, maps without minimap, missing data are handled with explicit messages, never a crash or a blank chart.
- Responsive for desktop first; must also be readable on a laptop-sized screen for the demo video.

## 5. Screens

Six screens: Home, Player Profile, Team Profile, Map Profile, Match Report, Action Plan. (The earlier standalone "Maps Analysis" was merged into Map Profile and Match Report.)

### 5.1 Home / Overview (`/`)
Entry point for all audiences.
- **Global search** for players (Riot ID), teams and maps → jumps to the profile.
- **Dataset KPIs:** matches, rounds, kills, players, teams, tournaments, date range.
- **Rankings / leaderboards:** top players (K/D, ADR, HS%, first kills) and top teams (win rate, round win rate); respects the tournament filter.
- **Tournament filter + recent matches:** Rush Series Esquenta, Esquenta 2, Inclusivo, Univavá phases; list of latest matches linking to Match Report.

### 5.2 Player Profile (`/jogador/:puuid`)
- Header: Riot ID, team(s), favorite agent, assigned role with confidence.
- **Role classification (behavioral heuristics, computed from data, never from the agent alone):**
  - *Entry Fragger*: Primeiro a entrar nos bombsites; busca o first blood ou morre dando informação para a troca (trade). Signals: share of rounds with the team's first duel, first-kill/first-death rate, early-round timing of kills/deaths, trades received.
  - *Lurker*: joga isolado, longe do time, flanqueia rotações. Signals: average distance to teammates (from `playerLocations`), late-round kills, kills away from the team's main position.
  - *IGL*: dita ritmo e estratégia. Not reliably derivable from this data; if shown, mark as "inferido" with low confidence (e.g. consistent presence in clutch/late calls, utility usage), otherwise omit.
  - *Suporte*: abre caminho com habilidades. Signals: assists, ability casts per round, assisted trades.
  - *Flex*: versátil, muda de agente/função. Signals: agent variety and spread of other role scores across maps.
  - *Anchor*: segura um bombsite sozinho na defesa. Signals: defense-side kills/deaths near the site, rounds held alone, low rotation.
  - Show the top-2 roles with a score/confidence, and the signals that justify them.
- **Stats:** team, K/D, assists, % de headshots (from `damage[]` head/body/leg), ADR, rounds played, **round opening** (first kill / first death rate, opening duel win %), clutch rounds, multi-kills.
- **Desempenho por arma comprada:** per weapon bought (`economy.weapon`): rounds, win rate, kills, K/D, HS%, damage per round; split by buy type (eco / force / full buy via `loadoutValue`/`spent`).
- **Kills e deaths por mapa:** per map, with link to a map view of the player's kills/deaths.
- **Agentes jogados** and agente favorito (most played), with performance per agent.
- **Pontos fortes / Pontos fracos** and **Recomendações de treino:** rule-based, each with evidence (see §3).

### 5.3 Team Profile (`/time/:teamName`)
- **Members:** roster with role badges (link to Player Profile); handle roster changes across tournaments.
- **Number of matches** and series; record (W/L), round win rate, attack vs defense win rate.
- **Every match:** list with score, map, date, opponent, link to Match Report.
- **Performance analysis per match** (trend over time, consistency across matches).
- **Performance analysis per map:** win rate, attack/defense split, best/worst maps.
- **Economy and tendencies:** eco / force / full-buy win rates, pistol rounds, plant-site preference, time-to-plant, post-plant and retake success.
- **Role composition:** which roles the team fields and gaps in the composition.
- **Pontos fortes / Pontos fracos** and **Sugestões de melhoria**, rule-based with evidence.

### 5.4 Map Profile (`/mapa/:mapName`)
- **Map image** (minimap from the catalog) with selectable layers:
  - Kill zones and death zones (heatmap), split by attack/defense.
  - **Blind spots, two toggleable layers:** (a) *dangerous zones*: grid cells where deaths far exceed kills per side; (b) *uncovered zones*: cells few players occupy/look at (from `playerLocations` + `viewRadians`) yet where enemies later appear or score kills from.
  - Plant locations and site preference.
- **Most used agents** and **most used weapons** on the map.
- **Classification:** better for attack or for defense (attacker vs defender round win rate, with sample size).
- Per-site stats (A/B/C): plant rate, defuse rate, retake rate.
- For maps without a minimap (Abyss, Summit): show only the non-spatial stats plus an explicit notice.

### 5.5 Match Report (`/partida/:matchId`)
- **Score** (team names from filename), map, date, tournament, duration, MVP.
- **Round timeline:** result of each round, side, plant/defuse, ceremony (Ace, Clutch, Flawless, Thrifty…), economy state.
- **Scoreboard:** per player K/D/A, ADR, HS%, first kills, agent.
- **Map + kills or deaths:** minimap with all kills/deaths of the match, filterable by round, player and team.
- **Kill replay map:** for each kill, show the map with **killer, victim and the trajectory between them**, plus the positions and view directions of the other alive players at that moment, weapon used and time in the round.
- **Improvements for each team:** rule-based suggestions for both teams, with evidence from this match.

### 5.6 Action Plan (`/plano`)
Impartial pre-match planner.
- **Inputs:** pick **Team A**, **Team B** and a **map**. A toggle flips the perspective (plan for A against B, or for B against A).
- **Agents recommendation** for the perspective team on that map, based on team history, map meta in the dataset and opponent tendencies.
- **Per round** (grouped by round type: pistol, eco, force, full buy; attack and defense):
  - Weapons recommendation.
  - Attack/Defense strategy (sites, timing, utility usage patterns that worked).
  - Weak points of the enemy.
  - Probable enemy strategy (site preference, early-round timing, buy pattern, positions seen in past rounds on the map).
- Every recommendation cites its evidence (numbers, sample size); low-sample recommendations are flagged.
- Optional LLM polish turns the structured plan into a coach-style narrative; the structured plan is always shown.

## 6. Derived metrics (shared definitions)

Keep one implementation per metric in the backend so all screens agree.
- **K/D, ADR** (damage per round), **HS%** = headshots / (headshots + bodyshots + legshots).
- **First kill / first death:** earliest kill in a round by `timeSinceRoundStartMillis`; opening duel win rate.
- **Trade:** a kill on the killer within a short window (default 5 s, configurable) after a teammate's death.
- **Buy type:** from `loadoutValue` / `spent` thresholds (eco / semi-eco / force / full buy), defined once in config.
- **Attack/defense side per round:** from `winningTeamRole` and halftime swap (overtime handled).
- **Clutch:** round won by a player when last alive vs ≥ 1 enemy.
- **Map coordinates → minimap pixels:** single utility using the catalog transform; discards out-of-bounds points.

## 7. Out of scope

- Real-time or in-match features, anything that gives live competitive advantage.
- Collecting data from outside the supplied JSON/catalog; integrations with Riot APIs.
- Accounts/authentication and persistence beyond in-memory data.
- Cosmetics (skins, cards, sprays, charms) from the catalog; ignore those folders.
