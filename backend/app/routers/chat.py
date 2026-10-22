"""POST /api/chat (Stream G). Triggers the existing engines and presents their output; never computes new metrics."""
from fastapi import APIRouter

from ..chat.compose import dispatch
from ..chat.understand import understand_rules
from ..schemas.chat import ChatContext, ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    ctx = req.context or ChatContext()
    u = understand_rules(req.message, ctx)
    out = dispatch(u, ctx)
    out.source = u.source  # type: ignore[assignment]
    return out
