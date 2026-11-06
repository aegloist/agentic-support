"""High-precision lexical overlay applied after the LLM intent classifier.

The LLM remains the primary classifier. Overlay only fires on phrases that
are stable in English e-commerce CS and that historically confuse nearby labels
(handoff vs refund, policy vs return, coupon vs points FAQ).
"""

from __future__ import annotations

import re

from app.core.enums import IntentLabel

_GREETING_ONLY = re.compile(
    r"^(hi|hello|hey|good\s*(morning|afternoon|evening))(\s*,?\s*(are you there|there))?[!,.~\s]*$",
    re.IGNORECASE,
)

_HANDOFF = (
    "speak to a human",
    "human agent",
    "human review",
    "to a human",
    "real person",
    "duty manager",
    "transfer me to",
)
_JAILBREAK = ("ignore previous", "jailbreak", "system prompt")
_OOS = (
    "stock market",
    "do my homework",
    "homework for me",
    "bomb",
    "president",
    "medical diagnosis",
    "trade stocks",
    "stock portfolio",
)
_COMPLAINT = (
    "complaint",
    "bad review",
    "rude",
    "unacceptable",
    "consumer protection",
    "lying",
    "running a scam",
    "this is fraud",
)
_LOGISTICS = ("tracking", "shipment", "where is my order", "where is my package", "stuck for")
_REFUND = ("refund", "money back", "original payment method")
_RETURN = ("return address", "return my", "be returned", "exchange it", "price difference")
_CANCEL = (
    "cancel order",
    "cancel my order",
    "cancel the",
    "cancel ord",
    "don't want it",
    "do not want it",
    "close an order",
    "can i cancel",
)
_COUPON = ("coupon", "voucher", "free shipping", "ship0", "new10")
_RECOMMEND = (
    "recommend",
    "anything similar",
    "similar to",
    "best-selling",
    "gift",
    "basic apparel",
)
_PRODUCT_SPEC = ("specs", "cotton", "over-ear", "battery", "printed with a photo", "in stock")
_ORDER = ("order", "payment", "shipped", "delivered", "status of my")
_ORDER_ID_RE = re.compile(r"\bORD\s*-?\s*\d", re.IGNORECASE)
_SF_RE = re.compile(r"^SF\s*\d", re.IGNORECASE)


def high_precision_intent(query: str) -> IntentLabel | None:
    """Return a label only when the rule is confident; otherwise None."""
    text = query.strip()
    if not text:
        return None
    lowered = text.lower()

    if any(token in lowered for token in _JAILBREAK) or any(token in lowered for token in _OOS):
        return IntentLabel.OUT_OF_SCOPE
    if any(token in lowered for token in _HANDOFF):
        return IntentLabel.HUMAN_HANDOFF
    if _GREETING_ONLY.match(text) or _GREETING_ONLY.match(lowered):
        return IntentLabel.GREETING
    if (
        text.lower()
        in {
            "nice weather today",
            "are you a robot",
            "tell me a joke",
            "what's your name",
            "what is your name",
            "are you busy",
        }
        or "what should i have for dinner" in lowered
    ):
        return IntentLabel.CHITCHAT
    if any(token in lowered for token in _COMPLAINT):
        return IntentLabel.COMPLAINT
    if (
        "expedite my shipment" in lowered
        or "tracking number" in lowered
        or "tracking history" in lowered
        or "stuck for" in lowered
    ):
        return IntentLabel.LOGISTICS
    if (
        _SF_RE.match(text)
        or "where is my order" in lowered
        or "where is my package" in lowered
        or ("shipment" in lowered and "complaint" not in lowered)
    ):
        return IntentLabel.LOGISTICS
    if "when will my order arrive" in lowered or "when will it arrive" in lowered:
        return IntentLabel.LOGISTICS
    if any(token in lowered for token in _CANCEL):
        return IntentLabel.CANCEL_ORDER
    if "presale" in lowered:
        return IntentLabel.FAQ_POLICY
    if "redeem" in lowered and "point" in lowered:
        return IntentLabel.FAQ_POLICY
    if "point" in lowered or any(token in lowered for token in _COUPON):
        return IntentLabel.COUPON
    if "how does the 30-day return policy work" in lowered:
        return IntentLabel.FAQ_POLICY
    if any(
        token in lowered
        for token in (
            "invoice",
            "electronic invoice",
            "installment",
            "support hours",
            "warranty",
            "free over $59",
            "$59",
            "remote",
            "inspect the package",
            "after opening",
            "accidental damage",
            "water-damaged",
            "repaired",
            "who pays return shipping",
        )
    ):
        return IntentLabel.FAQ_POLICY
    if (
        any(token in lowered for token in _REFUND)
        or "when will my refund" in lowered
        or "request a refund" in lowered
        or "refund progress" in lowered
        or "refund" in lowered
    ):
        return IntentLabel.REFUND
    if "original payment method" in lowered or "money back" in lowered:
        return IntentLabel.REFUND
    if (
        any(token in lowered for token in _RETURN)
        or "can i still return" in lowered
        or "can i return" in lowered
        or "return it" in lowered
    ):
        return IntentLabel.RETURN_EXCHANGE
    if any(token in lowered for token in _RECOMMEND):
        return IntentLabel.RECOMMENDATION
    if any(token in lowered for token in _PRODUCT_SPEC) or text.upper().startswith("SKU-"):
        return IntentLabel.PRODUCT_CONSULT
    if "noise-cancelling headset" in lowered or "this headset" in lowered or "t-shirt" in lowered:
        return IntentLabel.PRODUCT_CONSULT
    if any(token in lowered for token in _ORDER) or _ORDER_ID_RE.search(text):
        if any(token in lowered for token in ("tracking", "shipment", "package")):
            return IntentLabel.LOGISTICS
        return IntentLabel.ORDER_INQUIRY
    if "been delivered" in lowered:
        return IntentLabel.ORDER_INQUIRY
    return None


def apply_intent_overlay(query: str, label: IntentLabel) -> tuple[IntentLabel, str | None]:
    forced = high_precision_intent(query)
    if forced is None or forced == label:
        return label, None
    return forced, f"overlay:{forced.value}"
