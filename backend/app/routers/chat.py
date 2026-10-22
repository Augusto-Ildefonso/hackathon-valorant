"""POST /api/chat (Stream G). Triggers the existing engines and presents their output; never computes new metrics."""
from fastapi import APIRouter

from ..chat.compose import dispatch
from ..chat.llm_chat import SUMMARY_INTENTS, summarize, understand_llm
from ..chat.understand import understand_rules
from ..insights import llm
from ..schemas.chat import ChatContext, ChatRequest, ChatResponse, SummaryRequest, SummaryResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    ctx = req.context or ChatContext()
    u = understand_rules(req.message, ctx)
    if u.intent == "unknown":  # free-form sentence the offline rules could not place: ask the model, keep the rules if it fails
        guess = understand_llm(req.message, ctx)
        if guess and not (u.miss and guess.intent == "help"):  # a name the rules saw but the data lacks must still be reported
            u = guess
    out = dispatch(u, ctx)
    out.source = u.source  # type: ignore[assignment]
    out.can_summarize = llm.enabled() and out.intent in SUMMARY_INTENTS
    return out


@router.post("/chat/summary", response_model=SummaryResponse)
def chat_summary(req: SummaryRequest):
    """Optional AI paragraph for an answer already on screen (slow, so the client asks for it after showing the answer)."""
    text, note = summarize(req.intent, req.blocks)
    return SummaryResponse(text=text, note=note)
