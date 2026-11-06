import pytest

from app.agents.nodes.generate import generate_node
from app.agents.nodes.intent import IntentClassifier, rule_based_intent
from app.core.enums import IntentLabel, RetrievalStrategy
from app.providers.fake import OfflineLLMProvider
from app.schemas.retrieval import RetrievedChunk


def test_greeting_prefix_does_not_hide_order_intent() -> None:
    intent = rule_based_intent("hello, I'd like to cancel order ORD10003")
    assert intent.label != IntentLabel.GREETING


@pytest.mark.asyncio
async def test_offline_classifier_uses_rules_not_fake_json() -> None:
    intent = await IntentClassifier(OfflineLLMProvider()).classify(
        "how soon can I get an electronic invoice?"
    )
    assert intent.label == IntentLabel.FAQ_POLICY


@pytest.mark.asyncio
async def test_offline_answer_quotes_evidence_instead_of_test_json() -> None:
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        document_id="policy-1",
        title="Return Policy",
        content="Personalized items are not eligible for the 30-day change-of-mind return; you can request after-sales support if there is a defect.",
        score=1.0,
    )
    result = await generate_node(
        {
            "user_query": "can I still return a personalized item if it has a defect?",
            "strategy": RetrievalStrategy.MULTI,
            "retrieved_chunks": [chunk],
        },
        OfflineLLMProvider(),
    )
    assert "defect" in result["final_answer"]
    assert "label" not in result["final_answer"]
    assert result["citations"][0].chunk_id == "chunk-1"
