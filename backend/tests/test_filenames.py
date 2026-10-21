"""The filename parser must handle every file in data/ (the folder can grow, so no hardcoded counts)."""
from collections import Counter

import pytest

from app.data.filenames import display_name, parse_filename, tournament_and_phase
from app.deps import DATA_DIR

FILES = sorted(DATA_DIR.rglob("*.json"))


def test_example_from_docs():
    m = parse_filename("RUSH2_002_20-06-26_fatec_pg_10_x_13_panterao_gaming_ascent.json")
    assert (m.tournament_code, m.phase_code, m.match_no, m.date) == ("RUSH2", None, "002", "2026-06-20")
    assert (m.team_a, m.score_a, m.team_b, m.score_b, m.map_name) == ("Fatec PG", 10, "Panterao Gaming", 13, "Ascent")


def test_series_suffix_and_phase():
    m = parse_filename("UNIVAVA_G_012c_19-09-26_ufu_saints_8_x_13_caap_hellhounds_haven.json")
    assert (m.phase_code, m.match_no, m.series_no) == ("G", "012c", 12)
    assert m.team_a == "UFU Saints" and m.team_b == "CAAP Hellhounds"


def test_tournament_codes():
    assert parse_filename("RUSH_INCLUSIVO_002_08-08-26_inatel_gray_5_x_13_usp_stars_gc_lotus.json").tournament_code == "RUSH_INCLUSIVO"
    m = parse_filename("UNIVAVA_C1_002_27-06-26_poli_plague_10_x_13_unicamp_tritons_red_haven.json")
    assert (m.tournament_code, m.phase_code) == ("UNIVAVA", "C1")


def test_underscored_and_numeric_names():
    m = parse_filename("UNIVAVA_C1_046_27-06-26_pucc_cardinals_2_x_13_totale_umc_lotus.json")
    assert m.slug_a == "pucc_cardinals" and m.slug_b == "totale_umc" and m.map_name == "Lotus"


def test_display_name():
    assert display_name("azure_bears_golden") == "Azure Bears Golden"
    assert display_name("ufg_gc_eagles") == "UFG GC Eagles"


def test_bad_name():
    with pytest.raises(ValueError):
        parse_filename("not_a_match.json")


@pytest.mark.skipif(not FILES, reason="no data files")
def test_every_file_parses_and_scores_are_plausible():
    metas = [parse_filename(f.name) for f in FILES]
    for m in metas:
        assert m.team_a != m.team_b
        assert max(m.score_a, m.score_b) >= 13
    # tournament folder is always resolvable
    assert all(tournament_and_phase(f, DATA_DIR)[0] for f in FILES)
    # file names are unique per tournament+match number
    assert max(Counter((m.tournament_code, m.phase_code, m.match_no) for m in metas).values()) == 1
