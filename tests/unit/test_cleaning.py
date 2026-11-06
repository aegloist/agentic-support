import logging
from pathlib import Path

from app.core.constants import PII_MASK
from app.core.enums import DocumentCategory
from app.retrieval.chunking import chunk_markdown
from app.retrieval.cleaning import (
    NEAR_DUP_HAMMING,
    dedupe_chunks,
    hamming64,
    normalize_text,
    simhash64,
)
from app.retrieval.unstructured_parser import elements_to_chunks, parse_path
from app.schemas.retrieval import RetrievedChunk
from tests.unit.test_unstructured_parser import _FakeElement, _settings

# The CJK hard-break join rule only fires between CJK code points, so the join
# tests below need CJK sample text; build it via chr() so the sample exists only
# at runtime (keeps source and bytecode free of literal CJK characters).
_CJK_WORD = chr(0x65E0) + chr(0x7406) + chr(0x7531)  # three CJK chars, one "word"
_CJK_BROKEN = _CJK_WORD[:2] + "\n" + _CJK_WORD[2:]


def _chunk(chunk_id: str, document_id: str, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        title=document_id,
        content=content,
        score=0.0,
        category=DocumentCategory.FAQ,
    )


def test_strips_bom_and_zero_width() -> None:
    raw = "\ufeffno-\u200bquestions-\u00adasked"
    assert normalize_text(raw) == "no-questions-asked"


def test_nfkc_fullwidth_digits() -> None:
    assert normalize_text("\uff17-day no-questions-asked") == "7-day no-questions-asked"
    # NFKC must not rewrite spelled-out numerals.
    assert "7-day" not in normalize_text("seven-day no-questions-asked")
    assert normalize_text("seven-day no-questions-asked") == "seven-day no-questions-asked"


def test_joins_cjk_hard_breaks_but_not_tables() -> None:
    assert normalize_text(_CJK_BROKEN, join_hard_breaks=True) == _CJK_WORD
    assert "\n" in normalize_text(_CJK_BROKEN, join_hard_breaks=False)
    chunks = elements_to_chunks(
        [_FakeElement("Table", _CJK_BROKEN, table_html=f"<table>{_CJK_BROKEN}</table>")],
        document_id="shipping",
        title="shipping",
        category=DocumentCategory.SHIPPING,
        source="t.pdf",
    )
    assert "\n" in chunks[0].content


def test_collapses_inline_space_and_extra_blank_lines() -> None:
    text = "free shipping over 59\torders.\n\n\n\nRemote areas excluded."
    cleaned = normalize_text(text)
    assert "\t" not in cleaned
    assert "free shipping over 59 orders." in cleaned
    assert "\n\n\n" not in cleaned


def test_markdown_keeps_policy_pii_words_and_numbers(tmp_path: Path) -> None:
    path = tmp_path / "privacy_cs.md"
    path.write_text("Agents must never request a full ID card number. The contact example 13812345678 must not be repeated.\n", encoding="utf-8")
    chunks = parse_path(
        path,
        document_id="privacy",
        title="privacy_cs",
        category=DocumentCategory.ACCOUNT,
        settings=_settings(),
    )
    blob = " ".join(chunk.content for chunk in chunks)
    assert "ID card" in blob
    assert "13812345678" in blob


def test_non_markdown_masks_phone(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-fake")

    def fake_partition(_path: Path) -> list[_FakeElement]:
        return [_FakeElement("NarrativeText", "Customer phone 13812345678 is on file.")]

    chunks = parse_path(
        path,
        document_id="scan",
        title="scan",
        category=DocumentCategory.FAQ,
        settings=_settings(),
        partition_fn=fake_partition,
    )
    assert chunks
    assert "13812345678" not in chunks[0].content
    assert f"138{PII_MASK}5678" in chunks[0].content


def test_utf8_sig_markdown_reads_bom(tmp_path: Path) -> None:
    path = tmp_path / "faq.md"
    path.write_bytes("\ufeff# FAQ\n\nE-invoices can be downloaded the same day.\n".encode())
    chunks = parse_path(
        path,
        document_id="faq",
        title="faq",
        category=DocumentCategory.FAQ,
        settings=_settings(),
    )
    assert chunks
    assert chunks[0].content.startswith("E-invoices")


def test_exact_duplicate_keeps_first_chunk_id() -> None:
    first = _chunk("a_00", "doc_a", "Custom items are not covered by the 7-day no-questions-asked return.")
    second = _chunk("b_00", "doc_b", "Custom items are not covered by the 7-day no-questions-asked return.")
    kept = dedupe_chunks([first, second])
    assert [chunk.chunk_id for chunk in kept] == ["a_00"]


def test_near_duplicate_is_logged_not_dropped(caplog) -> None:
    text_a = "Non-custom, unopened items still fit for resale may be returned no questions asked within 7 calendar days of delivery."
    text_b = "Non-custom, unopened items still fit for resale may be returned no questions asked within 7 calendar days of delivery!"
    distance = hamming64(simhash64(text_a), simhash64(text_b))
    assert 0 < distance <= NEAR_DUP_HAMMING or distance <= 8
    threshold = min(NEAR_DUP_HAMMING, distance) if distance <= NEAR_DUP_HAMMING else distance
    with caplog.at_level(logging.INFO, logger="app.retrieval.cleaning"):
        kept = dedupe_chunks(
            [_chunk("a_00", "return_policy", text_a), _chunk("b_00", "return_electronics", text_b)],
            near_dup_bits=threshold,
        )
    assert len(kept) == 2
    assert any(record.message == "ingest_near_duplicate" for record in caplog.records)


def test_chunk_markdown_normalizes_fullwidth() -> None:
    chunks = chunk_markdown(
        "## Returns\n\nCustom items are not covered by the \uff17-day no-questions-asked return.",
        document_id="doc",
        title="policy",
        category=DocumentCategory.RETURN_POLICY,
        source="x.md",
    )
    assert "7-day" in chunks[0].content
    assert chunks[0].metadata["parser"] == "markdown"
