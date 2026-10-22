"""Action Plan endpoint. Owner: Stream D."""
from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from ..analytics.maps import canonical_map_name, map_exists
from ..analytics.teams import team_exists
from ..deps import get_store
from ..insights import llm
from ..insights.action_plan import build_plan
from ..insights.report import build_document
from ..insights.report_pdf import render_pdf
from ..schemas import PlanRequest, PlanResponse
from ..schemas.plan import PlanCapabilities

router = APIRouter(prefix="/api", tags=["plan"])
_CACHE: dict[tuple, PlanResponse] = {}  # the data is static in-process; keyed by every input that changes the result


@router.get("/plan/capabilities", response_model=PlanCapabilities)
def capabilities():
    return PlanCapabilities(llm=llm.enabled(), model=llm.model_name() if llm.enabled() else None)


def _validated(req: PlanRequest) -> str:
    """Raise 404/422 for a bad request; returns the canonical map name."""
    full = get_store()
    if req.team_a == req.team_b:
        raise HTTPException(422, "Choose two different teams")
    for t in (req.team_a, req.team_b):
        if not team_exists(full, t):
            raise HTTPException(404, f"Unknown team {t}")
    canon = canonical_map_name(req.map)
    if canon is None or not map_exists(full, canon):
        raise HTTPException(404, f"Unknown map {req.map}")
    if not 1 <= req.rounds_per_half <= 15:
        raise HTTPException(422, "rounds_per_half must be between 1 and 15")
    return canon


@router.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    full = get_store()
    canon = _validated(req)
    use_llm = req.use_llm and llm.enabled()
    key = (req.team_a, req.team_b, canon, req.perspective, req.rounds_per_half, req.starting_side, use_llm)
    if key in _CACHE:
        return _CACHE[key]
    built = build_plan(full, req.model_copy(update={"map": canon}))
    if not use_llm:
        _CACHE[key] = built
        return built
    out = llm.narrate(built)
    if out.text_source == "llm":  # a failed attempt must not be cached: the next click should try again
        _CACHE[key] = out
    return out


@router.post("/plan/report")
def report(req: PlanRequest):
    """The plan as a text-first PDF dossier (written by the LLM when `use_llm` and a key exist, deterministic otherwise)."""
    full = get_store()
    canon = _validated(req)
    key = (req.team_a, req.team_b, canon, req.perspective, req.rounds_per_half, req.starting_side, False)
    if key not in _CACHE:
        _CACHE[key] = build_plan(full, req.model_copy(update={"map": canon, "use_llm": False}))
    doc, bank = build_document(_CACHE[key], full, use_llm=req.use_llm and llm.enabled())
    mine = req.team_a if req.perspective == "a" else req.team_b
    name = re.sub(r"[^A-Za-z0-9]+", "-", f"plano-{mine}-{canon}").strip("-").lower() + ".pdf"
    return Response(render_pdf(doc, bank), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{name}"', "X-Report-Source": doc.source, "X-Report-Note": quote(doc.note or ""),
        "Access-Control-Expose-Headers": "X-Report-Source, X-Report-Note, Content-Disposition"})
