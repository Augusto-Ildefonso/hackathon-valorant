"""Win model (Stream D, layer 2): fitting, symmetry and the held-out validation gate."""
import numpy as np
import pytest

from app.insights.action_plan import cached_team_rounds
from app.insights.play_model import _fit_ridge_logistic, _is_test, _sigmoid, fit_win_model


def test_ridge_logistic_recovers_the_signal():
    rng = np.random.default_rng(1)
    x = np.column_stack([np.ones(4000), rng.normal(size=4000)])
    y = (rng.random(4000) < _sigmoid(0.3 + 1.5 * x[:, 1])).astype(float)
    w = _fit_ridge_logistic(x, y)
    assert abs(w[0] - 0.3) < 0.15 and abs(w[1] - 1.5) < 0.2


def test_split_is_by_match_and_stable():
    ids = [f"m{i}" for i in range(400)]
    share = np.mean([_is_test(i) for i in ids])
    assert 0.2 < share < 0.4 and [_is_test(i) for i in ids] == [_is_test(i) for i in ids]


@pytest.fixture(scope="module")
def model(full_store):
    return fit_win_model(full_store, cached_team_rounds(full_store))


def test_report_compares_with_the_baseline_on_unseen_matches(model):
    r = model.report
    assert r["test_matches"] > 30 and r["train_matches"] > r["test_matches"]
    assert 0.5 < r["logloss_model"] < 0.8 and 0.5 < r["logloss_baseline"] < 0.8
    assert r["adopted"] == (r["logloss_model"] < r["logloss_baseline"] - 0.0005)


def test_predictions_are_symmetric_between_the_two_teams(model, full_store):
    if not model.adopted:
        pytest.skip("model not adopted on this data")
    m = full_store.matches.iloc[0]
    a, b, mp = m.team_a, m.team_b, m.map_name
    p = model.predict(a, b, "attack", "full_buy", "full_buy", mp)
    q = model.predict(b, a, "defense", "full_buy", "full_buy", mp)
    assert abs(p + q - 1) < 0.02 and 0.02 <= p <= 0.98  # each round is in the data from both teams, so the fit is near-symmetric


def test_not_adopted_model_returns_none(model):
    model.report["adopted"] = False
    try:
        assert model.predict("a", "b", "attack", "full_buy", "full_buy", "Ascent") is None
    finally:
        model.report["adopted"] = True
