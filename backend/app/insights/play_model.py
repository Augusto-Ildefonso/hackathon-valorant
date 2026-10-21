"""Round win-probability model for the Action Plan base scenario (layer 2). Owner: Stream D.

A ridge logistic regression (numpy, no extra dependency) predicting whether a team wins a round from: its side, both
round types, the strength gap between the teams (overall and on the round's side) and the map's side bias. Team
strengths are shrunk win rates computed from the TRAINING matches only.

Validation is by match, never by round: 70% of the matches train, 30% test (split by a stable hash of the match id), and
the model is compared with the empirical baseline the planner already uses (`round_win_probability`, i.e. shrunk rates
by team x side x round type, averaged over both teams). The model is only adopted when it beats the baseline's log-loss
on the held-out matches; the report (also served in the plan notes) says which one is in use. A coarse model with
~80k team-rounds is a ranking aid, not an oracle.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data.store import Store
from ..metrics.config import WIN_PROB_K
from ..metrics.rounds import ROUND_TYPES

K_TEAM = 20  # shrinkage of team strengths towards 50%
RIDGE = 1.0
TEST_SHARE = 0.3
MIN_GAIN = 0.0005  # log-loss improvement needed to adopt the model


def _logit(p):
    p = np.clip(p, 0.02, 0.98)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def _fit_ridge_logistic(x: np.ndarray, y: np.ndarray, ridge: float = RIDGE, iters: int = 25) -> np.ndarray:
    """Newton / IRLS for L2-regularized logistic regression; the intercept (column 0) is not penalized."""
    w = np.zeros(x.shape[1])
    pen = np.eye(x.shape[1]) * ridge
    pen[0, 0] = 0
    for _ in range(iters):
        p = _sigmoid(x @ w)
        g = x.T @ (p - y) + pen @ w
        h = (x * (p * (1 - p))[:, None]).T @ x + pen
        step = np.linalg.solve(h, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return w


@dataclass
class _Tables:
    overall: dict[str, float]
    side: dict[tuple[str, str], float]
    global_side: dict[str, float]
    map_delta: dict[str, float]


def _tables(rows: pd.DataFrame) -> _Tables:
    g_side = rows.groupby("side").won.mean().to_dict()
    o = rows.groupby("team_name").won.agg(["sum", "size"])
    overall = {t: (r["sum"] + K_TEAM * 0.5) / (r["size"] + K_TEAM) for t, r in o.iterrows()}
    s = rows.groupby(["team_name", "side"]).won.agg(["sum", "size"])
    side = {(t, sd): (r["sum"] + K_TEAM * g_side[sd]) / (r["size"] + K_TEAM) for (t, sd), r in s.iterrows()}
    att = rows[rows.side == "attack"].groupby("map_name").won.agg(["sum", "size"])
    delta = {m: (r["sum"] + 100 * g_side["attack"]) / (r["size"] + 100) - g_side["attack"] for m, r in att.iterrows()}
    return _Tables(overall, side, g_side, delta)


def _features(t: _Tables, team, enemy, side, my_type, en_type, map_name) -> np.ndarray:
    side_en = "defense" if side == "attack" else "attack"
    f = [1.0, 1.0 if side == "attack" else 0.0]
    f += [1.0 if my_type == r else 0.0 for r in ROUND_TYPES[1:]]  # pistol is the reference level
    f += [1.0 if en_type == r else 0.0 for r in ROUND_TYPES[1:]]
    f.append(float(_logit(t.overall.get(team, 0.5)) - _logit(t.overall.get(enemy, 0.5))))
    f.append(float(_logit(t.side.get((team, side), t.global_side[side])) - _logit(t.side.get((enemy, side_en), t.global_side[side_en]))))
    f.append(t.map_delta.get(map_name, 0.0) * (1 if side == "attack" else -1) * 10)
    return np.array(f)


def _matrix(t: _Tables, rows: pd.DataFrame) -> np.ndarray:
    return np.array([_features(t, a, b, s, m, e, mp) for a, b, s, m, e, mp in
                     zip(rows.team_name, rows.opp_team, rows.side, rows.round_type, rows.enemy_type, rows.map_name)])


def _baseline(rows: pd.DataFrame, train: pd.DataFrame) -> np.ndarray:
    """The planner's empirical estimate on `rows`, with rates from `train` only (shrunk, averaged over both teams)."""
    pg = train.groupby(["side", "round_type"]).won.mean()
    own = train.groupby(["team_name", "side", "round_type"]).won.agg(["sum", "size"])

    def rate(team, side, typ):
        g = pg.get((side, typ), 0.5)
        if (team, side, typ) in own.index:
            r = own.loc[(team, side, typ)]
            return (r["sum"] + WIN_PROB_K * g) / (r["size"] + WIN_PROB_K)
        return g

    side_en = {"attack": "defense", "defense": "attack"}
    p = [(rate(a, s, m) + 1 - rate(b, side_en[s], e)) / 2 for a, b, s, m, e in
         zip(rows.team_name, rows.opp_team, rows.side, rows.round_type, rows.enemy_type)]
    return np.clip(np.array(p), 0.02, 0.98)


