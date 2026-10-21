"""Action Plan endpoint. Owner: Stream D."""
from fastapi import APIRouter

from ..deps import fixture
from ..schemas import PlanRequest, PlanResponse

router = APIRouter(prefix="/api", tags=["plan"])


@router.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    return fixture("plan")
