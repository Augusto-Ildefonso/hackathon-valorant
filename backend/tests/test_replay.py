import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.analytics.replay import match_kills
from app.main import app
from app.schemas import KillsResponse

client = TestClient(app)


@pytest.fixture(scope="module")
def mids(full_store):
    m = full_store.matches
    return list(m[m.map_name.isin(["Ascent", "Lotus", "Haven"])].match_id.iloc[::40][:6])


def test_every_kill_of_the_match_is_returned(full_store, mids):
    for mid in mids:
        r = match_kills(full_store, mid)
        assert len(r.kills) == (full_store.kills.match_id == mid).sum()
        assert r.has_minimap and set(r.teams) == {"a", "b"}
        assert [k.time_ms for k in r.kills if k.round == 1] == sorted(k.time_ms for k in r.kills if k.round == 1)
        assert len({k.id for k in r.kills}) == len(r.kills)


def test_positions_are_normalized_and_others_exclude_the_pair(full_store, mids):
    for mid in mids[:3]:
        for k in match_kills(full_store, mid).kills[:60]:
            pts = [k.killer.pos, k.victim.pos] + [o.pos for o in k.others_alive]
            assert all(p is None or (0 <= p.x <= 1 and 0 <= p.y <= 1) for p in pts)
            ids = {o.puuid for o in k.others_alive}
            assert k.killer.puuid not in ids and k.victim.puuid not in ids and len(ids) <= 8
            assert k.headshot is None


def test_killer_looks_at_the_victim(full_store, mids):
    """The payload's view angles must be usable to draw cones: weapon kills point the killer at the victim."""
    errs = []
    for mid in mids:
        for k in match_kills(full_store, mid).kills:
            if k.damage_type == "weapon" and k.killer.pos and k.victim.pos and k.killer.view_radians is not None:
                du, dv = k.victim.pos.x - k.killer.pos.x, k.victim.pos.y - k.killer.pos.y
                t = k.killer.view_radians
                diff = abs((np.arctan2(dv, du) - np.arctan2(-np.cos(t), np.sin(t)) + np.pi) % (2 * np.pi) - np.pi)
                errs.append(np.degrees(diff))
    assert len(errs) > 100 and np.median(errs) < 10


def test_filters_and_weapons(full_store, mids):
    mid = mids[0]
    allk = match_kills(full_store, mid)
    r2 = match_kills(full_store, mid, round_number=2)
    assert r2.kills and all(k.round == 2 for k in r2.kills)
    p = allk.kills[0].killer.puuid
    assert all(p in (k.killer.puuid, k.victim.puuid) for k in match_kills(full_store, mid, player=p).kills)
    ta = match_kills(full_store, mid, team="a").kills
    assert ta and all(k.killer.team == "a" for k in ta)
    assert all((k.weapon is not None) == (k.damage_type == "weapon") for k in allk.kills)


def test_endpoint(mids):
    r = client.get(f"/api/matches/{mids[0]}/kills", params={"round": 3})
    assert r.status_code == 200
    body = KillsResponse.model_validate(r.json())
    assert body.kills and all(k.round == 3 for k in body.kills)
