"""Parse match filenames: team names, final scores, date, tournament and map live ONLY in the filename.

`<TOURNAMENT>[_<PHASE>]_<no>[a-z]_<dd-mm-yy>_<team A>_<score A>_x_<score B>_<team B>_<map>.json`
e.g. `RUSH2_002_20-06-26_fatec_pg_10_x_13_panterao_gaming_ascent.json`, `UNIVAVA_G_012c_19-09-26_...`.
Owner: Stream A.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FILE_RE = re.compile(
    r"^(?P<prefix>[A-Z0-9]+(?:_[A-Z0-9]+)*)_(?P<no>\d+)(?P<sub>[a-z])?_"
    r"(?P<d>\d{2})-(?P<m>\d{2})-(?P<y>\d{2})_"
    r"(?P<a>.+)_(?P<sa>\d+)_x_(?P<sb>\d+)_(?P<b>.+)_(?P<map>[a-z]+)\.json$"
)

PHASE_RE = re.compile(r"^(C\d|G)$")  # Classificatória 1-4, Fase de Grupos

# Short tokens that are acronyms (kept upper-case in display names); anything <= 3 chars is upper-cased too.
ACRONYMS = {"caap", "ufmt", "ufmg", "ufpr", "ufpb", "uscs", "pucc", "pucgo", "ceub"}


@dataclass(frozen=True)
class FileMeta:
    tournament_code: str  # e.g. "UNIVAVA", "RUSH2"
    phase_code: str | None  # e.g. "G" (Fase de Grupos)
    match_no: str  # e.g. "012c"
    series_no: int  # 12 (several maps of one series share it)
    date: str  # ISO
    slug_a: str
    slug_b: str
    team_a: str  # display names
    team_b: str
    score_a: int
    score_b: int
    map_name: str  # public map name as written in the filename, capitalized ("Lotus")


def display_name(slug: str) -> str:
    """`fatec_pg` -> `Fatec PG`. The slug is the identity; this is cosmetic only."""
    return " ".join(t.upper() if len(t) <= 3 or t in ACRONYMS else t.capitalize() for t in slug.split("_"))


def parse_filename(name: str) -> FileMeta:
    m = FILE_RE.match(Path(name).name)
    if not m:
        raise ValueError(f"Unrecognized match filename: {name}")
    code, phase = m["prefix"], None
    head, _, tail = code.rpartition("_")
    if head and PHASE_RE.match(tail):  # UNIVAVA_C1 -> (UNIVAVA, C1); RUSH_INCLUSIVO stays whole
        code, phase = head, tail
    return FileMeta(
        tournament_code=code,
        phase_code=phase,
        match_no=m["no"] + (m["sub"] or ""),
        series_no=int(m["no"]),
        date=f"20{m['y']}-{m['m']}-{m['d']}",
        slug_a=m["a"],
        slug_b=m["b"],
        team_a=display_name(m["a"]),
        team_b=display_name(m["b"]),
        score_a=int(m["sa"]),
        score_b=int(m["sb"]),
        map_name=m["map"].capitalize(),
    )


def tournament_and_phase(path: Path, data_dir: Path) -> tuple[str, str | None]:
    """Folder names under `data/`: tournament folder, optional phase folder (e.g. `Classificatória 1`)."""
    parts = path.relative_to(data_dir).parts
    return parts[0], parts[1] if len(parts) > 2 else None
