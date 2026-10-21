import numpy as np
import pytest

from app.metrics.config import classify_round
from app.metrics.rounds import (ROUND_TYPES, next_type_distribution, project_next_credits, round_win_probability,
                                team_rounds)


@pytest.fixture(scope="module")
def tr(full_store):
    return team_rounds(full_store)


def test_one_row_per_team_per_round(tr, full_store):
    assert len(tr) == len(full_store.rounds) * 2
    assert tr.groupby(["match_id", "round_num"]).size().eq(2).all()
    assert tr.groupby(["match_id", "round_num"]).won.sum().eq(1).all()  # exactly one winner


def test_classify_boundaries():
    assert classify_round(0, 800) == classify_round(12, 3000) == "pistol"
    assert [classify_round(3, v) for v in (1599, 1600, 2899, 2900, 3899, 3900)] == [
        "eco", "semi_eco", "semi_eco", "force", "force", "full_buy"]


def test_pistols_are_rounds_0_and_12(tr):
    assert set(tr[tr.round_type == "pistol"].round_num) == {0, 12}
    assert tr[tr.round_num.isin([0, 12])].prev_type.isna().all()  # no carry-over across the half


def test_loss_streak_and_prev_state(tr):
    t = tr[(tr.match_id == tr.match_id.iloc[0]) & (tr.team_name == tr.team_name.iloc[0])].sort_values("round_num")
    assert t.iloc[0].loss_streak == 0
    for a, b in zip(t.itertuples(), t.iloc[1:].itertuples()):
        if b.round_num in (12,):
            continue
        assert b.prev_won == a.won
        assert b.loss_streak == (0 if a.won else a.loss_streak + 1)


def test_transition_distribution_sums_to_one_and_falls_back(tr):
    d = next_type_distribution(tr, "pistol", True, 0)  # won pistol -> usually eco-ish/force/full
    assert d["source"] == "global" and d["sample_size"] > 100
    assert sum(d["probs"].values()) == pytest.approx(1.0)
    team = tr.team_name.value_counts().index[0]
    assert next_type_distribution(tr, "full_buy", True, 0, team=team)["source"] in ("team", "global")
    rare = next_type_distribution(tr, "eco", True, 3, team="No Such Team")
    assert rare["source"] == "global"


def test_after_losing_pistol_teams_do_not_full_buy(tr):
    d = next_type_distribution(tr, "pistol", False, 1)
    assert d["probs"]["full_buy"] < 0.2 and d["probs"]["eco"] + d["probs"]["semi_eco"] > 0.5


def test_projected_economy_tracks_the_data(tr):
    """Predict next-round start credits from the previous round; the model must be close to what the data shows."""
    t = tr.sort_values(["match_id", "team_name", "round_num"])
    nxt = t.groupby(["match_id", "team_name"]).shift(-1)
    ok = nxt.round_num.notna() & ~nxt.round_num.isin([0, 12]) & (nxt.round_num == t.round_num + 1)
    pred = [project_next_credits(r.remaining_mean, r.won, r.loss_streak, r.planted and not r.won and r.side == "attack",
                                 r.kills / 5, int(n)) for r, n in zip(t[ok].itertuples(), nxt[ok].round_num)]
    err = np.abs(np.array(pred) - nxt[ok].credits_start.to_numpy())
    assert np.median(err) < 400, np.median(err)  # model is coarse (kills/plant bonus), stays within ~one weapon tier


def test_win_probability_is_shrunk_toward_global(tr):
    team = tr.team_name.value_counts().index[0]
    p = round_win_probability(tr, team, "attack", "full_buy")
    assert 0 < p["value"] < 1 and p["sample_size"] > 0
    ghost = round_win_probability(tr, "No Such Team", "attack", "full_buy")
    assert ghost["sample_size"] == 0 and ghost["value"] == pytest.approx(ghost["p_global"]) and ghost["low_sample"]
    assert set(ROUND_TYPES) == {"pistol", "eco", "semi_eco", "force", "full_buy"}
