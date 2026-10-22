# API contract (frozen in Phase 0)

Source of truth for response shapes: Pydantic models in `backend/app/schemas/` (also browsable at `/docs` when the backend runs).
Examples: `contract/fixtures/<endpoint>.json` (regenerate with `backend/.venv/bin/python contract/make_fixtures.py`).
Frontend types: `frontend/src/api/types.ts` mirrors the models (Stream E keeps them in sync).
**Changing a shape = a PR touching `schemas/`, `contract/` and `types.ts`, announced to all streams.** Adding an optional field is fine; removing/renaming is a breaking change.

## Conventions
- Base path `/api`; JSON; field names `snake_case`; UI text fields end in `_pt` (Portuguese-BR), everything else is language-neutral.
- Every stat that is a rate/average is a `Stat {value, sample_size, low_sample}`; screens must show `sample_size` and mark `low_sample`.
- Coordinates in API payloads are already minimap-normalized `Point {x, y}` in 0..1 (x right, y down). Maps with `has_minimap=false` return no points.
- Unknown agent/weapon: `name: null` (UI shows "Agente/Arma desconhecido(a)"); `name_inferred: true` when a name was guessed.
- Rounds are **1-based** in the API (`number`, `round`), 0-based in the Store.
- Team routes use the team name as the path segment (URL-encoded). Map routes use the public name (`Lotus`, not `Jam`).
- Global filters (optional query params wherever listed): `tournament` (id), `map` (public name), `date_from`, `date_to` (ISO dates). `tournament` may carry a phase prefix after a slash: `UNIVAVA/Classificat` (qualifiers 1-4) or `UNIVAVA/Fase` (group stage); the frontend builds these from `/api/meta` `tournaments[].phases`.
- Additive fields added while building the screens from Figma (Stream E): leaderboard rows carry `kd/adr/hs_pct/first_kills` (players) and `wins/losses` (teams); `PlayerStats` has `shots/first_kills/first_deaths/traded_deaths`; `PlayerProfile.roles` now lists **all five** roles sorted by score (the UI shows the top 2 as badges) and `weapons` also has aggregated rows (`buy_type: null`) per weapon; `RosterMember` has `kd/adr`; `TrendPoint` has `map_name`. Leaderboards rank players with >= 5 maps.
- Errors: standard FastAPI `{"detail": "..."}` with 404 for unknown entities, 422 for bad params.
- Static catalog images: `/assets/<Folder>/<id>.png` (served from `public_catalog/`); API payloads already carry full `icon_url`/`minimap_url`.
- **List pictures:** `icon_url` (agents, weapons) and `MapRef.thumb_url` point to `GET /api/thumb/{Characters|Weapons|Maps}/{file-stem}?w=<px>`, small cached PNG thumbnails (the originals are ~1024px / 850 KB). `null`/missing => the UI shows a neutral tile (unknown agents/weapons, and Abyss/Summit which have no catalog image). Every list that names an agent, weapon or map must show its picture beside the name (Figma rule, `CLAUDE.md`).

## Endpoints
| Method + path | Query / body | Response model | Owner |
|---|---|---|---|
| GET `/api/health` | | `{status}` | A |
| GET `/api/meta` | | `MetaResponse` | A |
| GET `/api/search` | `q` | `SearchResponse` | A |
| GET `/api/leaderboards` | `tournament` | `LeaderboardsResponse` | A |
| GET `/api/matches` | `tournament, map, team, date_from, date_to, limit, offset` | `MatchListResponse` | A |
| GET `/api/players/{puuid}` | `tournament, map` | `PlayerProfile` | B |
| GET `/api/teams` | `tournament` | `TeamListResponse` | B |
| GET `/api/teams/{name}` | `tournament, map` | `TeamProfile` | B |
| GET `/api/maps` | `tournament` | `MapListResponse` | C |
| GET `/api/maps/{name}` | `tournament` | `MapProfile` | C |
| GET `/api/maps/{name}/heatmap` | `side=attack\|defense\|both, grid_size, tournament` | `HeatmapResponse` | C |
| GET `/api/matches/{id}` | | `MatchReport` | C |
| GET `/api/matches/{id}/kills` | `round, player, team` | `KillsResponse` | C |
| POST `/api/plan` | body `PlanRequest` (`use_llm` optional) | `PlanResponse` (`text_source`, `notes_pt` additive) | D |
| GET `/api/plan/capabilities` | | `PlanCapabilities` `{llm, model}` | D |
| POST `/api/plan/report` | body `PlanRequest` (`use_llm` optional) | `application/pdf` attachment; headers `X-Report-Source` (`llm`\|`rules`) and `X-Report-Note` | D |

Additive (Stream D): `GET /api/players/{id}`, `/api/teams/{name}`, `/api/maps/{name}` and `/api/matches/{id}` take `insights=rules|llm` (default `rules`) and return `insights_source` (`rules` | `llm`). With `llm` the model picks and words the insights from a fact packet and the answer is validated against it; when the LLM is off, fails or returns nothing the response is the rule-based one and says `rules`.

## Insight engine entry points (Python, not HTTP)
`insights.engine.for_player(PlayerProfile) / for_team(TeamProfile) / for_match(MatchReport) / for_map(MapProfile)`; implemented by Stream D (`for_map` also accepts an optional `store`). Routers call them after building the stats so the engine never touches raw data.

## Stub behaviour
Until a stream replaces its router, the endpoint returns the matching fixture, so every screen can be built against a live backend or the frontend mock layer (`VITE_USE_MOCKS=1`) with identical shapes.
