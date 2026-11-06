"""Chat routes: single-shot JSON and SSE streaming."""

from fastapi import APIRouter, Depends, Request
from sse_starlette import JSONServerSentEvent
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_container
from app.api.routes.auth import require_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.container import AppContainer

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    container: AppContainer = Depends(get_container),
    user_id: str = Depends(require_user),
) -> ChatResponse:
    """Answer one turn and return the full JSON response."""
    payload = payload.model_copy(update={"user_id": user_id})
    return await container.chat_service.chat(payload, trace_id=request.state.trace_id)


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    container: AppContainer = Depends(get_container),
    user_id: str = Depends(require_user),
) -> EventSourceResponse:
    """Answer one turn as an SSE stream of node, token and answer events."""

    payload = payload.model_copy(update={"user_id": user_id})
    await container.chat_service.validate_session(payload)

    async def events():
        async for item in container.chat_service.stream(payload, trace_id=request.state.trace_id):
            yield JSONServerSentEvent(item)

    return EventSourceResponse(events())
