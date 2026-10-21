import pytest
from fastapi.testclient import TestClient

from app.analytics.players import player_profile
from app.analytics.roles import ROLES, build_role_model
from app.analytics.teams import team_profile
from app.data.catalog import get_catalog
from app.main import app
from app.metrics import player_table
from app.schemas import PlayerProfile, TeamListResponse, TeamProfile

client = TestClient(app)
DUELISTS = {"Jett", "Raze", "Reyna", "Neon", "Phoenix", "Yoru", "Iso"}


@pytest.fixture(scope="module")
def roles(full_store):
    return build_role_model(full_store)


@pytest.fixture(scope="module")
def busy_player(full_store):
    return player_table(full_store).sort_values("rounds").index[-1]


def test_role_scores_are_bounded_and_top2_with_signals(roles, busy_player):
    assert ((roles.scores >= 0) & (roles.scores <= 1)).all().all() and list(roles.scores.columns) == list(ROLES)
    r = roles.roles_for(busy_player)
    assert len(r) == 2 and r[0].score >= r[1].score and all(0 <= x.confidence <= 1 for x in r)
    assert r[0].signals or r[0].role == "flex"
    assert not any(x.inferred or x.role == "igl" for x in r)  # IGL is not derivable from the data


def test_confidence_grows_with_sample(roles):
    sig = roles.signals
    few, many = sig[sig.rounds < 40].index, sig[sig.rounds >= 300].index
    assert roles.confidence.loc[few].max(axis=1).mean() < roles.confidence.loc[many].max(axis=1).mean()


def test_duelist_players_look_more_like_entries(roles, full_store):
    """Sanity check: players whose most played agent is a duelist should score higher on 'entry' on average."""
    cat = get_catalog()
    mp = full_store.match_players
    fav = mp.groupby("puuid").agent_id.agg(lambda s: s.value_counts().index[0])
    is_duelist = fav.map(lambda a: cat.agent_name(a) in DUELISTS)
    sig = roles.signals
    enough = sig[sig.rounds >= 100].index
    duel = roles.scores.loc[[p for p in enough if is_duelist.get(p, False)], "entry"].mean()
    other = roles.scores.loc[[p for p in enough if not is_duelist.get(p, True)], "entry"].mean()
    assert duel > other


def test_player_profile_matches_player_table(full_store, busy_player):
    p = player_profile(full_store, busy_player, full_store)
    PlayerProfile.model_validate(p.model_dump())
    row = player_table(full_store).loc[busy_player]
    assert p.stats.kills == row.kills and p.stats.rounds == row.rounds
    assert p.stats.kd.value == pytest.approx(row.kd) and p.stats.hs_pct.sample_size == row.rounds
    assert p.favorite_agent is not None and p.agents[0].agent.id == p.favorite_agent.id
    assert sum(m.kills for m in p.by_map) == row.kills
    assert p.weapons and all(w.rounds >= 5 for w in p.weapons)


def test_player_endpoint_and_filters(full_store, busy_player):
    r = client.get(f"/api/players/{busy_player}")
    assert r.status_code == 200
    PlayerProfile.model_validate(r.json())
    code = full_store.matches.tournament_code.iloc[0]
    sub = client.get(f"/api/players/{busy_player}", params={"tournament": code})
    assert sub.status_code in (200, 404)
    assert client.get("/api/players/nobody").status_code == 404


def test_team_profile_and_endpoints(full_store):
    name = full_store.matches.team_a.value_counts().index[0]
    p = team_profile(full_store, name, full_store)
    TeamProfile.model_validate(p.model_dump())
    assert p.record.matches == len(p.matches) == p.record.wins + p.record.losses
    assert len(p.trend) == p.record.matches and p.trend == sorted(p.trend, key=lambda t: t.date)
    assert sum(m.matches for m in p.by_map) == p.record.matches
    assert set(p.economy.win_rate_by_round_type) == {"pistol", "eco", "semi_eco", "force", "full_buy"}
    assert p.roster and len(p.role_composition) >= 1 and sum(r.count for r in p.role_composition) == 5
    r = client.get(f"/api/teams/{name}")
    assert r.status_code == 200 and r.json()["team"]["name"] == name
    assert client.get("/api/teams/No%20Such%20Team").status_code == 404
    lst = TeamListResponse.model_validate(client.get("/api/teams").json())
    assert len(lst.items) == len(set(full_store.matches.team_a) | set(full_store.matches.team_b))


def test_team_profile_map_filter(full_store):
    name = full_store.matches.team_a.value_counts().index[0]
    r = client.get(f"/api/teams/{name}", params={"map": "Ascent"})
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert {m["map"]["name"] for m in r.json()["by_map"]} == {"Ascent"}
