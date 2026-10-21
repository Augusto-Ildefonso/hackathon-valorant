import pytest
from fastapi.testclient import TestClient

from app.analytics.maps import map_list, map_profile
from app.main import app
from app.metrics import site_summary
from app.schemas import MapListResponse, MapProfile

client = TestClient(app)


def test_map_list_matches_the_raw_counts(full_store):
    items = {i.map.name: i for i in map_list(full_store)}
    assert set(items) == set(full_store.matches.map_name)
    for name, it in items.items():
        assert it.matches == (full_store.matches.map_name == name).sum()
        raw = full_store.rounds.merge(full_store.matches[["match_id", "map_name"]], on="match_id")
        assert it.rounds == (raw.map_name == name).sum()
        assert 0 < it.attack_win_rate.value < 1 and it.attack_win_rate.sample_size == it.rounds


def test_profile_win_rates_classification_and_usage(full_store):
    p = map_profile(full_store, "Ascent")
    MapProfile.model_validate(p.model_dump())
    assert p.attack_win_rate.value + p.defense_win_rate.value == pytest.approx(1)
    gap = p.defense_win_rate.value - p.attack_win_rate.value
    assert p.classification == ("defense" if gap >= 0.03 else "attack" if gap <= -0.03 else "balanced")
    for rows in (p.top_agents, p.top_weapons):
        assert rows and sum(r.share for r in rows) <= 1.0001 and [r.share for r in rows] == sorted((r.share for r in rows), reverse=True)
    assert p.top_agents[0].icon_url is None or p.top_agents[0].icon_url.startswith("/api/thumb/")
    assert [s.site for s in p.sites] == [x["site"] for x in site_summary(full_store.where(map_name="Ascent"), "Ascent")]
    assert {x.site for x in p.plants} == {"A", "B"}  # Ascent has two sites
    assert all(0 <= x.point.x <= 1 and 0 <= x.point.y <= 1 for x in p.plants)


def test_three_site_maps_and_maps_without_minimap(full_store):
    assert {x.site for x in map_profile(full_store, "Lotus").plants} == {"A", "B", "C"}
    abyss = map_profile(full_store, "Abyss")
    assert abyss.plants == [] and not abyss.map.has_minimap  # no transform => no points, non-spatial stats still there
    assert abyss.rounds > 0 and abyss.sites


def test_endpoints(full_store):
    r = client.get("/api/maps")
    assert r.status_code == 200
    assert len(MapListResponse.model_validate(r.json()).items) == full_store.matches.map_name.nunique()
    assert client.get("/api/maps/lotus").json()["map"]["name"] == "Lotus"  # case-insensitive
    assert client.get("/api/maps/Nowhere").status_code == 404
    sub = client.get("/api/maps/Ascent", params={"tournament": "RUSH2"}).json()
    assert 0 < sub["matches"] < client.get("/api/maps/Ascent").json()["matches"]
