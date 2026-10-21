"""Tiny Store built from a few real files, so B/C/D can develop before Stream A's real loader lands.

This is a deliberately simple reference implementation of `app/data/SCHEMA.md`. Stream A's `loader.py` produces the
same tables (adding caching, the full filename parser and catalog lookups); analytics code must not notice the swap.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from app.data.store import Store
from app.deps import DATA_DIR

FILE_RE = re.compile(
    r"^(?P<tour>[A-Z0-9]+)_(?:(?P<phase>[A-Z0-9]+)_)?(?P<no>\d+[ab]?)_(?P<d>\d\d)-(?P<m>\d\d)-(?P<y>\d\d)_"
    r"(?P<a>.+)_(?P<sa>\d+)_x_(?P<sb>\d+)_(?P<b>.+)_(?P<map>[a-z]+)\.json$"
)
MAP_NAMES = {"Ascent": "Ascent", "Jam": "Lotus", "Triad": "Haven", "Bonsai": "Split", "Juliett": "Sunset",
             "Infinity": "Abyss", "Plummet": "Summit", "Foxtrot": "Breeze", "Pitt": "Pearl", "Canyon": "Fracture"}


def default_files() -> list[Path]:
    """Three deterministic real files (different maps/tournaments)."""
    picks = []
    for pat in ("Rush Series Esquenta 2/RUSH2_002*", "Univav*/Classificat*ria 1/*lotus.json", "Univav*/Classificat*ria 1/*haven.json"):
        picks.append(sorted(DATA_DIR.glob(pat))[0])
    return picks


def _team_names(path: Path, teams: list[dict]) -> tuple[str, str, int, int, dict[str, str]]:
    m = FILE_RE.match(path.name)
    a, b = m["a"].replace("_", " ").title(), m["b"].replace("_", " ").title()
    sa, sb = int(m["sa"]), int(m["sb"])
    won = {t["teamId"]: t["roundsWon"] for t in teams}
    color_a = "Red" if won["Red"] == sa and won["Blue"] == sb else "Blue"  # ties handled by A's loader (rosters)
    other = "Blue" if color_a == "Red" else "Red"
    return a, b, sa, sb, {color_a: a, other: b}


def build_mini_store(files: list[Path] | None = None) -> Store:
    files = files or default_files()
    matches, mps, rounds, rps, kills, damage = [], [], [], [], [], []
    for path in files:
        d = json.loads(path.read_text())
        info, fm = d["matchInfo"], FILE_RE.match(path.name)
        mid = info["matchId"]
        a, b, sa, sb, color_to_team = _team_names(path, d["teams"])
        rel = path.relative_to(DATA_DIR).parts
        matches.append(dict(
            match_id=mid, map_codename=info["mapId"].split("/")[-1], map_name=MAP_NAMES[info["mapId"].split("/")[-1]],
            tournament=rel[0], phase=rel[1] if len(rel) > 2 else None, match_no=fm["no"],
            date=f"20{fm['y']}-{fm['m']}-{fm['d']}", game_start_ms=info["gameStartMillis"],
            duration_ms=info["gameLengthMillis"], team_a=a, team_b=b, score_a=sa, score_b=sb,
            red_team=color_to_team["Red"], blue_team=color_to_team["Blue"], source_file=path.name,
        ))
        team_of = {}
        for p in d["players"]:
            if p["isObserver"]:
                continue
            s = p["stats"]
            team_of[p["puuid"]] = p["teamId"]
            mps.append(dict(
                match_id=mid, puuid=p["puuid"], riot_id=f"{p['gameName']}#{p['tagLine']}", team_color=p["teamId"],
                team_name=color_to_team[p["teamId"]], agent_id=p["characterId"], score=s["score"],
                rounds_played=s["roundsPlayed"], kills=s["kills"], deaths=s["deaths"], assists=s["assists"],
                grenade_casts=s["abilityCasts"]["grenadeCasts"], ability1_casts=s["abilityCasts"]["ability1Casts"],
                ability2_casts=s["abilityCasts"]["ability2Casts"], ultimate_casts=s["abilityCasts"]["ultimateCasts"],
            ))
        for r in d["roundResults"]:
            n, win = r["roundNum"], r["winningTeam"]
            lose = "Blue" if win == "Red" else "Red"
            att, de = (win, lose) if r["winningTeamRole"] == "Attacker" else (lose, win)
            planted = r["bombPlanter"] is not None
            rounds.append(dict(
                match_id=mid, round_num=n, half=1 if n < 12 else 2 if n < 24 else 3, result=r["roundResult"],
                result_code=r["roundResultCode"] or None, ceremony=r["roundCeremony"], winning_color=win,
                winning_team=color_to_team[win], attacker_color=att, attacker_team=color_to_team[att],
                defender_team=color_to_team[de], planter=r["bombPlanter"], plant_site=r["plantSite"] or None,
                plant_time_ms=r["plantRoundTime"] if planted else None,
                plant_x=r["plantLocation"]["x"] if planted else None, plant_y=r["plantLocation"]["y"] if planted else None,
                defuser=r["bombDefuser"], defuse_time_ms=r["defuseRoundTime"] if r["bombDefuser"] else None,
            ))
            for ps in r["playerStats"]:
                if ps["puuid"] not in team_of:
                    continue
                e, dm = ps["economy"], ps["damage"]
                rps.append(dict(
                    match_id=mid, round_num=n, puuid=ps["puuid"], team_color=team_of[ps["puuid"]],
                    side="attack" if team_of[ps["puuid"]] == att else "defense", score=ps["score"],
                    loadout_value=e["loadoutValue"], spent=e["spent"], remaining=e["remaining"],
                    weapon_id=e["weapon"] or None, armor_id=e["armor"] or None,
                    damage_dealt=sum(x["damage"] for x in dm), headshots=sum(x["headshots"] for x in dm),
                    bodyshots=sum(x["bodyshots"] for x in dm), legshots=sum(x["legshots"] for x in dm),
                    kills_n=len(ps["kills"]),
                ))
                for x in dm:
                    damage.append(dict(match_id=mid, round_num=n, giver=ps["puuid"], receiver=x["receiver"],
                                       damage=x["damage"], headshots=x["headshots"], bodyshots=x["bodyshots"],
                                       legshots=x["legshots"]))
                for k in ps["kills"]:
                    fd = k["finishingDamage"]
                    locs = [dict(puuid=pl["puuid"], x=pl["location"]["x"], y=pl["location"]["y"],
                                 view_radians=float(pl["viewRadians"])) for pl in k["playerLocations"]]
                    kills.append(dict(
                        match_id=mid, round_num=n, kill_idx=len(kills), time_in_round_ms=k["timeSinceRoundStartMillis"],
                        time_in_game_ms=k["timeSinceGameStartMillis"], killer=k["killer"], victim=k["victim"],
                        killer_color=team_of.get(k["killer"]), victim_color=team_of.get(k["victim"]),
                        victim_x=k["victimLocation"]["x"], victim_y=k["victimLocation"]["y"],
                        damage_type=fd["damageType"], damage_item=fd["damageItem"] or None,
                        secondary_fire=fd["isSecondaryFireMode"], assistants=list(k["assistants"]), player_locations=locs,
                    ))
    return Store(*(pd.DataFrame(t) for t in (matches, mps, rounds, rps, kills, damage)))
