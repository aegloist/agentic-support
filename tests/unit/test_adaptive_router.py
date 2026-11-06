from app.agents.nodes.intent import rule_based_intent
from app.core.enums import IntentLabel, RetrievalStrategy
from app.retrieval.adaptive import rule_based_complexity
from app.schemas.agent import IntentResult


def test_greeting_goes_direct() -> None:
    intent = rule_based_intent("hello")
    assert intent.label == IntentLabel.GREETING
    routed = rule_based_complexity("hello", intent)
    assert routed.strategy == RetrievalStrategy.DIRECT


def test_order_goes_agent() -> None:
    intent = IntentResult(label=IntentLabel.ORDER_INQUIRY, confidence=0.9, prompt_version="t")
    routed = rule_based_complexity("check order ORD10001", intent)
    assert routed.strategy == RetrievalStrategy.AGENT


def test_policy_multi_hop() -> None:
    intent = IntentResult(label=IntentLabel.FAQ_POLICY, confidence=0.8, prompt_version="t")
    query = "my personalized mug is past the 30-day window but it arrived with a defect, can I still return it?"
    routed = rule_based_complexity(query, intent)
    assert routed.strategy in {RetrievalStrategy.MULTI, RetrievalStrategy.SINGLE}


def test_general_return_policy_does_not_request_order_tools() -> None:
    intent = IntentResult(label=IntentLabel.RETURN_EXCHANGE, confidence=0.8, prompt_version="t")
    routed = rule_based_complexity(
        "what are the rules for the 30-day change-of-mind return?", intent
    )
    assert routed.strategy == RetrievalStrategy.SINGLE


def test_specific_order_return_uses_tools() -> None:
    intent = IntentResult(label=IntentLabel.RETURN_EXCHANGE, confidence=0.8, prompt_version="t")
    routed = rule_based_complexity("can I still return order ORD10002?", intent)
    assert routed.strategy == RetrievalStrategy.AGENT
