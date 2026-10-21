import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.analytics.heatmaps import heatmap, kill_events_with_positions
from app.main import app
from app.schemas import HeatmapResponse

client = TestClient(app)


@pytest.fixture(scope="module")
def ascent(full_store):
    return full_store.where(map_name="Ascent")


def test_layers_are_square_normalized_grids(full_store):
    h = heatmap(full_store, "Ascent", "both", 32)
    assert h.has_data and h.grid_size == 32
    for layer in (h.kills, h.deaths, h.danger, h.uncovered):
        g = np.array(layer.grid)
        assert g.shape == (32, 32) and g.min() >= 0 and g.max() == pytest.approx(1.0) and layer.max_count > 0
    assert {p.site for p in h.plants} == {"A", "B"} and h.agents_used and h.weapons_used


def test_every_kill_has_a_side_and_sides_partition_the_events(ascent):
    e = kill_events_with_positions(ascent, "Ascent")
    assert len(e) > 5000
    assert e.victim_side.isin(["attack", "defense"]).all() and e.killer_side.isin(["attack", "defense"]).all()
    assert (e.killer_side != e.victim_side).all()  # a kill is always attacker vs defender
    raw = ascent.kills[ascent.kills.killer_color.notna() & (ascent.kills.killer_color != ascent.kills.victim_color)]
    assert len(e) == len(raw)


def test_blind_spot_inputs_are_plausible(ascent):
    e = kill_events_with_positions(ascent, "Ascent")
    unc = (~e.covered & e.has_opp).sum() / e.has_opp.sum()
    assert 0.05 < unc < 0.6  # some, but not most, kills come from unwatched positions
    inside = e.ku.notna() & e.kv.notna()
    assert inside.mean() > 0.9  # most killer positions fall on the minimap


def test_side_filter_changes_the_layers(full_store):
    a = np.array(heatmap(full_store, "Ascent", "attack", 32).deaths.grid)
    d = np.array(heatmap(full_store, "Ascent", "defense", 32).deaths.grid)
    assert not np.allclose(a, d)


def test_maps_without_minimap_have_no_data(full_store):
    h = heatmap(full_store, "Abyss")
    assert not h.has_data and h.kills is None and h.deaths is None and h.danger is None and h.uncovered is None


def test_endpoint_validates_caches_and_filters(full_store):
    r = client.get("/api/maps/Ascent/heatmap", params={"side": "attack", "grid_size": 24})
    assert r.status_code == 200
    body = HeatmapResponse.model_validate(r.json())
    assert body.side == "attack" and len(body.kills.grid) == 24
    assert client.get("/api/maps/Ascent/heatmap", params={"side": "attack", "grid_size": 24}).json() == r.json()  # cached
    full = client.get("/api/maps/Ascent/heatmap").json()["kills"]["max_count"]
    sub = client.get("/api/maps/Ascent/heatmap", params={"tournament": "RUSH2"}).json()["kills"]["max_count"]
    assert sub < full
    assert client.get("/api/maps/Ascent/heatmap", params={"grid_size": 4}).status_code == 422
    assert client.get("/api/maps/Abyss/heatmap").json()["has_data"] is False
