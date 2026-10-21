# Public Catalog Report — Hackathon Valorant

Folder analyzed: `Public Catalog/` (inside the repo)
Method: the whole folder was inventoried, `PublicContentCatalog.json` was parsed in full, and every ID in the 336 match files was cross-referenced against it.

## 1. Overview

The catalog is a **static dictionary of game content**: one metadata file (`PublicContentCatalog.json`, 9.4 MB) plus ~7,000 image assets organized by content type. It contains **no match data**. Its purpose is to translate the UUIDs found in `Dados .Json/` into names, and to supply images and reference values.

| Item | Value |
|---|---|
| Catalog version | `08.09.00.2521387` |
| Total size | ~500 MB (6,768 files) |
| Files | 1 JSON + PNG images only |
| Last modified | May 14, 2024 |
| Languages in the JSON | 18 locales (`en-US`, `pt-BR`, `es-ES`, `ja-JP`, ... ) |

**Important:** the catalog version (08.09) is **older** than the matches (patch 12.10 → 13.06). Content added after it is missing from the catalog (see §4).

## 2. `PublicContentCatalog.json`

Top-level keys (all are lists of objects, except `version`):

| Key | Items | Fields (besides `id`, `label`, `name`) |
|---|---|---|
| `characters` (agents) | 25 | `description`, `abilities` (`Ability1`, `Ability2`, `Grenade`, `Ultimate`, plus `Passive` on 2 agents; each with `name`, `description`) |
| `weapons` | 34 | `category` (Melee, Sidearm, SMG, Rifle, Sniper, Shotgun, Heavy, Hidden), `stats` |
| `weaponSkins` | 918 | `weaponId`, `defaultChromaId`, `chromas` (1,867), `levels` (1,637) |
| `maps` | 15 | `coordinates` (flavor text), `xMultiplier`, `xScalarToAdd`, `yMultiplier`, `yScalarToAdd` |
| `playerCards` | 552 | — |
| `playerTitles` | 208 | `titleText` |
| `charms` | 513 | `levels` |
| `sprays` | 590 | `levels` |
| `gameModes` | 10 | `duration` |
| `acts` | 33 | `type` (`episode` / `act`) — Closed Beta, Episodes 1–8 with Acts 1–3 |
| `characterRoles` | 4 | `description` (Duelist, Initiator, Sentinel, Controller) |
| `matchmakingQueues` | 12 | `description` (Competitive, Custom Game, Premier, Unrated, Spike Rush, ...) |

Every `name` / `description` is an object `{defaultText, localizedByCulture: {<locale>: text}}`. The IDs are UPPERCASE UUIDs.

### 2.1 Content details

- **Agents (25):** Gekko, Fade, Breach, Deadlock, Raze, Chamber, KAY/O, Skye, Cypher, Sova (appears twice with different IDs), Killjoy, Harbor, Viper, Phoenix, Astra, Brimstone, Iso, Clove, Neon, Yoru, Sage, Reyna, Omen, Jett. **No agent→role field**: roles exist as a separate list with no link to the agents.
- **Weapons (34):** 19 are the normal buy-menu weapons (Classic, Shorty, Frenzy, Ghost, Sheriff, Stinger, Spectre, Bucky, Judge, Bulldog, Guardian, Phantom, Vandal, Marshal, Outlaw, Operator, Ares, Odin, plus Melee). The rest are hidden/event items (Spike, KAY/O Core, Overdrive, Headhunter, Tour De Force, Golden Gun, Snowball Launcher, ...).
- **Weapon `stats`:** `fireMode`, `fireRate`, `magazineSize`, `runSpeedMultiplier`, `equipTimeSeconds`, `reloadTimeSeconds`, `firstBulletAccuracy`, `shotgunPelletCount`, `wallPenetration`, `damageRanges` (head/body/leg damage by distance range), ADS stats and alt-fire info. Example, Vandal: 9.75 shots/s, 25 rounds, 160 head / 40 body / 34 leg damage.
- **Maps (15):** Ascent, Split, Fracture, Bind, Breeze, District, Kasbah, Drift, Piazza, Lotus, Sunset, Pearl, Icebox, The Range, Haven. Ten have real coordinate transforms; **District, Kasbah, Drift, Piazza, The Range have all four values at 0**.
- **Game modes (10):** Standard, Deathmatch, Escalation, Team Deathmatch, Onboarding, Replication, Spike Rush, The Range, Snowball Fight, Swiftplay.
- **No data on:** armor items, ranks/tiers, economy prices, ability costs, map callouts or site positions, round/economy rules.

## 3. Image folders

| Folder | Files | Size | What it is (naming) |
|---|---|---|---|
| `Abilities/` | 102 | 1.1 MB | `<agentId>_Ability1/Ability2/Grenade/Ultimate.png` (25 each) + 2 `_Passive.png` |
| `CharacterRoles/` | 4 | 16 KB | Role icons |
| `Characters/` | 74 | 66 MB | Agent portraits: `.png`, `_small.png`, `_full.png` (24 full) |
| `Charms/` | 513 | 8.2 MB | Gun buddies |
| `GameModes/` | 8 | 60 KB | Mode icons |
| `Maps/` | 44 | 49 MB | Per map: `.png` (minimap), `_listview.png`, `_splash.png` |
| `PlayerCards/` | 2,208 | 197 MB | 552 cards × 4 sizes: `.png`, `_small`, `_large`, `_wide` |
| `Sprays/` | 590 | 13 MB | Spray images |
| `Weapons/` | 66 | 1.5 MB | `.png` and `_killstream.png` (33 each) |
| `WeaponSkins/` | 3,158 | 161 MB | 1,867 skin images + 1,291 `_swatch.png` |

