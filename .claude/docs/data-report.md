# Database Report — Hackathon Valorant (SEMCOMP / USP São Carlos)

Folder analyzed: `Dados .Json/`
Method: every file was parsed and the full schema, value distributions and numeric ranges were computed across all 336 files (not just a sample).

## 1. Overview

The "database" is not a SQL database. It is a collection of **336 JSON files**, one per played **map** (match), exported from Valorant **custom games** (tournament matches) in the Brazilian region.

| Metric | Value |
|---|---|
| Match files | 336 |
| Rounds | 6,618 |
| Kills | 46,753 |
| Damage records (who hit whom, per round) | 80,071 |
| Unique players (distinct `puuid`) | 413 |
| Date range (`gameStartMillis`) | 2026-06-06 → 2026-09-27 |
| Size on disk | ~193 MB (Univavá alone: 155 MB) |
| Region / mode | 100% `br`, 100% `CustomGame`, 100% Bomb (Spike) mode, 100% completed, 0% ranked |

### Folder structure

| Folder | Files | Dates in filenames |
|---|---|---|
| `Rush Series Esquenta` | 29 | 06–07/06/26 |
| `Rush Series Esquenta 2` | 26 | 20–21/06/26 |
| `Rush Series Inclusivo` | 13 | 08/08/26 |
| `Univavá/Classificatória 1` | 55 | 27–28/06/26 |
| `Univavá/Classificatória 2` | 39 | — |
| `Univavá/Classificatória 3` | 43 | — |
| `Univavá/Classificatória 4` | 62 | — |
| `Univavá/Fase de Grupos` | 69 | 19/09/26 onward |

**Filename convention:** `<TOURNAMENT>_<match no.>_<dd-mm-yy>_<team A>_<score A>_x_<score B>_<team B>_<map>.json`
Example: `RUSH2_002_20-06-26_fatec_pg_10_x_13_panterao_gaming_ascent.json`.
A suffix `a` / `b` on the match number (e.g. `UNIVAVA_G_001a`, `001b`) marks several maps of the same series. The team names and scores exist **only in the filename**, not inside the JSON (see §5).

## 2. File structure (top level)

Every file has exactly the same 5 top-level keys:

```
matchInfo     dict  – metadata for the map
players       list  – 10 players (11 in 22 files: one is an observer)
coaches       list  – 0, 1 or 2 coaches (empty in 156 files, 1 in 143, 2 in 37)
teams         list  – always 2 (Red and Blue): final result
roundResults  list  – one entry per round (the bulk of the data)
```

## 3. Fields and types

### 3.1 `matchInfo` (one object per file)

| Field | Type | Meaning / observed values |
|---|---|---|
| `matchId` | string (UUID) | Unique match ID |
| `mapId` | string | Map path. 10 maps seen: Ascent (86), Jam (82), Triad (75), Bonsai (36), Juliett (24), Infinity (13), Plummet (10), Foxtrot (5), Pitt (3), Canyon (2). Internal codenames, not the public map names |
| `gameVersion` | string | Game patch, 8 versions (`release-12.10` … `release-13.06`) |
| `gameLengthMillis` | int | Map duration in ms (685,840 – 4,576,800, i.e. ~11 to ~76 min) |
| `gameStartMillis` | int | Start timestamp, Unix epoch in ms |
| `region` | string | Always `br` |
| `provisioningFlowId` | string | Always `CustomGame` |
| `isCompleted` | bool | Always `true` |
| `isRanked` | bool | Always `false` |
| `gameMode` | string | Always the Bomb (Spike) mode |
| `seasonId` | string (UUID) | 3 distinct values (game acts) |
| `queueId`, `customGameName` | string | Always empty |
| `premierMatchInfo` | dict | Always empty `{}` |

`region`, `provisioningFlowId`, `isCompleted`, `isRanked`, `gameMode`, `queueId`, `customGameName` and `premierMatchInfo` are constant across the whole dataset, so they carry no analytical information.

### 3.2 `players[]` (10 per match)

| Field | Type | Notes |
|---|---|---|
| `puuid` | string | Player's global ID. Stable across matches (413 distinct) — the join key for everything else |
| `gameName`, `tagLine` | string | Riot ID (nickname + tag) |
| `teamId` | string | `Red` or `Blue`. `Neutral` for the 22 observers |
| `partyId` | string (UUID) | Party/lobby ID |
| `characterId` | string (UUID) or **null** | Agent played. 28 distinct agents. UUID only, no name in the data. `null` for observers |
| `competitiveTier` | int | **Always 0** (unranked) — useless in this dataset |
| `isObserver` | bool | `true` for 22 entries |
| `playerCard`, `playerTitle` | string (UUID) | Cosmetics, irrelevant for analysis |
| `accountLevel` | int | 25 – 1067 |
| `stats` | dict or **null** | Aggregate for the map. `null` for observers |

