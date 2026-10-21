"""Kill replay payload for the Match Report. Owner: Stream C.

Per kill: killer and victim with minimap positions and view angles, everyone else alive at that moment, weapon, time.
`headshot` is always None: the data only has per-target hit counts per round, so the finishing hit cannot be known.
"""
from __future__ import annotations

from ..data.catalog import get_catalog
from ..data.coords import to_minimap
from ..data.store import Store
from ..schemas.common import AgentRef, PlayerRef, Point, TeamRef
from ..schemas.match import KillEvent, KillsResponse, ReplayPlayer

DAMAGE = {"Weapon": "weapon", "Ability": "ability", "Bomb": "bomb", "Fall": "fall", "Melee": "melee", "Crush": "crush"}


def _point(map_name: str, x, y) -> Point | None:
    p = to_minimap(map_name, x, y)
    return Point(x=p[0], y=p[1]) if p else None


def match_kills(store: Store, match_id: str, round_number: int | None = None, player: str | None = None,
                team: str | None = None) -> KillsResponse:
    """Kills of one match (rounds are 1-based), optionally for a round, a player (killer or victim) or a killing team
    (`a`, `b` or the team name). Raises KeyError for an unknown id."""
    s = store.subset([match_id])
    if s.matches.empty:
        raise KeyError(match_id)
    m = s.matches.iloc[0]
    cat = get_catalog()
    ref = cat.map_ref(m.map_name)
    roster = {p.puuid: p for p in s.match_players.itertuples()}
    side_of = lambda puuid: "a" if roster[puuid].team_name == m.team_a else "b"  # noqa: E731

    def actor(puuid: str, pos: Point | None, view: float | None) -> ReplayPlayer:
        p = roster[puuid]
        return ReplayPlayer(puuid=puuid, riot_id=p.riot_id, team=side_of(puuid), agent=cat.agent(p.agent_id) or AgentRef(id="unknown"),
                            pos=pos, view_radians=view)

    k = s.kills.sort_values(["round_num", "time_in_round_ms", "kill_idx"])
    if round_number is not None:
        k = k[k.round_num == round_number - 1]
    if player:
        k = k[(k.killer == player) | (k.victim == player)]
    if team:
        want = {"a": m.team_a, "b": m.team_b}.get(team.lower(), team)
        k = k[k.killer.map(lambda x: roster[x].team_name == want)]

    out, counter = [], {}
    for r in k.itertuples():
        snap = {p["puuid"]: p for p in r.player_locations}
        ks, vs = snap.get(r.killer), snap.get(r.victim)
        idx = counter[r.round_num] = counter.get(r.round_num, -1) + 1
        item = r.damage_item if isinstance(r.damage_item, str) and "-" in r.damage_item else None
        out.append(KillEvent(
            id=f"{r.round_num + 1}-{idx}", round=int(r.round_num) + 1, time_ms=int(r.time_in_round_ms),
            killer=actor(r.killer, _point(m.map_name, ks["x"], ks["y"]) if ks else None, ks["view_radians"] if ks else None),
            victim=actor(r.victim, _point(m.map_name, r.victim_x, r.victim_y), vs["view_radians"] if vs else None),
            assistants=[PlayerRef(puuid=a, riot_id=roster[a].riot_id) for a in r.assistants if a in roster],
            weapon=cat.weapon(item) if r.damage_type == "Weapon" and item else None,
            damage_type=DAMAGE.get(r.damage_type, "unknown"), headshot=None,
            others_alive=[actor(pid, _point(m.map_name, p["x"], p["y"]), p["view_radians"])
                          for pid, p in snap.items() if pid not in (r.killer, r.victim) and pid in roster]))
    return KillsResponse(match_id=match_id, map=ref, has_minimap=ref.has_minimap, kills=out,
                         teams={"a": TeamRef(name=m.team_a), "b": TeamRef(name=m.team_b)})