Image files are named by the UUID of the item they depict. `Maps/<mapId>.png` is the top-down minimap, which is what can be used to plot kill/death positions. (I confirmed the file naming and counts; I did not open the images.)

## 4. How the catalog matches the match data

I looked up every ID used in the 336 match files.

| Match-data field | Resolved against catalog | Not resolved |
|---|---|---|
| **`characterId`** (agent) | 24 of 28 distinct agent IDs. 100% of the 8 most-played agents resolve | 4 IDs (**140 + 51 + 6 + 1 = 198 player-slots**, 5.9%): `efba5359-…`, `df1cb487-…`, `b444168c-…`, `92eeef5d-…`. They are agents released after catalog v08.09. |
| **`economy.weapon`** and **`finishingDamage.damageItem`** | 18 of 20 weapon IDs; the whole common arsenal (Vandal, Phantom, Sheriff, ...) | `410B2E0B-…` (1,678 buys, 949 kills as the finishing weapon, ranking 8th by purchases) and `8DB0A1BF-…` (1 use). Newer weapons not in the catalog. |
| **`economy.armor`** | **None of 3 armor IDs** (`822BCAB2…` 40,524 uses, `4DEC83D5…` 10,799, `B1B9086D…` 4,302) | The catalog has no armor entries. `""` = no armor (10,555) |
| **`mapId`** | **None directly**: the match uses internal codenames (`/Game/Maps/Jam/Jam`), and the catalog has no codename field | — |
| **`playerCard`** | 2,036 of 3,382 slots (60%) | 1,346 |
| **`playerTitle`** | 2,067 of 3,382 slots (61%) | 1,315 |
| **`seasonId`** | **None** (0 of 3 values match the 33 `acts` IDs) | all 3 |
| `gameMode`, `queueId` | not applicable (constant / empty in the matches) | — |

Extra identifiers in `finishingDamage.damageItem`: non-UUID values `Ultimate`, `Ability1`, `Ability2`, `GrenadeAbility` need no lookup.

### 4.1 Map codename → name (derived from the match files, not the catalog)

The catalog does not translate map codenames, but every match filename ends with the map name, and the mapping turns out to be 1:1 with no conflicts across all 336 files:

| Codename in JSON | Name in filename | Matches |
|---|---|---|
| Ascent | Ascent | 86 |
| Jam | Lotus | 82 |
| Triad | Haven | 75 |
| Bonsai | Split | 36 |
| Juliett | Sunset | 24 |
| Infinity | Abyss | 13 |
| Plummet | Summit | 10 |
| Foxtrot | Breeze | 5 |
| Pitt | Pearl | 3 |
| Canyon | Fracture | 2 |

**Abyss** and **Summit** (23 matches) are not in the catalog, so they have **no minimap and no coordinate transform** there. Of the 10 maps played, the catalog has coordinate multipliers for Ascent, Lotus, Haven, Split, Sunset, Breeze, Pearl and Fracture (8 maps, 313 matches). The other 23 matches (Abyss and Summit) have no transform.

### 4.2 Using the coordinate transform (not verified)

Each map has `xMultiplier`, `xScalarToAdd`, `yMultiplier`, `yScalarToAdd`. The catalog does not document the formula. The usual reading is a normalized minimap position `u = y × xMultiplier + xScalarToAdd`, `v = x × yMultiplier + yScalarToAdd` (note the axis swap), then scaling by image size. I did **not** test this against the images; it should be validated by plotting plant positions on a minimap before relying on it.

## 5. What this adds to the hackathon work

- **Names for the analysis:** agent names for ~94% of player slots, and weapon names for all but one weapon ID, enough for charts and the pitch.
- **Weapon reference values:** fire rate, magazine, damage-by-range. Useful to compare a player's real head/body/leg hit mix against what each weapon can do, and to explain recommendations.
- **Maps for visualization:** minimaps and coordinate transforms to build heatmaps of deaths and plants (8 of 10 played maps).
- **Role grouping is not possible from the catalog alone**, since agents have no role field.
- **Interface assets:** portraits, ability icons, weapon icons and role icons for a polished dashboard.

## 6. Caveats

1. **Rules check (important).** The challenge PDF says match data must come "exclusively" from the JSON files supplied by the organization and forbids collecting external data. This catalog is already inside the repo (apparently supplied with the materials), so *using it as a lookup table* looks consistent with the rules, but I can't confirm who provided it. **Ask the organization (Discord ticket) to confirm** before building on it, and do not fill the unresolved IDs from outside sources.
2. **Outdated version:** 4 agents (198 player-slots) and 2 weapons (the 410B2E0B weapon is heavily used) can't be named. Options: label them "Unknown agent/weapon N", or infer from the data (e.g. cost from `spent`/`loadoutValue`, or kill patterns). Inferred names must be marked as inferred.
3. **Armor IDs have no names.** They can be told apart by price/usage pattern, but that would be an inference.
4. **Duplicate Sova** (two IDs in the catalog); only `320b2a48-…` appears in the matches.
5. **Cosmetics are mostly irrelevant** to performance analysis (cards, titles, charms, sprays, skins = ~6,470 of the 6,768 files and ~380 MB). They can be ignored for the project.
6. **Size:** ~500 MB; if the repo is published or zipped for submission, exclude the cosmetic folders.
