"""Building blocks shared by the rule modules. Owner: Stream D."""
from __future__ import annotations

from dataclasses import dataclass

from ..metrics.config import LOW_SAMPLE
from ..schemas.common import Evidence, Insight, InsightKind
from . import thresholds as T
from .baselines import Dist


def f_num(v: float, digits: int = 2) -> str:
    """pt-BR number: 1,23"""
    return f"{v:.{digits}f}".replace(".", ",")


def f_pct(v: float, digits: int = 0) -> str:
    """Percentage given in 0..100: '58%'"""
    return f"{v:.{digits}f}".replace(".", ",") + "%"


def make_insight(id: str, kind: InsightKind, text: str, metric: str, value: float, n: int, baseline: float | None = None,
                 unit: str | None = None, sample: str = "rounds") -> Insight:
    return Insight(id=id, kind=kind, text_pt=text,
                   evidence=Evidence(metric=metric, value=round(float(value), 2),
                                     baseline=None if baseline is None else round(float(baseline), 2),
                                     sample_size=int(n), unit=unit),
                   low_sample=int(n) < LOW_SAMPLE[sample])


def judge(value: float | None, dist: Dist | None, higher_is_better: bool = True) -> str | None:
    """'strong' / 'weak' when `value` is in the tail of the qualified population, else None."""
    if value is None or dist is None:
        return None
    hi, lo = value >= dist.p_strong, value <= dist.p_weak
    if higher_is_better:
        return "strong" if hi else "weak" if lo else None
    return "strong" if lo else "weak" if hi else None


def intensity(value: float, dist: Dist) -> float:
    """How far into the tail the value is (1.0 = right at the cut), used to rank insights."""
    span = abs(dist.p_strong - dist.median) or 1.0
    return abs(value - dist.median) / span


@dataclass
class Scored:
    insight: Insight
    score: float


def select(items: list[Scored]) -> list[Insight]:
    """Strongest first inside each kind, capped per kind; order: strengths, weaknesses, tips, strategies."""
    caps = {"strength": T.MAX_STRENGTHS, "weakness": T.MAX_WEAKNESSES, "tip": T.MAX_TIPS, "strategy": T.MAX_TIPS}
    out: list[Insight] = []
    for kind in ("strength", "weakness", "tip", "strategy"):
        pool = sorted((s for s in items if s.insight.kind == kind), key=lambda s: -s.score)
        out.extend(s.insight for s in pool[:caps[kind]])
    return out
