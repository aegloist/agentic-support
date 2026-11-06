"""English lexical tokenizer for BM25 retrieval."""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Normalize text and retain English words, contractions, and identifiers."""

    return [token.lower() for token in _WORD.findall(text)]
