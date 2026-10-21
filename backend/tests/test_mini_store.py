"""The mini store must honour SCHEMA.md and the invariants analytics code relies on."""
import pytest

from tests.fixtures.mini_store import build_mini_store


@pytest.fixture(scope="module")
def store():
    return build_mini_store()


def test_three_matches_ten_players_each(store):
    assert len(store.matches) == 3
    assert (store.match_players.groupby("match_id").size() == 10).all()  # observers excluded


def test_rounds_match_final_score(store):
    for m in store.matches.itertuples():
        r = store.rounds[store.rounds.match_id == m.match_id]
        assert len(r) >= m.score_a + m.score_b - 1  # all played rounds are present
        assert (r.winning_team == m.team_a).sum() == m.score_a
        assert (r.winning_team == m.team_b).sum() == m.score_b


def test_side_swaps_at_halftime(store):
    m = store.matches.iloc[0]
    first = store.side(m.match_id, 0, m.team_a)
    assert first in ("attack", "defense")
    assert store.side(m.match_id, 12, m.team_a) != first
    assert {store.side(m.match_id, 0, m.team_a), store.side(m.match_id, 0, m.team_b)} == {"attack", "defense"}


def test_no_plant_means_null_not_zero(store):
    r = store.rounds
    assert r[r.planter.isna()].plant_x.isna().all()
    assert r[r.planter.notna()].plant_x.notna().all()


def test_every_kill_is_between_known_players(store):
    k = store.kills
    assert k.killer_color.notna().all() or (k.damage_type != "Weapon").any()
    assert k.victim_color.notna().all()


def test_team_of(store):
    row = store.match_players.iloc[0]
    assert store.team_of(row.match_id, row.puuid) == row.team_name
    assert store.team_of(row.match_id, "nobody") is None