`stats` fields (all int): `score` (101–9836), `roundsPlayed` (13–36), `kills` (0–36), `deaths` (1–30), `assists` (0–23), `playtimeMillis`, and `abilityCasts` with `grenadeCasts`, `ability1Casts`, `ability2Casts`, `ultimateCasts` (counts of ability uses).

### 3.3 `coaches[]`

Only `puuid` (string) and `teamId` (`Red`/`Blue`). No name or other data.

### 3.4 `teams[]` (2 per match)

| Field | Type | Notes |
|---|---|---|
| `teamId` | string | `Red` / `Blue` |
| `won` | bool | Winner of the map |
| `roundsPlayed` | int | 13–36 (always equals the number of entries in `roundResults`) |
| `roundsWon`, `numPoints` | int | 0–19 (same value in all cases checked) |
| `rank` | int (1–2) | **Only in 22 files**, optional |

Maximum 19 rounds won implies overtime games exist (scores like 15x17).

### 3.5 `roundResults[]` (6,618 rounds; the core of the dataset)

Round-level fields:

| Field | Type | Notes |
|---|---|---|
| `roundNum` | int | 0-based (0–35) |
| `roundResult` / `roundResultCode` | string | `Eliminated` / `Elimination` (4,597), `Bomb defused` / `Defuse` (1,349), `Bomb detonated` / `Detonate` (522), `Round timer expired` / `""` (150) |
| `roundCeremony` | string | `CeremonyDefault` (4,977), `Flawless` (544), `Closer` (484), `Clutch` (247), `Thrifty` (215), `TeamAce` (84), `Ace` (67) |
| `winningTeam` | string | `Red` / `Blue` |
| `winningTeamRole` | string | `Attacker` (3,427) / `Defender` (3,191) |
| `bombPlanter` | string (puuid) or **null** | Null when no plant (1,965 rounds) |
| `plantSite` | string | `A` (2,040), `B` (1,603), `C` (1,010) or `""` when no plant. C appears only on 3-site maps |
| `plantRoundTime` | int (ms) | Time of the plant within the round. `0` when no plant |
| `plantLocation` | `{x, y}` int | Plant coordinates. **`(0,0)` when no plant** (1,965 rounds), not null |
| `plantPlayerLocations` | list or **null** | Position and view angle of every player at plant time |
| `bombDefuser` | string (puuid) or **null** | Null in 5,269 rounds (no defuse) |
| `defuseRoundTime`, `defuseLocation`, `defusePlayerLocations` | int / `{x,y}` / list-or-null | Same pattern as the plant. `defuseLocation` is `(0,0)` and `defuseRoundTime` is `0` without a defuse |
| `playerStats` | list (10) | One entry per player in the round (see below) |

#### `playerStats[]` (13,080 entries)

| Field | Type | Notes |
|---|---|---|
| `puuid` | string | Join key to `players` |
| `score` | int | Round score (0–1545) |
| `economy` | dict | `loadoutValue` (0–7500), `spent` (0–9750), `remaining` (0–9000) as ints; `weapon` and `armor` as string IDs (`""` = no armor/weapon) |
| `ability` | dict | `grenadeEffects`, `ability1Effects`, `ability2Effects`, `ultimateEffects` — **always `null`** in this dataset |
| `damage` | list | One record per target hit in the round (see below) |
| `kills` | list | One record per kill made by the player in the round (see below) |

`damage[]` item: `receiver` (puuid), `damage` (int, 0–2997), `headshots`, `bodyshots`, `legshots` (ints, number of hits by body part). Lets you compute headshot rate and damage per round.

`kills[]` item (46,753 total; a player makes 0–5 kills per round):

| Field | Type | Notes |
|---|---|---|
| `killer`, `victim` | string (puuid) | |
| `assistants` | list of puuid | 0–4 entries. (In the raw type scan the field appears as list/str because empty lists contain no elements) |
| `timeSinceRoundStartMillis` | int | 1,375 – 143,301 ms |
| `timeSinceGameStartMillis` | int | |
| `victimLocation` | `{x, y}` int | Where the victim died |
| `playerLocations` | list | Position (`location.x/y`), `viewRadians` (float, 0–2π, where the player was looking) and `puuid` of **all alive players at the kill moment** |
| `finishingDamage` | dict | `damageType` (`Weapon` 45,121 / `Ability` 1,238 / `Bomb` 327 / `Fall` 48 / `Melee` 15 / `Crush` 4), `damageItem` (weapon UUID, or `Ultimate`/`Ability1`/`Ability2`/`GrenadeAbility`, or `""`), `isSecondaryFireMode` (bool) |

