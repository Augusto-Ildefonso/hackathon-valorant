import pytest
from fastapi.testclient import TestClient

from app.analytics.matches import match_report
from app.main import app
from app.schemas import MatchReport

client = TestClient(app)


@pytest.fixture(scope="module")
def sample(full_store):
    m = full_store.matches
    # a spread of matches: shortest, longest (overtime) and a few others
    ids = list(m.sort_values("score_a").match_id.iloc[[0, 40, 120, 200]]) + [m.assign(t=m.score_a + m.score_b).sort_values("t").match_id.iloc[-1]]
    return [(i, match_report(full_store, i)) for i in ids]


def test_rounds_match_the_final_score(sample, full_store):
    for mid, r in sample:
        m = full_store.matches[full_store.matches.match_id == mid].iloc[0]
        assert [x.number for x in r.rounds] == list(range(1, m.score_a + m.score_b + 1))
        assert sum(x.winner == "a" for x in r.rounds) == m.score_a == r.team_a.score
        assert sum(x.winner == "b" for x in r.rounds) == m.score_b == r.team_b.score
        assert r.winner == ("a" if m.score_a > m.score_b else "b")


def test_halves_sides_and_pistols(sample):
    for _, r in sample:
        halves = [x.half for x in r.rounds]
        assert halves[:12] == [1] * 12 and set(halves[12:24]) <= {2} and set(halves[24:]) <= {"ot"}
        assert r.rounds[0].team_a_side != r.rounds[12].team_a_side  # sides swap at halftime
        assert r.rounds[0].economy.team_a_type == r.rounds[0].economy.team_b_type == "pistol"
        assert r.rounds[12].economy.team_a_type == "pistol"
        assert all(x.result in ("eliminated", "defused", "detonated", "timer") for x in r.rounds)
        assert all((x.plant_site is not None) == x.planted for x in r.rounds)
        assert all(not x.defused or x.planted for x in r.rounds)


def test_scoreboard_matches_player_totals(sample, full_store):
    for mid, r in sample:
        mp = full_store.match_players[full_store.match_players.match_id == mid].set_index("puuid")
        assert len(r.scoreboard) == 10 and sum(1 for p in r.scoreboard if p.team == "a") == 5
        for p in r.scoreboard:
            row = mp.loc[p.player.puuid]
            assert (p.kills, p.deaths, p.assists, p.score) == (row.kills, row.deaths, row.assists, row.score)
            assert p.adr.value >= 0 and (p.hs_pct.value is None or 0 <= p.hs_pct.value <= 1)
        assert sum(p.first_kills for p in r.scoreboard) <= len(r.rounds)
        winners = [p for p in r.scoreboard if p.team == r.winner]
        assert r.mvp.puuid == max(winners, key=lambda p: p.score).player.puuid


def test_endpoint(sample):
    mid = sample[0][0]
    body = client.get(f"/api/matches/{mid}").json()
    MatchReport.model_validate(body)
    assert body["match_id"] == mid and body["map"]["name"]
    assert client.get("/api/matches/does-not-exist").status_code == 404
    assert client.get("/api/matches/does-not-exist/kills").status_code == 404
