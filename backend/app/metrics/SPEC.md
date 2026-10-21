# Metric definitions (one implementation each, in `backend/app/metrics/`)

Owner: Stream A implements; everyone else calls. All functions take the `Store` (or a filtered slice of its tables) and
return plain numbers/`Stat`-shaped dicts `{value, sample_size, low_sample}`. Thresholds live in
`metrics/config.py` (single place, documented here). A metric that is not listed here must not be reimplemented
locally: add it here first (PR touching this file).

Conventions: `round_num` 0-based; "player rounds" = rows of `round_player_stats`; rates are 0..1 floats.

## Low-sample rule
`low_sample = sample_size < threshold`, with defaults in `config.LOW_SAMPLE`: **3 maps** for per-map/match-level stats,
**30 rounds** for round-level stats, **10 events** for event-level stats (plants, pistol rounds, clutches).

## Player metrics
| metric | definition |
|---|---|
| K/D | `sum(kills) / max(sum(deaths), 1)` from `match_players` |
| ADR | `sum(damage_dealt) / rounds` over `round_player_stats` |
| HS% | `headshots / (headshots + bodyshots + legshots)` from `damage` (not from kills) |
| First kill / first death | in each round, the earliest kill by `time_in_round_ms` (tie => lowest `kill_idx`); first-kill rate = first kills / player rounds |
| Opening duel win % | first kills / (first kills + first deaths) |
| Trade | a kill on the killer within `TRADE_WINDOW_MS = 5000` after a teammate's death; "traded death" is the victim side |
| Multi-kill | kills by a player in one round: 2K, 3K, 4K, 5K (ace) |
| Clutch | round won by the team where one player was the last alive on their team while >= 1 enemy was alive; credited to that player (derive from kills order) |

## Round / economy metrics
| metric | definition |
|---|---|
| Side per round | `store.side(...)` (from `winningTeamRole`; halftime at round 12, overtime alternates, already encoded) |
| Team loadout | mean `loadout_value` over the 5 players of the team in the round |
| Round type (buy type) | pistol if `round_num in {0, 12}`; otherwise by team loadout `L`: **eco** `L < 1600`; **semi_eco** `1600 <= L < 2900`; **force** `2900 <= L < 3900`; **full_buy** `L >= 3900`. **Calibrated 2026-10-21 on the full dataset** (11,892 non-pistol team-rounds: ~8% eco, 12% semi, 15% force, 65% full buy; clear breaks at those values; pistol mean 783). Constants in `metrics/config.py` |
| Round win rate | wins / rounds, by team, map, side, round type |
| Round-type transitions | `P(next_type \| prev_type, prev_result, loss_streak)` per team; rounds 0 and 12 are always pistol; fallback to the global dataset when the team has `< 30` transitions (flag `low_sample`) |
| Projected economy | expected team credits for the next round = `remaining(prev) + income`, income = 3000 win / 1900 + 500*loss_streak(cap 4) loss (+ plant bonus 300 if planted and lost) -- constants in `config.ECONOMY`; blended with what the team historically spends in that situation; same for the enemy |
| Round win probability | per team x map x side x round type (empirical), shrunk toward the global rate: `(wins + k*p_global) / (n + k)` with `k = 10`; used for the Action Plan base scenario |

## Objective metrics
| metric | definition |
|---|---|
| Plant rate | attack rounds with `planter` not null / attack rounds |
| Site preference | share of plants per `plant_site` |
| Time to plant | mean `plant_time_ms` over planted rounds |
| Post-plant win | planted rounds won by the attackers / planted rounds |
| Retake / defuse rate | defused rounds / planted rounds |

## Spatial
- `coords.to_minimap(map_codename, x, y) -> Point | None`: catalog transform (`u = y*xMultiplier + xScalarToAdd`, `v = x*yMultiplier + yScalarToAdd`), `None` for out-of-bounds (outside 0..1 or `x < -10000`) or maps without minimap.
- Heatmap grids: `grid_size x grid_size` over the minimap, counts then normalized by max.
- Blind spots: **danger** = per cell `deaths - kills` (clipped >= 0) normalized, minimum count `MIN_CELL_EVENTS = 5`; **uncovered** = cells with low presence/look coverage (`playerLocations` + `viewRadians`, 90-degree cone) that still produce enemy kills.

## Where each metric lives (`from app.metrics import ...`)
| module | functions |
|---|---|
| `config.py` | thresholds, `make_stat(value, n, kind)` (builds a `Stat` with `low_sample`), `classify_round` |
| `events.py` | `kill_events` (is_first, is_trade, death_traded, teamkill), `multikills`, `clutch_events` (every 1vX with `vs`, `won`) |
| `players.py` | `player_table(store)` (index puuid), `team_table(store)` (index team) |
| `rounds.py` | `team_rounds` (one row per team per round: side, won, round_type, enemy_type, credits, prev_type, prev_won, loss_streak), `next_type_distribution`, `project_next_credits` / `projected_economy`, `typical_loadout_by_type`, `round_win_probability` |
| `objective.py` | `objective_summary(store, team, map)`, `site_summary(store, map, team)` |
Filter first with `store.where(tournament=, map_name=, date_from=, date_to=, team=)`.

Implementation notes (verified on the real data)
- **Trade:** the avenged kill must come earlier in the round order (`order_p < order_k`), so an opening kill is never a trade.
- **Clutch:** a 1vX is any moment a team is down to one alive player while `X >= 1` enemies live; `won` = that team wins the round. All 247 rounds the game labels `CeremonyClutch` are among them (the game's flag is stricter), so use `vs` to filter (e.g. `vs >= 2`) when showing "clutches".
- **Economy:** `project_next_credits` = previous `remaining` + income (win 3000; loss 1900/2400/2900/3400 by streak; +300 plant bonus when attackers planted and lost; +200 per kill), capped at 9000; rounds 0 and 12 start at 800. Median error vs the real next-round credits is under 400 (tested).
- **Round type transitions:** key = (previous type, previous result, loss streak capped at 3); team-specific when it has >= 30 matching rounds, otherwise global (`source` says which).
- **Round win probability:** shrinkage `(wins + 10 * p_global) / (n + 10)`, `p_global` = dataset win rate for (side, round type[, enemy round type when >= 30 samples]).

## Testing
Each metric has a pytest against hand-computed values from the mini store (3 real files); changing a threshold requires updating this table.