## 4. Data types — summary

| Kind | Fields |
|---|---|
| **Identifiers (string/UUID)** | `matchId`, `puuid`, `partyId`, `characterId`, `seasonId`, `mapId`, weapon and armor IDs, `playerCard`, `playerTitle` |
| **Categorical** | `teamId`, `winningTeam`, `winningTeamRole`, `roundResult(Code)`, `roundCeremony`, `plantSite`, `damageType`, `mapId`, `gameVersion` |
| **Integer counters** | kills, deaths, assists, score, rounds, ability casts, headshots/bodyshots/legshots, accountLevel |
| **Integer, money** | `loadoutValue`, `spent`, `remaining` |
| **Integer, time (ms)** | `gameLengthMillis`, `gameStartMillis` (epoch), `plantRoundTime`, `defuseRoundTime`, `timeSince*Millis`, `playtimeMillis` |
| **Integer, spatial** | `x`, `y` in game-world units (no direct pixel coordinates) |
| **Float** | `viewRadians` (view direction, radians) |
| **Boolean** | `won`, `isObserver`, `isCompleted`, `isRanked`, `isSecondaryFireMode` |
| **Nullable** | `bombPlanter`, `bombDefuser`, `plantPlayerLocations`, `defusePlayerLocations`, `characterId` and `stats` (observers), `ability*Effects` (always) |

The data is hierarchical: Match → Round → Player → Kill/Damage. A relational model would be roughly `matches`, `players`, `match_players`, `rounds`, `round_player_stats`, `kills`, `damage_events`, joined by `matchId`, `roundNum` and `puuid`.

## 5. Data-quality notes and caveats

1. **Team names are not in the JSON.** Only `Red`/`Blue` and the players' Riot IDs. Team names and final score exist only in the filename. A `Red`/`Blue` side can swap role (attacker/defender) mid-game, so mapping a name to a color requires matching the filename score against `teams[].roundsWon`.
2. **No lookup tables.** Agents, weapons and armors are UUIDs only; map names are internal codenames (Jam, Triad, Bonsai, Juliett, Infinity, Plummet, Foxtrot, Pitt, Canyon). Translating them requires an external source (Valorant public API / community data), which I did not verify here.
3. **"Empty" is encoded in several ways:** `null` (planter/defuser/location lists), `""` (plantSite, armor, queueId), and `(0,0)` / `0` (plant and defuse location/time without an event). Filter on `bombPlanter is not null`, not on the coordinates.
4. **Coordinate outliers:** `location.x` goes down to about −50,000 in `playerLocations`, against a typical range of roughly −6,000 to +13,800. These probably come from players outside the playable area (e.g. dead/spectating or a teleport/fall); this is an inference and should be checked before plotting.
5. **`viewRadians` is mixed float/int** (11 integer values, probably exactly 0). Cast to float.
6. **Constant or empty columns** (no analytical value): `competitiveTier`, `region`, `provisioningFlowId`, `isCompleted`, `isRanked`, `gameMode`, `queueId`, `customGameName`, `premierMatchInfo`, all `ability*Effects`.
7. **Observers:** 22 matches have an 11th entry with `teamId = Neutral`, `stats = null`, `characterId = null`. Exclude with `isObserver`.
8. **Possible duplicates/overlap between tournaments:** the same `puuid` appears across folders (413 unique players in 3,360 player slots), which makes cross-tournament player tracking possible. I did not check for duplicate `matchId`s.
9. **Inconsistent game versions** (8 patches) can mean balance or map differences between matches.
10. **Pure Spike mode:** no ranked data and no rank information. Skill level has to be inferred from performance (kills, damage, headshot rate).

## 6. What the data allows (link to `brainstorm.md`)

The notes in `brainstorm.md` propose (a) analysis of the data and (b) an interactive environment to train aim from perceived mistakes. This dataset supports:

- **Aim / duel analysis:** headshot vs body vs leg ratio per player, damage per hit, `finishingDamage` by weapon, first-kill rate and trade kills (via `timeSinceRoundStartMillis`).
- **Positioning:** `victimLocation` and `playerLocations` give heatmaps of death spots and view angle at the moment of a kill (crosshair placement, via `viewRadians`).
- **Economy:** `loadoutValue`/`spent`/`remaining` per round to identify eco, force and full-buy rounds and the win rate of each.
- **Objective play:** plant/defuse timing and site preference (`plantSite`, `plantRoundTime`) per team.
- **Per-agent / per-map** performance (needs the UUID → name mapping).

Not available: raw mouse/crosshair movement, shot-by-shot data (only aggregated hit counts per target), utility effect data (always null), and any video. Aim *training* would therefore be driven by statistics (e.g. a player misses many body-to-head conversions or dies in specific spots), not by recorded aim traces.
