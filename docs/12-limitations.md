# 12 · Limitations and Roadmap

> In one line: docs must match the code. Below is what is explicitly unfinished or intentionally skipped; once something is fixed, stop describing it as a gap.

## In this chapter

1. [Limitations (checked against code)](#limitations-checked-against-code)
2. [Already fixed](#already-fixed-stop-writing-these-as-gaps)
3. [Not planned](#no-plans-to-pad-the-resume-with)
4. [Next phase](#suggested-next-phase)

## Limitations (checked against code)

| Item | Status | Where to look |
|---|---|---|
| Embedding | Production uses local `BAAI/bge-small-en-v1.5`; hash only when loading fails | `app/providers/embeddings.py` |
| Rerank | Local Cross-Encoder `BAAI/bge-reranker-base`; falls back to lexical overlap when weights aren't installed | `app/providers/reranker.py` |
| Tokenizer | 128k heuristic, not the official tokenizer | `app/memory/budget.py` |
| Orders / logistics | Seed data + repositories, no carriers | `app/services/seed.py` |
| Knowledge base updates | Full ingest at startup, no delete API | `app/retrieval/ingest.py` |
| Document parsing | Production uses Unstructured (PDF/Office/HTML/images); degrades to Markdown heading chunking when deps are missing or under testing. OCR / complex tables are not guaranteed | `app/retrieval/unstructured_parser.py` |
| Text cleaning | Post-chunking NFKC / whitespace / hard line breaks; exact dedup; near-duplicates are only logged. No embedding clustering, no Chinese numeral rewriting. "seven days" stays "seven days" | `app/retrieval/cleaning.py` |
| Knowledge base PII | Only non-`.md` documents go through `mask_pii` before ingest; policy Markdown and log masking are handled separately | `app/core/security.py` |
| Multi-tenancy | None; string `user_id` isolation | `OrderRepository.get_visible_order` |
| Authentication | Private-demo bearer tokens map to server-side user IDs; public registration and identity-provider integration are not implemented | `app/api/routes/chat.py` |
| Demo data | Not written automatically at startup; run `python -m scripts.seed_demo` explicitly, repeatable | `scripts/seed_demo.py` |
| Startup migrations | `create_all`; Alembic versions exist but are not run by default | `alembic/versions/` |

## Already fixed — stop writing these as gaps

| Capability | Code |
|---|---|
| SSE tokens | `ChatService.stream` sends segments only after the answer passes validation; the client shows a waiting state during generation |
| MCP executable | `app/mcp/runtime.py`, `MCPToolProxy.execute` |
| On-demand Skill loading | `match_skill` + Planner narrows the catalog |
| Execution-layer fallback | `execute_with_fallback` |
| Faithfulness LLM self-correction | `self_correct_answer` |
| Unstructured multi-format ingest | `app/retrieval/unstructured_parser.py` (testing / missing extra degrades to Markdown) |
| Post-chunking cleaning and exact dedup | `app/retrieval/cleaning.py` |

## No plans to pad the resume with

- Kafka / Celery: there are no outbound async jobs
- Elasticsearch: in-memory BM25 is enough for the policy corpus size
- Forcing hash vectors into the Hybrid fusion: it would drag Hit@1 down in eval
- Passing lexical overlap off as a Cross-Encoder
- Unstructured Cloud / Transform MCP
- Embedding clustering that would drop near-duplicate policy clauses

## Suggested next phase

1. Swap in a larger embedding and rerun `--task retrieval` separately; do not republish the small numbers as bge-m3.
2. RRF did not beat small-only on this set; to prove fusion helps, change the set or break down the failure cases.
3. Add trusted authentication and bind `user_id` server-side; do not trust the request body directly.
4. Move startup to Alembic.
5. Incremental knowledge-base deletion and `policy_version` filtering.

When behavior changes, update this chapter, [10](10-evaluation.md), and [14 · Evaluation Report](14-evaluation-report.md) in the same pass. The README keeps only the entry point and the measured-results table.

---

Previous chapter [11](11-deployment.md) · [Back to index](README.md)
