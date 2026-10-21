# Store schema (normalized tables)

Source of truth for column names/dtypes. `Store` (in `store.py`) holds these six pandas DataFrames. Stream A's
`loader.py` fills them from `data/`; `tests/fixtures/mini_store.py` is a reference implementation built from 3 real
files (`build_mini_store()`), and `tests/test_mini_store.py` checks the invariants below.

Conventions
- `round_num` is **0-based** as in the raw data (the API shows 1-based).
- `team_color` is `Red`/`Blue`; `team_name` comes from the filename (see "Team mapping"). **Always prefer `team_name`**.
- "Empty" is `None` (never `""`, `0` or `(0,0)`): no plant => `plant_*` are `None`; no armor => `armor_id` is `None`.
- Observers (`isObserver`) are dropped everywhere. Coordinates are raw game units (use `coords.py` to get 0..1 minimap points).
- IDs (`agent_id`, `weapon_id`, `armor_id`) are the raw UUIDs, resolved to names only at the API edge via `catalog.py`.

## matches (one row per map)
| column | dtype | notes |
|---|---|---|
| match_id | str | `matchInfo.matchId` (primary key) |
| map_codename / map_name | str | `Jam` / `Lotus` (see CLAUDE.md for the mapping) |
| tournament / phase | str / str\|None | top folder under `data/` / second-level folder (e.g. `Classificatória 1`) |
| match_no | str | e.g. `002`, `001a` |
| date | str | ISO `YYYY-MM-DD`, from the filename |
| game_start_ms, duration_ms | int | epoch ms / `gameLengthMillis` |
| team_a, team_b | str | names in filename order |
| score_a, score_b | int | filename score |
| red_team, blue_team | str | which name is Red / Blue (matched via `teams[].roundsWon`) |
| source_file | str | file name |

## match_players (one row per player per map, observers excluded)
`match_id, puuid, riot_id ("name#tag"), team_color, team_name, agent_id (str|None), score, rounds_played, kills, deaths, assists, grenade_casts, ability1_casts, ability2_casts, ultimate_casts` (ints).

## rounds (one row per round)
| column | dtype | notes |
|---|---|---|
| match_id, round_num | str, int | key |
| half | int | 1 (rounds 0-11), 2 (12-23), 3 (overtime, 24+) |
| result / result_code | str / str\|None | `Bomb defused`, `Eliminated`, ... |
| ceremony | str | `CeremonyDefault`, `CeremonyClutch`, `Flawless`, `Thrifty`, ... |
| winning_color / winning_team | str | |
| attacker_color / attacker_team / defender_team | str | from `winningTeamRole` (halftime and overtime already resolved) |
| planter, defuser | str\|None | puuid; `None` when no plant/defuse |
| plant_site | str\|None | `A`/`B`/`C` |
| plant_time_ms, defuse_time_ms | int\|None | time within the round |
| plant_x, plant_y | int\|None | game units |

## round_player_stats (one row per player per round)
`match_id, round_num, puuid, team_color, side ("attack"|"defense"), score, loadout_value, spent, remaining, weapon_id (str|None), armor_id (str|None), damage_dealt, headshots, bodyshots, legshots, kills_n` (ints). Derived buy type per player/team comes from `metrics` (never recomputed elsewhere).

## kills (one row per kill)
| column | dtype | notes |
|---|---|---|
| match_id, round_num, kill_idx | str, int, int | `kill_idx` is a running index in the file |
| time_in_round_ms, time_in_game_ms | int | |
| killer, victim | str | puuid |
| killer_color, victim_color | str\|None | `None` when the killer is not a player (e.g. bomb) |
| victim_x, victim_y | int | game units |
| damage_type | str | `Weapon`, `Ability`, `Bomb`, `Fall`, `Melee`, `Crush` |
| damage_item | str\|None | weapon UUID or `Ultimate`/`Ability1`/`Ability2`/`GrenadeAbility` |
| secondary_fire | bool | |
| assistants | list[str] | puuids |
| player_locations | list[dict] | `{puuid, x, y, view_radians}` for everyone alive at the kill (outliers kept raw; filter in `coords.py`) |

## damage (one row per giver/receiver per round)
`match_id, round_num, giver, receiver, damage, headshots, bodyshots, legshots`.

## Team mapping
Names come from `<TOURNAMENT>_<no>_<dd-mm-yy>_<team A>_<score A>_x_<score B>_<team B>_<map>.json`. Mapping a name to Red/Blue: the colour whose `roundsWon` equals that name's filename score. If both colours have the same `roundsWon` (a tied score), resolve by comparing rosters with the team's other matches; unresolved files are logged and skipped, never fatal. (`mini_store.py` only does the score match.)

## Store interface (what analytics code may call)
- Tables: `store.matches`, `.match_players`, `.rounds`, `.round_player_stats`, `.kills`, `.damage`.
- `store.team_of(match_id, puuid) -> team_name | None`
- `store.color_of(match_id, team_name) -> "Red"|"Blue"|None`
- `store.side(match_id, round_num, team_name) -> "attack"|"defense"|None`
- `store.players_of(match_id, team_name)`, `store.matches_of_team(team_name)`, `store.matches_of_player(puuid)`
- Stream A may **add** helpers (announce in the plan); changing/removing an existing column or method is a contract change.
