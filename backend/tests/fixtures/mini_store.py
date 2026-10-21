"""Tiny Store built from a few real files, so B/C/D can develop and test on a small, fast dataset.

It uses the real loader (`app.data.loader.build_store`), just on 3 files, so analytics code sees exactly the tables
that production uses (`app/data/SCHEMA.md`).
"""
from __future__ import annotations

from pathlib import Path

from app.data.loader import build_store
from app.data.store import Store
from app.deps import DATA_DIR


def default_files() -> list[Path]:
    """Three deterministic real files (different maps/tournaments)."""
    picks = []
    for pat in ("Rush Series Esquenta 2/RUSH2_002*", "Univav*/Classificat*ria 1/*lotus.json", "Univav*/Classificat*ria 1/*haven.json"):
        picks.append(sorted(DATA_DIR.glob(pat))[0])
    return picks


def build_mini_store(files: list[Path] | None = None) -> Store:
    return build_store(files or default_files(), DATA_DIR, workers=1)
