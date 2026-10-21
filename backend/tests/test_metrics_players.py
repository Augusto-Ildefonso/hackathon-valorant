import pandas as pd
import pytest

from app.metrics import objective_summary, player_table, site_summary, team_table
from app.metrics.events import clutch_events, kill_events


@pytest.fixture(scope="module")
def pt(full_store):
    return player_table(full_store)


def test_totals_match_the_raw_data(pt, full_store):
    assert pt.kills.sum() == full_store.match_players.kills.sum()
    assert pt.rounds.sum() == len(full_store.round_player_stats)
    assert len(pt) == full_store.match_players.puuid.nunique()


def test_hand_computed_player_from_one_match(full_store):
    """Recompute K/D, ADR and HS% for one player-match straight from the tables."""
    mp = full_store.match_players.iloc[0]
    one = full_store.subset([mp.match_id])
    row = player_table(one).loc[mp.puuid]
    rps = full_store.round_player_stats
    mine = rps[(rps.match_id == mp.match_id) & (rps.puuid == mp.puuid)]
    assert row.kd == pytest.approx(mp.kills / max(mp.deaths, 1))
    assert row.adr == pytest.approx(mine.damage_dealt.sum() / len(mine))
    shots = mine[["headshots", "bodyshots", "legshots"]].sum().sum()
    assert row.hs_pct == pytest.approx(mine.headshots.sum() / shots)
    assert row.rounds == mp.rounds_played  # roundsPlayed in stats == rows in round_player_stats


def test_every_round_has_at_most_one_first_kill(full_store):
    ke = kill_events(full_store)
    assert ke[ke.is_first].groupby(["match_id", "round_num"]).size().max() == 1


def test_trades_are_consistent(full_store):
    ke = kill_events(full_store)
    assert ke.is_trade.sum() > 0 and ke.death_traded.sum() > 0
    assert not (ke.is_trade & ke.is_first).any()  # an opening kill cannot avenge anything


def test_game_clutch_ceremonies_are_all_detected(full_store):
    """The game flags 247 'CeremonyClutch' rounds; every one must be a clutch win in our independent detection."""
    c = clutch_events(full_store)
    won = c[c.won][["match_id", "round_num"]].drop_duplicates()
    cer = full_store.rounds[full_store.rounds.ceremony == "CeremonyClutch"][["match_id", "round_num"]]
    assert len(cer.merge(won)) == len(cer)


def test_team_table(full_store):
    tt = team_table(full_store)
    assert tt.matches.sum() == 2 * len(full_store.matches)
    assert tt.wins.sum() == len(full_store.matches)
    assert tt.rounds_won.sum() == tt.rounds_lost.sum()
    assert ((tt.attack_win_rate >= 0) & (tt.attack_win_rate <= 1)).all()
    assert isinstance(tt.last_match_date.iloc[0], str)


def test_objective(full_store):
    s = objective_summary(full_store, map_name="Ascent")
    assert sum(v.value for v in s["site_preference"].values()) == pytest.approx(1.0)
    assert s["plant_rate"].sample_size > 100
    sites = site_summary(full_store, "Ascent")
    assert {x["site"] for x in sites} == {"A", "B"}  # Ascent has no C site
    assert isinstance(pd.Series([s["avg_time_to_plant_ms"].value]).iloc[0], float)
