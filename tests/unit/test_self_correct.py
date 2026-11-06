import pytest

from app.agents.nodes.faithfulness import self_correct_answer
from app.guardrails.hallucination import FaithfulnessChecker
from app.providers.base import LLMResponse
from app.schemas.common import TokenUsage
from app.schemas.retrieval import RetrievedChunk


class _SequenceLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def ping(self) -> bool:
        return True

    async def generate(self, messages, **kwargs) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            content = '{"answer":"Custom items are excluded from change-of-mind returns.","citation_chunk_ids":[]}'
        else:
            content = '{"supported":true,"hallucinated_spans":[],"rationale":"ok"}'
        return LLMResponse(content=content, usage=TokenUsage(total_tokens=4), model="fake")


@pytest.mark.asyncio
async def test_self_correct_rewrites_unsupported_answer() -> None:
    llm = _SequenceLLM()
    checker = FaithfulnessChecker(llm)
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="return_policy_0",
        title="Return policy",
        content="Custom items are not eligible for change-of-mind returns.",
        score=1.0,
        rank=1,
        source="bm25",
    )
    from app.guardrails.hallucination import FaithfulnessResult

    first = FaithfulnessResult(
        supported=False, hallucinated_spans=["return at any time"], rationale="unsupported"
    )
    answer, judged, corrected = await self_correct_answer(
        llm=llm,
        checker=checker,
        query="Can a custom mug be returned for change of mind?",
        answer="Every item can be returned at any time.",
        chunks=[chunk],
        tool_results_text="",
        first_result=first,
    )
    assert corrected is True
    assert judged.supported is True
    assert "Custom items" in answer
