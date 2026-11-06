"""Answer generation and refusal nodes."""

from __future__ import annotations

import json
import time

from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.enums import RetrievalStrategy
from app.core.exceptions import LLMOutputError, LLMProviderError
from app.prompts.answer import ANSWER_SYSTEM, ANSWER_USER
from app.providers.base import LLMProvider
from app.providers.fake import OfflineLLMProvider
from app.providers.json_parser import parse_model
from app.schemas.common import LatencyBreakdown, TokenUsage
from app.schemas.retrieval import Citation


class AnswerPayload(BaseModel):
    answer: str
    citation_chunk_ids: list[str] = Field(default_factory=list)
    refused: bool = False


async def generate_node(state: AgentState, llm: LLMProvider) -> dict:
    started = time.perf_counter()
    chunks = state.get("retrieved_chunks") or []
    tools = state.get("tool_results") or []
    if tools and all(not tool.success for tool in tools):
        return {
            "final_answer": "I could not retrieve that account information. Check the order number and try again.",
            "citations": [],
        }
    pending = state.get("pending_action")
    if (state.get("extra") or {}).get("missing_order_id"):
        return {
            "final_answer": "Please provide the order number before I can continue.",
            "citations": [],
        }
    if pending:
        answer = pending.summary
        latency = state.get("latency") or LatencyBreakdown()
        latency.llm_ms = (time.perf_counter() - started) * 1000
        return {
            "final_answer": answer,
            "citations": [],
            "refused": False,
            "latency": latency,
        }
    evidence = (
        "\n\n".join(f"[{c.chunk_id}] {c.title}\n{c.content}" for c in chunks[:6])
        or "(no retrieved evidence)"
    )
    tool_text = (
        json.dumps([t.model_dump() for t in tools], ensure_ascii=False) if tools else "(none)"
    )
    intent = state.get("intent")
    strategy = state.get("strategy") or RetrievalStrategy.DIRECT
    if isinstance(llm, OfflineLLMProvider):
        answer, citation_ids = _offline_answer(state)
        citations = [
            Citation(
                document_id=chunk.document_id,
                title=chunk.title,
                chunk_id=chunk.chunk_id,
                section=chunk.section,
            )
            for chunk in chunks
            if chunk.chunk_id in citation_ids
        ]
        return {"final_answer": answer, "citations": citations, "refused": False}
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM},
        {
            "role": "user",
            "content": ANSWER_USER.format(
                query=state["user_query"],
                intent=intent.label.value if intent else "unknown",
                strategy=strategy.value,
                evidence=evidence,
                tool_results=tool_text,
            ),
        },
    ]
    try:
        response = await llm.generate(
            messages,
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        payload = parse_model(response.content, AnswerPayload)
        usage = response.usage
    except (LLMProviderError, LLMOutputError):
        payload = AnswerPayload(
            answer=_extractive_fallback(state["user_query"], evidence, tool_text),
            citation_chunk_ids=[chunks[0].chunk_id] if chunks else [],
        )
        usage = TokenUsage()
    citations = [
        Citation(
            document_id=chunk.document_id,
            title=chunk.title,
            chunk_id=chunk.chunk_id,
            section=chunk.section,
        )
        for chunk in chunks
        if chunk.chunk_id in set(payload.citation_chunk_ids)
    ]
    latency = state.get("latency") or LatencyBreakdown()
    latency.llm_ms = (time.perf_counter() - started) * 1000
    prev_usage = state.get("token_usage") or TokenUsage()
    merged = TokenUsage(
        prompt_tokens=prev_usage.prompt_tokens + usage.prompt_tokens,
        completion_tokens=prev_usage.completion_tokens + usage.completion_tokens,
        total_tokens=prev_usage.total_tokens + usage.total_tokens,
    )
    return {
        "final_answer": payload.answer,
        "citations": citations,
        "refused": payload.refused,
        "latency": latency,
        "token_usage": merged,
    }


async def refuse_node(state: AgentState) -> dict:
    return {
        "final_answer": "That request is outside store support. I can help with products, orders, shipping, and returns.",
        "refused": True,
        "citations": [],
    }


def _extractive_fallback(query: str, evidence: str, tool_text: str) -> str:
    if evidence and evidence != "(no retrieved evidence)":
        snippet = evidence.split("\n", 1)[-1][:240].strip()
        return f"I could not generate a complete answer. Relevant source excerpt:\n\n> {snippet}\n\nPlease refer to the source text."
    if tool_text and tool_text != "(none)":
        return "I retrieved the system data but could not summarize it reliably. Please try again or ask for a human agent."
    return "I cannot answer reliably from the available information. Please provide more detail or ask for a human agent."


def _offline_answer(state: AgentState) -> tuple[str, set[str]]:
    """Return only retrieved text or explicitly whitelisted demo-tool fields."""
    if state.get("strategy") == RetrievalStrategy.DIRECT:
        return "Hello! I can help with store policies, orders, shipping, and returns.", set()
    statuses = {
        "created": "awaiting payment",
        "paid": "paid",
        "shipped": "shipped",
        "delivered": "delivered",
        "cancelled": "cancelled",
        "refunding": "refund pending",
        "refunded": "refunded",
    }
    for result in reversed(state.get("tool_results") or []):
        if not result.success:
            continue
        data = result.output
        order_id = data.get("order_id", "")
        if result.name == "cancel_order":
            return f"Order {order_id} was cancelled.", set()
        if result.name == "create_refund_request":
            return (
                f"A refund request was submitted for order {order_id}. The funds have not necessarily arrived yet.",
                set(),
            )
        if result.name == "create_return_request":
            return (
                f"A return request was submitted for order {order_id}. This does not mean a refund is complete.",
                set(),
            )
        if result.name == "get_order":
            status = statuses.get(str(data.get("status")), "unknown")
            return f"Order {order_id} is currently {status}.", set()
        if result.name == "track_shipment":
            events = data.get("events") or []
            latest = events[-1] if events else None
            labels = {
                "warehouse": "being prepared",
                "in_transit": "in transit",
                "delivered": "delivered",
            }
            status = (
                labels.get(str(latest.get("status")), "unknown")
                if isinstance(latest, dict)
                else "no tracking events yet"
            )
            return f"The latest shipping status for order {order_id} is {status}.", set()
        if result.name == "get_refund_status":
            refunds = data.get("refunds") or []
            if not refunds:
                return "There is no refund request on file for this order.", set()
            first = refunds[0]
            if isinstance(first, dict):
                return (
                    f"Refund {first.get('refund_id', '')} is currently {first.get('status', 'unknown')}.",
                    set(),
                )
        if result.name == "search_knowledge":
            found = data.get("chunks") or []
            if found and isinstance(found[0], dict):
                item = found[0]
                return (
                    f"No answer model is configured. Here is an excerpt from {item.get('title') or 'the policy'}:\n\n> {str(item.get('content') or '').strip()[:260]}",
                    set(),
                )
    chunks = state.get("retrieved_chunks") or []
    if chunks:
        chunk = chunks[0]
        return (
            f"No answer model is configured. Here is an excerpt from {chunk.title}:\n\n> {chunk.content.strip()[:260]}",
            {chunk.chunk_id},
        )
    return (
        "I cannot answer reliably yet. Please share more details or contact a human agent.",
        set(),
    )
