"""English lexical tokenization for BM25."""

from app.retrieval.tokenizer import tokenize


def test_tokenize_empty_input() -> None:
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_tokenize_normalizes_english_and_keeps_identifiers() -> None:
    assert tokenize("REFUNDS, refund-status ORD10001") == ["refunds", "refund-status", "ord10001"]


def test_tokenize_keeps_contractions_and_numbers() -> None:
    assert tokenize("Customer's order 2024") == ["customer's", "order", "2024"]
