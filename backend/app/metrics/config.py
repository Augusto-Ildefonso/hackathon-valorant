"""Single place for metric thresholds (documented in SPEC.md; change both together). Owner: Stream A."""
from __future__ import annotations

from ..schemas.common import RoundType, Stat

# Low-sample thresholds: maps/matches, rounds, discrete events (plants, pistols, clutches...)
LOW_SAMPLE = {"matches": 3, "rounds": 30, "events": 10}

TRADE_WINDOW_MS = 5000
PISTOL_ROUNDS = (0, 12)

# Team mean loadout value per player (calibrated on the full dataset: natural breaks near 1.6k / 2.9k / 3.9k)
ECO_MAX, SEMI_ECO_MAX, FORCE_MAX = 1600, 2900, 3900

# Valorant economy (per player). Source: game rules; sanity-checked against the data in tests/test_metrics_economy.py
ECONOMY = {"start": 800, "win": 3000, "loss": (1900, 2400, 2900, 3400), "plant_bonus": 300, "kill": 200, "cap": 9000}

# Shrinkage strength for round win probability: (wins + K * p_global) / (n + K)
WIN_PROB_K = 10
# Minimum transitions for a team-specific round-type distribution before falling back to the global one
MIN_TRANSITIONS = 30
MIN_CELL_EVENTS = 5


def make_stat(value: float | None, n: int, kind: str = "rounds") -> Stat:
    """Stat with the low-sample flag derived from `LOW_SAMPLE[kind]`."""
    v = None if value is None or value != value else float(value)
    return Stat(value=v, sample_size=int(n), low_sample=int(n) < LOW_SAMPLE[kind])


def classify_round(round_num: int, loadout_mean: float) -> RoundType:
    if round_num in PISTOL_ROUNDS:
        return "pistol"
    if loadout_mean < ECO_MAX:
        return "eco"
    if loadout_mean < SEMI_ECO_MAX:
        return "semi_eco"
    if loadout_mean < FORCE_MAX:
        return "force"
    return "full_buy"
