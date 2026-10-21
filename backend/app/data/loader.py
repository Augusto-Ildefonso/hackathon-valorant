"""Load every JSON under `data/` into the normalized tables of `SCHEMA.md`. Owner: Stream A.

`load_store()` is the single entry point. Files are parsed in parallel, team names (filename only) are mapped to
Red/Blue by score with a roster-vote fallback, and the result is pickled under `.cache/` keyed by file mtimes so
restarts are fast. New files dropped into `data/` are picked up on the next start.
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import orjson
import pandas as pd

from ..deps import DATA_DIR, REPO_ROOT
from .catalog import MAP_NAMES
from .filenames import parse_filename, tournament_and_phase
from .store import Store

log = logging.getLogger(__name__)

LOADER_VERSION = 2  # bump when the table layout changes
CACHE_DIR = REPO_ROOT / ".cache"
TABLES = ("matches", "match_players", "rounds", "round_player_stats", "kills", "damage")


def _color_for_scores(teams: list[dict], score_a: int, score_b: int) -> str | None:
    """Colour of team A (filename order) by matching the filename score with `teams[].roundsWon`."""
    won = {t["teamId"]: t["roundsWon"] for t in teams}
    fits_red = won.get("Red") == score_a and won.get("Blue") == score_b
    fits_blue = won.get("Blue") == score_a and won.get("Red") == score_b
    if fits_red != fits_blue:
        return "Red" if fits_red else "Blue"
    return None  # tied or inconsistent: resolved by rosters later


def parse_match_file(args: tuple[str, str]) -> dict:
    """Parse one file into row dicts (no team names yet: the colour mapping is resolved once all files are read)."""
    path, data_dir = Path(args[0]), Path(args[1])
    d = orjson.loads(path.read_bytes())
    meta = parse_filename(path.name)
    info = d["matchInfo"]
    mid = info["matchId"]
    codename = info["mapId"].split("/")[-1]
    tournament, phase = tournament_and_phase(path, data_dir)

    color_a = _color_for_scores(d["teams"], meta.score_a, meta.score_b)
    match = dict(
        match_id=mid, map_codename=codename, map_name=MAP_NAMES.get(codename, meta.map_name),
        tournament=tournament, tournament_code=meta.tournament_code, phase=phase, match_no=meta.match_no,
        series_no=meta.series_no, date=meta.date, game_start_ms=info["gameStartMillis"],
        duration_ms=info["gameLengthMillis"], team_a=meta.team_a, team_b=meta.team_b,
        score_a=meta.score_a, score_b=meta.score_b, source_file=path.name,
        _color_a=color_a,  # Red/Blue of team A, or None when unresolved
    )
    mps, rounds, rps, kills, damage = [], [], [], [], []
    color_of: dict[str, str] = {}
    for p in d["players"]:
        if p["isObserver"]:
            continue
        s, ac = p["stats"], p["stats"]["abilityCasts"]
        color_of[p["puuid"]] = p["teamId"]
        mps.append(dict(
            match_id=mid, puuid=p["puuid"], riot_id=f"{p['gameName']}#{p['tagLine']}", team_color=p["teamId"],
            agent_id=(p["characterId"] or "").lower() or None, score=s["score"], rounds_played=s["roundsPlayed"],
            kills=s["kills"], deaths=s["deaths"], assists=s["assists"], grenade_casts=ac["grenadeCasts"],
            ability1_casts=ac["ability1Casts"], ability2_casts=ac["ability2Casts"], ultimate_casts=ac["ultimateCasts"],
        ))
    kill_idx = 0
    for r in d["roundResults"]:
        n, win = r["roundNum"], r["winningTeam"]
        lose = "Blue" if win == "Red" else "Red"
        att, dfn = (win, lose) if r["winningTeamRole"] == "Attacker" else (lose, win)
        planted = r["bombPlanter"] is not None
        rounds.append(dict(
            match_id=mid, round_num=n, half=1 if n < 12 else 2 if n < 24 else 3, result=r["roundResult"],
            result_code=r["roundResultCode"] or None, ceremony=r["roundCeremony"], winning_color=win,
            attacker_color=att, defender_color=dfn, planter=r["bombPlanter"], plant_site=r["plantSite"] or None,
            plant_time_ms=r["plantRoundTime"] if planted else None,
            plant_x=r["plantLocation"]["x"] if planted else None,
            plant_y=r["plantLocation"]["y"] if planted else None,
            defuser=r["bombDefuser"], defuse_time_ms=r["defuseRoundTime"] if r["bombDefuser"] else None,
        ))
        for ps in r["playerStats"]:
            puuid = ps["puuid"]
            if puuid not in color_of:
                continue
            e, dm = ps["economy"], ps["damage"]
            rps.append(dict(
                match_id=mid, round_num=n, puuid=puuid, team_color=color_of[puuid],
                side="attack" if color_of[puuid] == att else "defense", score=ps["score"],
                loadout_value=e["loadoutValue"], spent=e["spent"], remaining=e["remaining"],
                weapon_id=(e["weapon"] or "").lower() or None, armor_id=(e["armor"] or "").lower() or None,
                damage_dealt=sum(x["damage"] for x in dm), headshots=sum(x["headshots"] for x in dm),
                bodyshots=sum(x["bodyshots"] for x in dm), legshots=sum(x["legshots"] for x in dm),
                kills_n=len(ps["kills"]),
            ))
            for x in dm:
                damage.append(dict(match_id=mid, round_num=n, giver=puuid, receiver=x["receiver"], damage=x["damage"],
                                   headshots=x["headshots"], bodyshots=x["bodyshots"], legshots=x["legshots"]))
            for k in ps["kills"]:
                fd = k["finishingDamage"]
                item = fd["damageItem"] or None
                kills.append(dict(
                    match_id=mid, round_num=n, kill_idx=kill_idx, time_in_round_ms=k["timeSinceRoundStartMillis"],
                    time_in_game_ms=k["timeSinceGameStartMillis"], killer=k["killer"], victim=k["victim"],
                    killer_color=color_of.get(k["killer"]), victim_color=color_of.get(k["victim"]),
                    victim_x=k["victimLocation"]["x"], victim_y=k["victimLocation"]["y"],
                    damage_type=fd["damageType"], damage_item=item.lower() if item and "-" in item else item,
                    secondary_fire=fd["isSecondaryFireMode"], assistants=list(k["assistants"]),
                    player_locations=[dict(puuid=pl["puuid"], x=pl["location"]["x"], y=pl["location"]["y"],
                                           view_radians=float(pl["viewRadians"])) for pl in k["playerLocations"]],
                ))
                kill_idx += 1
    return dict(match=match, match_players=mps, rounds=rounds, round_player_stats=rps, kills=kills, damage=damage)


def _resolve_teams(parsed: list[dict]) -> tuple[dict[str, tuple[str, str]], list[dict]]:
    """match_id -> (red_team, blue_team). Score match first, then roster votes. Returns (mapping, skipped)."""
    mapping: dict[str, tuple[str, str]] = {}
    votes: dict[str, Counter] = defaultdict(Counter)  # puuid -> Counter(team name)
    pending = []
    for p in parsed:
        m = p["match"]
        if m["_color_a"] is None:
            pending.append(p)
            continue
        red, blue = (m["team_a"], m["team_b"]) if m["_color_a"] == "Red" else (m["team_b"], m["team_a"])
        mapping[m["match_id"]] = (red, blue)
        for pl in p["match_players"]:
            votes[pl["puuid"]][red if pl["team_color"] == "Red" else blue] += 1
    skipped = []
    for p in pending:
        m = p["match"]
        score = {"ab": 0, "ba": 0}  # ab: A=Red, B=Blue
        for pl in p["match_players"]:
            v = votes.get(pl["puuid"], {})
            a_is_red = pl["team_color"] == "Red"
            score["ab"] += v.get(m["team_a"] if a_is_red else m["team_b"], 0)
            score["ba"] += v.get(m["team_b"] if a_is_red else m["team_a"], 0)
        if score["ab"] == score["ba"]:
            skipped.append(dict(source_file=m["source_file"], reason="team/colour mapping unresolved"))
            log.warning("Skipping %s: could not map team names to Red/Blue", m["source_file"])
            continue
        mapping[m["match_id"]] = (m["team_a"], m["team_b"]) if score["ab"] > score["ba"] else (m["team_b"], m["team_a"])
    return mapping, skipped


def build_store(files: list[Path], data_dir: Path = DATA_DIR, workers: int | None = None) -> Store:
    """Parse `files` into a Store (no cache)."""
    args = [(str(f), str(data_dir)) for f in files]
    workers = workers if workers is not None else min(os.cpu_count() or 1, 8)
    if workers > 1 and len(args) > 4:
        with ProcessPoolExecutor(workers) as ex:
            parsed = list(ex.map(parse_match_file, args, chunksize=4))
    else:
        parsed = [parse_match_file(a) for a in args]

    mapping, skipped = _resolve_teams(parsed)
    parsed = [p for p in parsed if p["match"]["match_id"] in mapping]

    t = {name: [] for name in TABLES}
    for p in parsed:
        t["matches"].append(p["match"])
        for name in TABLES[1:]:
            t[name].extend(p[name])
    frames = {name: pd.DataFrame(rows) for name, rows in t.items()}

    m = frames["matches"]
    m["red_team"] = m.match_id.map(lambda i: mapping[i][0])
    m["blue_team"] = m.match_id.map(lambda i: mapping[i][1])
    m["winner_team"] = m.apply(lambda r: r.team_a if r.score_a > r.score_b else r.team_b, axis=1)
    m = m.drop(columns=["_color_a"]).sort_values(["game_start_ms", "match_id"]).reset_index(drop=True)
    frames["matches"] = m

    names = m.set_index("match_id")[["red_team", "blue_team"]]

    def team_name(df: pd.DataFrame, color_col: str) -> pd.Series:
        red, blue = df.match_id.map(names.red_team), df.match_id.map(names.blue_team)
        return red.where(df[color_col] == "Red", blue)

    frames["match_players"]["team_name"] = team_name(frames["match_players"], "team_color")
    r = frames["rounds"]
    r["winning_team"] = team_name(r, "winning_color")
    r["attacker_team"] = team_name(r, "attacker_color")
    r["defender_team"] = team_name(r, "defender_color")
    frames["round_player_stats"]["team_name"] = team_name(frames["round_player_stats"], "team_color")

    store = Store(**frames)
    store.skipped = skipped
    return store


def _cache_key(files: list[Path]) -> str:
    h = hashlib.sha1(f"v{LOADER_VERSION}".encode())
    for f in files:
        st = f.stat()
        h.update(f"{f.name}|{st.st_mtime_ns}|{st.st_size}".encode())
    return h.hexdigest()[:16]


def load_store(data_dir: Path = DATA_DIR, use_cache: bool = True, workers: int | None = None) -> Store:
    """Load all JSON files under `data_dir` (recursive, `.DS_Store` ignored) with a disk cache."""
    files = sorted(data_dir.rglob("*.json"))
    if not files:
        raise FileNotFoundError(f"No match files under {data_dir}")
    cache = CACHE_DIR / f"store-{_cache_key(files)}.pkl"
    if use_cache and cache.exists():
        return pickle.loads(cache.read_bytes())
    store = build_store(files, data_dir, workers)
    if use_cache:
        CACHE_DIR.mkdir(exist_ok=True)
        for old in CACHE_DIR.glob("store-*.pkl"):
            old.unlink()
        cache.write_bytes(pickle.dumps(store, protocol=pickle.HIGHEST_PROTOCOL))
    return store