def _logloss(y, p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


@dataclass
class WinModel:
    tables: _Tables
    weights: np.ndarray
    report: dict = field(default_factory=dict)

    @property
    def adopted(self) -> bool:
        return bool(self.report.get("adopted"))

    def predict(self, team, enemy, side, my_type, en_type, map_name) -> float | None:
        """Win probability of `team`, or None when the model did not beat the baseline on held-out matches."""
        if not self.adopted:
            return None
        x = _features(self.tables, team, enemy, side, my_type, en_type, map_name)
        return float(np.clip(_sigmoid(x @ self.weights), 0.02, 0.98))


def _is_test(match_id: str) -> bool:
    return int(hashlib.md5(match_id.encode()).hexdigest(), 16) % 100 < TEST_SHARE * 100


def fit_win_model(full: Store, tr: pd.DataFrame) -> WinModel:
    rows = tr.merge(full.matches[["match_id", "map_name"]], on="match_id")
    rows = rows.assign(won=rows.won.astype(float))
    test_mask = rows.match_id.map(_is_test)
    train, test = rows[~test_mask], rows[test_mask]
    t_train = _tables(train)
    w_val = _fit_ridge_logistic(_matrix(t_train, train), train.won.to_numpy())
    p_model = _sigmoid(_matrix(t_train, test) @ w_val)
    p_base = _baseline(test, train)
    y = test.won.to_numpy()
    ll_model, ll_base = _logloss(y, p_model), _logloss(y, p_base)
    report = {
        "train_rounds": len(train), "test_rounds": len(test), "train_matches": int(train.match_id.nunique()),
        "test_matches": int(test.match_id.nunique()), "logloss_model": round(ll_model, 4), "logloss_baseline": round(ll_base, 4),
        "brier_model": round(float(np.mean((p_model - y) ** 2)), 4), "brier_baseline": round(float(np.mean((p_base - y) ** 2)), 4),
        "accuracy_model": round(float(np.mean((p_model > 0.5) == (y > 0.5))), 4),
        "accuracy_baseline": round(float(np.mean((p_base > 0.5) == (y > 0.5))), 4),
        "adopted": bool(ll_model < ll_base - MIN_GAIN),
    }
    t_all = _tables(rows)
    w_all = _fit_ridge_logistic(_matrix(t_all, rows), rows.won.to_numpy())
    return WinModel(t_all, w_all, report)


_CACHE: dict[int, WinModel] = {}


def get_win_model(full: Store, tr: pd.DataFrame) -> WinModel:
    key = id(full)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = fit_win_model(full, tr)
    return _CACHE[key]
