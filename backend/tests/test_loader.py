"""Loader invariants on the whole dataset, plus the cross-check against data-report.md."""
from app.deps import DATA_DIR


def test_matches_the_data_report_when_full_dataset_is_present(full_store):
    files = list(DATA_DIR.rglob("*.json"))
    if len(files) != 336:
        return  # folder grew or shrank: only the generic invariants below apply
    s = full_store
    assert (len(s.matches), len(s.rounds), len(s.kills), len(s.damage)) == (336, 6618, 46753, 80071)
    # data-report says 413 distinct puuids; 5 of those only ever appear as observers
    assert s.match_players.puuid.nunique() == 411


def test_no_file_skipped_and_every_file_loaded(full_store):
    assert full_store.skipped == []
    assert len(full_store.matches) == len(list(DATA_DIR.rglob("*.json")))


def test_ten_players_five_per_team(full_store):
    per_team = full_store.match_players.groupby(["match_id", "team_name"]).size()
    assert (per_team == 5).all()
    assert full_store.match_players.team_name.notna().all()


def test_filename_score_equals_rounds_won(full_store):
    s = full_store
    won = s.rounds.groupby(["match_id", "winning_team"]).size()
    for m in s.matches.itertuples():
        assert won.get((m.match_id, m.team_a), 0) == m.score_a, m.source_file
        assert won.get((m.match_id, m.team_b), 0) == m.score_b, m.source_file


def test_attacker_and_defender_differ_and_swap_at_halftime(full_store):
    r = full_store.rounds
    assert (r.attacker_team != r.defender_team).all()
    first = r[r.round_num == 0].set_index("match_id").attacker_team
    second = r[r.round_num == 12].set_index("match_id").attacker_team
    common = first.index.intersection(second.index)
    assert (first[common] != second[common]).all()


def test_no_empty_encodings_left(full_store):
    s = full_store
    assert not (s.rounds.plant_site == "").any()
    assert s.rounds[s.rounds.planter.isna()].plant_x.isna().all()
    assert not (s.round_player_stats.armor_id == "").any()
    assert s.kills.player_locations.map(lambda x: all(isinstance(p["view_radians"], float) for p in x)).all()


def test_observers_excluded(full_store):
    s = full_store
    assert (s.match_players.groupby("match_id").size() == 10).all()
    assert s.round_player_stats.groupby(["match_id", "round_num"]).size().max() == 10


def test_helper_lookups(full_store):
    s = full_store
    m = s.matches.iloc[0]
    assert s.side(m.match_id, 0, m.team_a) != s.side(m.match_id, 0, m.team_b)
    assert s.color_of(m.match_id, m.team_a) in ("Red", "Blue")
