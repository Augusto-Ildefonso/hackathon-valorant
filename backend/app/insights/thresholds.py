"""Single place for every cutoff the insight rules use. Owner: Stream D.

A fact is "notable" when it sits in the top or bottom tail of the qualified population (see `baselines.py`), not at a
hand-picked absolute value: `STRONG_PCT` / `WEAK_PCT` are percentiles. The calibration output (how many players and
teams end up flagged) is recorded in `.claude/plans/mvp-plan.md` and checked by `tests/test_insight_rules.py`.
"""
from __future__ import annotations

# Percentile cuts of the qualified population: >= STRONG_PCT is a strength, <= WEAK_PCT is a weakness.
STRONG_PCT = 0.80
WEAK_PCT = 0.20

# Who is part of the baseline population
QUALIFY_PLAYER_ROUNDS = 100
QUALIFY_TEAM_MATCHES = 3
QUALIFY_TEAM_ROUNDS = 15  # rounds of one type / side needed for a team to enter that distribution
QUALIFY_TEAM_EVENTS = 10  # plants / retakes

# Hard minimums: below these a rule stays silent. Between the minimum and `metrics.config.LOW_SAMPLE` the insight is
# emitted with `low_sample=True` (the UI shows the amber badge).
MIN_PLAYER_ROUNDS = 40
MIN_OPENING_DUELS = 6
MIN_SHOTS = 60
MIN_TEAM_ROUNDS = 12
MIN_TEAM_EVENTS = 6
MIN_MATCHES_ON_MAP = 3  # two games are not enough to call a map "weak" and tell the team to train it
MIN_WEAPON_ROUNDS = 20

# How many insights each panel shows
MAX_STRENGTHS = 3
MAX_WEAKNESSES = 3
MAX_TIPS = 3

# Rules that compare a part with the whole (best/worst map, weapon)
MAP_GAP = 0.15  # win rate on a map differs from the overall one by at least 15 p.p.
WEAPON_GAP = 0.10  # round win rate with a weapon differs by at least 10 p.p. from the player's overall one

# Plant-site predictability: the preferred site takes at least this share of the plants
SITE_PREDICTABLE_SHARE = 0.65
SITE_CONCEDED_MIN_PLANTS = 8

# Map-level
MAP_SIDE_GAP = 0.03  # same as Stream C's "balanced" classification
ZONE_THRESHOLD = 0.3
ZONE_MIN_CELLS = 5
ZONE_DEATH_RATIO = 1.2  # a "dangerous" zone needs at least 20% more deaths than kills inside its box
ZONE_NEAR_SITE = 0.2  # minimap units: a blind-spot blob closer than this to a plant point is "near the site"

# Match-level (one map only: small samples, so rules need a clear signal)
MATCH_PISTOL_ROUNDS = (0, 12)
MATCH_LOSING_STREAK = 4
MATCH_OPENING_SHARE_GAP = 0.15  # share of first kills differs by 15 p.p. from an even split
