"""Match endpoints (detail + kills). The list endpoint lives in meta.py (Stream A). Owner: Stream C."""
from typing import Literal

from fastapi import APIRouter, HTTPException

from ..analytics.matches import match_exists, match_report
from ..analytics.replay import match_kills as build_kills
from ..deps import get_store
from ..insights import engine
from ..schemas import KillsResponse, MatchReport

router = APIRouter(prefix="/api", tags=["matches"])


def _check(match_id: str):
    if not match_exists(get_store(), match_id):
        raise HTTPException(404, f"Unknown match {match_id}")


@router.get("/matches/{match_id}", response_model=MatchReport)
def match(match_id: str, insights: Literal["rules", "llm"] = "rules"):
    _check(match_id)
    report = match_report(get_store(), match_id)
    report.insights_a, report.insights_b, report.insights_source = engine.match_insights(report, insights)
    return report


@router.get("/matches/{match_id}/kills", response_model=KillsResponse)
def match_kills(match_id: str, round: int | None = None, player: str | None = None, team: str | None = None):
    _check(match_id)
    return build_kills(get_store(), match_id, round, player, team)
