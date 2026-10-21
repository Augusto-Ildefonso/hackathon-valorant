from fastapi.testclient import TestClient

from app.main import app
from app.schemas import LeaderboardsResponse, MatchListResponse, MetaResponse, SearchResponse

client = TestClient(app)


def test_meta_kpis_match_the_store(full_store):
    r = MetaResponse.model_validate(client.get("/api/meta").json())
    assert r.kpis.matches == len(full_store.matches) and r.kpis.rounds == len(full_store.rounds)
    assert r.date_from <= r.date_to and r.tournaments and {m.name for m in r.maps} >= {"Ascent", "Lotus"}
    assert sum(t.matches for t in r.tournaments) == r.kpis.matches
    abyss = [m for m in r.maps if m.name in ("Abyss", "Summit")]
    assert all(not m.has_minimap for m in abyss)


def test_search_players_teams_maps_and_accents(full_store):
    team = full_store.matches.team_a.iloc[0]
    r = SearchResponse.model_validate(client.get("/api/search", params={"q": team[:4].lower()}).json())
    assert any(t.team.name == team for t in r.teams)
    p = full_store.match_players.riot_id.iloc[0]
    r = SearchResponse.model_validate(client.get("/api/search", params={"q": p[:3]}).json())
    assert any(h.player.riot_id == p for h in r.players)
    assert [m.map.name for m in SearchResponse.model_validate(client.get("/api/search", params={"q": "lot"}).json()).maps] == ["Lotus"]
    assert client.get("/api/search", params={"q": ""}).json()["players"] == []


def test_leaderboards_sorted_and_respect_tournament(full_store):
    r = LeaderboardsResponse.model_validate(client.get("/api/leaderboards").json())
    kd = [x.value for x in r.players["kd"]]
    assert kd == sorted(kd, reverse=True) and len(kd) == 10
    code = full_store.matches.tournament_code.iloc[0]
    sub = LeaderboardsResponse.model_validate(client.get("/api/leaderboards", params={"tournament": code}).json())
    assert sub.players["adr"]


def test_matches_list_filters_and_paging(full_store):
    all_ = MatchListResponse.model_validate(client.get("/api/matches", params={"limit": 5}).json())
    assert all_.total == len(full_store.matches) and len(all_.items) == 5
    dates = [i.date for i in all_.items]
    assert dates == sorted(dates, reverse=True)
    lotus = MatchListResponse.model_validate(client.get("/api/matches", params={"map": "Lotus", "limit": 200}).json())
    assert lotus.total == (full_store.matches.map_name == "Lotus").sum() and all(i.map.name == "Lotus" for i in lotus.items)
    team = full_store.matches.team_a.iloc[0]
    t = MatchListResponse.model_validate(client.get("/api/matches", params={"team": team, "limit": 200}).json())
    assert t.total >= 1 and all(team in (i.team_a.team.name, i.team_b.team.name) for i in t.items)
    page2 = MatchListResponse.model_validate(client.get("/api/matches", params={"limit": 5, "offset": 5}).json())
    assert {i.match_id for i in page2.items}.isdisjoint({i.match_id for i in all_.items})
