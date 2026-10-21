"""Insight rules (Stream D): fire on constructed stats, stay silent otherwise, keep evidence honest, flag small samples."""
import re

import pytest

from app.analytics.maps import map_profile
from app.analytics.players import player_profile
from app.analytics.teams import team_profile
from app.insights import engine
from app.insights.baselines import get_baselines
from app.insights.zones import find_zones
from app.metrics import make_stat, player_table, team_table
from app.schemas.map import HeatLayer

NUM = re.compile(r"\d+(?:,\d+)?")


@pytest.fixture(scope="module")
def base(full_store):
    return get_baselines(full_store)


@pytest.fixture(scope="module")
def veteran(full_store):
    pt = player_table(full_store)
    return pt[pt.rounds >= 300].index[0]


def _profile(full_store, puuid, **stats):
    p = player_profile(full_store, puuid, full_store)
    return p.model_copy(update={"stats": p.stats.model_copy(update=stats)})


def _ids(insights):
    return [i.id for i in insights]


def test_player_strong_and_weak_kd_fire(full_store, base, veteran):
    hi = engine.for_player(_profile(full_store, veteran, rounds=400, kd=make_stat(2.5, 400)), base)
    lo = engine.for_player(_profile(full_store, veteran, rounds=400, kd=make_stat(0.4, 400)), base)
    assert "player-kd-strong" in _ids(hi) and "player-kd-weak" not in _ids(hi)
    assert "player-kd-weak" in _ids(lo)
    ev = next(i for i in hi if i.id == "player-kd-strong").evidence
    assert ev.value == 2.5 and ev.sample_size == 400 and ev.baseline == round(base.players["kd"].median, 2)


def test_player_median_kd_is_silent(full_store, base, veteran):
    mid = engine.for_player(_profile(full_store, veteran, rounds=400, kd=make_stat(base.players["kd"].median, 400)), base)
    assert "player-kd-strong" not in _ids(mid) and "player-kd-weak" not in _ids(mid)


def test_player_with_few_rounds_gets_no_rate_insight(full_store, base, veteran):
    few = _profile(full_store, veteran, rounds=10, kd=make_stat(3.0, 10), adr=make_stat(250, 10))
    ids = _ids(engine.for_player(few, base))
    assert not any(i in ids for i in ("player-kd-strong", "player-adr-strong", "player-first-death-weak"))


def test_opening_duels_low_sample_flag(full_store, base, veteran):
    p = _profile(full_store, veteran, first_kills=7, first_deaths=0, opening_duel_win_pct=make_stat(1.0, 7, "events"))
    ins = next(i for i in engine.for_player(p, base) if i.id == "player-opening-strong")
    assert ins.low_sample and ins.evidence.sample_size == 7  # below LOW_SAMPLE["events"] = 10
    p = _profile(full_store, veteran, first_kills=30, first_deaths=3, opening_duel_win_pct=make_stat(30 / 33, 33, "events"))
    assert not next(i for i in engine.for_player(p, base) if i.id == "player-opening-strong").low_sample


def test_every_text_number_is_backed_by_evidence(full_store, base):
    """Each figure in a player/team insight text is the evidence value, its baseline, its sample size or a count of it."""
    pt = player_table(full_store)
    checked = 0
    for puuid in pt[pt.rounds >= 100].index[:25]:
        for i in engine.for_player(player_profile(full_store, puuid, full_store), base):
            allowed = {i.evidence.value, i.evidence.baseline, i.evidence.sample_size}
            for n in NUM.findall(i.text_pt):
                x = float(n.replace(",", "."))
                nums = [a for a in allowed if a is not None]
                # also the player's overall figure quoted next to a per-weapon/per-map value
                assert any(abs(x - a) <= 0.51 or abs(x - a * 100) <= 0.51 for a in nums) or "média do jogador" in i.text_pt or "geral" in i.text_pt, (i.id, i.text_pt)
                checked += 1
    assert checked > 20


def test_ids_unique_per_response_and_kinds_are_capped(full_store, base):
    tt = team_table(full_store).sort_values("matches", ascending=False)
    for team in tt.index[:6]:
        ins = engine.for_team(team_profile(full_store, team, full_store), base)
        assert len(set(_ids(ins))) == len(ins)
        for kind, cap in (("strength", 3), ("weakness", 3), ("tip", 3)):
            assert sum(i.kind == kind for i in ins) <= cap


def test_thresholds_flag_a_minority_of_players(full_store, base):
    pt = player_table(full_store)
    qualified = pt[pt.rounds >= 100].index[:60]
    strong = weak = 0
    for p in qualified:
        ids = _ids(engine.for_player(player_profile(full_store, p, full_store), base))
        strong += "player-kd-strong" in ids
        weak += "player-kd-weak" in ids
    n = len(qualified)
    assert 0.03 * n <= strong <= 0.4 * n and 0.03 * n <= weak <= 0.4 * n  # ~20% each by construction


def test_team_rules_use_the_team_tails(full_store, base):
    tp = team_profile(full_store, team_table(full_store).sort_values("matches").index[-1], full_store)
    boosted = tp.model_copy(update={"record": tp.record.model_copy(update={"attack_win_rate": make_stat(0.9, 120)})})
    assert "team-attack-strong" in _ids(engine.for_team(boosted, base))
    flat = tp.model_copy(update={"record": tp.record.model_copy(update={"attack_win_rate": make_stat(base.teams["attack_win_rate"].median / 100, 120)})})
    assert "team-attack-strong" not in _ids(engine.for_team(flat, base))


def test_map_insights_have_side_bias_and_sites(full_store):
    s = full_store.where(map_name="Ascent")
    prof = map_profile(s, "Ascent")
    ins = engine.for_map(prof, s)
    assert any(i.id == "map-site-popular" for i in ins)
    assert len({i.id for i in ins}) == len(ins)
    assert all(i.evidence.sample_size > 0 for i in ins)


def test_find_zones_returns_strongest_blob_first():
    n = 16
    g = [[0.0] * n for _ in range(n)]
    for r in range(2, 5):
        for c in range(2, 5):
            g[r][c] = 0.9
    for r in range(10, 13):
        for c in range(10, 13):
            g[r][c] = 0.5
    zones = find_zones(HeatLayer(grid=g, max_count=1))
    assert len(zones) == 2 and zones[0].weight > zones[1].weight
    assert (zones[0].x0, zones[0].y0) == (2 / n, 2 / n)
