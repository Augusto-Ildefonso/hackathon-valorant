"""Contract tests: fixtures validate against the models, and every route answers with a valid body."""
import json

import pytest
from fastapi.testclient import TestClient

from app.deps import FIXTURES, get_store
from app.main import app
from app.schemas import ENDPOINTS

client = TestClient(app)
_STORE = get_store()  # routes backed by real data need real ids

ROUTES = {
    "meta": ("get", "/api/meta"),
    "search": ("get", "/api/search?q=fa"),
    "leaderboards": ("get", "/api/leaderboards"),
    "matches": ("get", "/api/matches"),
    "player": ("get", f"/api/players/{_STORE.match_players.puuid.iloc[0]}"),
    "teams": ("get", "/api/teams"),
    "team": ("get", f"/api/teams/{_STORE.matches.team_a.iloc[0]}"),
    "maps": ("get", "/api/maps"),
    "map": ("get", "/api/maps/Ascent"),
    "map_heatmap": ("get", "/api/maps/Ascent/heatmap?side=both"),
    "match": ("get", "/api/matches/aaac8e08-a406-498d-bd39-342a6a2f9aeb"),
    "match_kills": ("get", "/api/matches/aaac8e08-a406-498d-bd39-342a6a2f9aeb/kills"),
}


@pytest.mark.parametrize("name", sorted(ENDPOINTS))
def test_fixture_matches_model(name):
    ENDPOINTS[name].model_validate(json.loads((FIXTURES / f"{name}.json").read_text()))


@pytest.mark.parametrize("name", sorted(ROUTES))
def test_route_returns_valid_body(name):
    method, url = ROUTES[name]
    res = getattr(client, method)(url)
    assert res.status_code == 200, res.text
    ENDPOINTS[name].model_validate(res.json())


def test_plan_route():
    body = {"team_a": "Fatec PG", "team_b": "Panterão Gaming", "map": "Ascent", "perspective": "a",
            "rounds_per_half": 12, "starting_side": "attack"}
    res = client.post("/api/plan", json=body)
    assert res.status_code == 200, res.text
    ENDPOINTS["plan"].model_validate(res.json())


def test_every_endpoint_has_a_route_test():
    assert set(ROUTES) | {"plan"} == set(ENDPOINTS)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}
