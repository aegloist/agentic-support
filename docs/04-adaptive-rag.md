# 04 · Adaptive-RAG and Retrieval

> In one sentence: route complexity first, then decide no retrieval / one-hop hybrid / Self-RAG multi-hop; BM25 and vectors are fused with RRF, which merges **rank**, not scores.

## Chapter Contents

1. [Paper Mapping and Routing](#paper-mapping-and-routing)
2. [Retrieval Nodes](#retrieval-nodes)
4. [RRF](#rrf-fuse-rank-not-scores)
5. [Self-RAG Multi-Hop](#self-rag-multi-hop)
7. [Rerank and Fallback](#rerank-and-fallback)
8. [Caching](#caching)
9. [Evaluation Methodology](#evaluation-methodology)

Covers: `app/retrieval/`, `app/agents/nodes/retrieval.py`, `knowledge/`.

Paper: [Adaptive-RAG (Jeong et al., ACL 2024)](https://aclanthology.org/2024.acl-long.123/). E-commerce additionally adds **Agent** and **Refuse**.

## Paper Mapping and Routing

| complexity | strategy | behavior | `top_k` |
|---|---|---|---|
| simple | `direct` | greetings, no retrieval | — |
| single_hop | `single` | rewrite → hybrid → rerank | `RETRIEVAL_TOP_K_SIMPLE` (3) |
| multi_hop | `multi` | Self-RAG: retrieve → score → rewrite → retrieve again | `RETRIEVAL_TOP_K_COMPLEX` (8) |
| tool_required | `agent` | Planner + tools | 4 within the tool |
| out_of_scope | `refuse` | boundary refusal | — |

### Key Points

Routing must still work even if LLM classification fails. Rules look at intent plus order IDs plus multi-hop cues like "and also / but / after".

### Code Summary

```python
# app/retrieval/adaptive.py
def rule_based_complexity(query: str, intent: IntentResult) -> ComplexityResult:
    if intent.label == IntentLabel.OUT_OF_SCOPE:
        return ComplexityResult(strategy=RetrievalStrategy.REFUSE, ...)
    if intent.label in {IntentLabel.GREETING, IntentLabel.CHITCHAT}:
        return ComplexityResult(strategy=RetrievalStrategy.DIRECT, ...)
    if intent.label in {ORDER_INQUIRY, LOGISTICS, REFUND, ...} or _ORDER_ID.search(text):
        return ComplexityResult(strategy=RetrievalStrategy.AGENT, ...)
    # multi-hop cues → MULTI; otherwise SINGLE
```

`AdaptiveRouter.route()`: calls the LLM with JSON first, and on catching `LLMProviderError` / `LLMOutputError` falls back to the rules above.

### Why

Pure LLM routing is untestable under Fake/timeouts. The rule-based fallback lets `tests/unit/test_adaptive_router.py` run offline. Agents take priority over Multi: when an order ID is present, query the system first rather than searching policies first.

## Retrieval Nodes

### Key Points

`SINGLE` and `MULTI` share the node `retrieve_docs`, branching on `state.strategy` to avoid two nearly identical sets of edges.

### Code Summary

```python
# app/agents/nodes/retrieval.py
async def retrieval_node(state, *, retriever, reranker, rewriter, self_rag, settings):
    top_k = (
        settings.retrieval_top_k_complex
        if strategy == RetrievalStrategy.MULTI
        else settings.retrieval_top_k_simple
    )
    if strategy == RetrievalStrategy.MULTI:
        chunks = await self_rag.retrieve(query, top_k=top_k)
    else:
        rewritten = await rewriter.rewrite(query)
        candidates = await retriever.retrieve(rewritten[0], top_k=top_k)
        chunks = await reranker.rerank(rewritten[0], candidates, top_n=settings.rerank_top_n)
    return {"retrieved_chunks": chunks, "rewritten_queries": rewritten, ...}
```

### Why

`top_k` varies with complexity: 3 documents suffice for simple policies; multi-constraint questions need a larger candidate pool before reranking. Rewriting only runs by default on the single path; for multi it happens within Self-RAG at each hop.

## Self-RAG Multi-Hop

### Key Points

Not special tokens but structured JSON: `relevant` / `sufficient` / `missing_aspect`. At most `MAX_RETRIEVAL_HOPS` (default 3) hops. Break as soon as it's sufficient.

### Code Summary

```python
# app/retrieval/self_rag.py
class GradeResult(BaseModel):
    relevant: bool
    sufficient: bool
    missing_aspect: str = ""

async def retrieve(self, query, *, top_k):
    accumulated = {}
    for _hop in range(self._settings.max_retrieval_hops):
        rewritten = await self._rewriter.rewrite(current_query, missing_aspect=missing)
        candidates = await self._retriever.retrieve(hop_query, top_k=top_k)
        reranked = await self._reranker.rerank(hop_query, candidates, top_n=...)
        for chunk in reranked:
            accumulated[chunk.chunk_id] = chunk
        grade = await self._grade(query, list(accumulated.values()))
        if grade.sufficient:
            break
        missing = grade.missing_aspect or "more specific policy conditions"
    return list(accumulated.values())[: ...]
```

### Why

"Custom-made + past 7 days + quality issue" — a single hop often only matches the general return policy. The second hop uses `missing_aspect` to search for quality exceptions. Hop counts are capped to prevent the Agent from burning its entire budget on retrieval.

## RRF: Fuse Rank, Not Scores

### Key Points

BM25 scores and cosine similarity are not on the same scale. RRF: `1 / (k + rank)`, where `k=60` is Cormack et al.'s default, not a tuned hyperparameter of this project.

### Code Summary

```python
# app/retrieval/fusion.py
def reciprocal_rank_fusion(ranked_lists, *, k=DEFAULT_RRF_K):
    scores: dict[str, float] = {}
    canonical: dict[str, RetrievedChunk] = {}
    for ranked in ranked_lists:
        for rank_position, chunk in enumerate(ranked, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank_position)
            # sort by fused score, source="rrf"
```

Unit tests: `tests/unit/test_rrf.py`.

### Why

If `score = 0.5 * bm25 + 0.5 * cosine`, the scales change whenever the embedding model changes and the weights break. RRF only looks at rank, so both branches contribute equally. `chunk_id` deduplication: when the same chunk is hit by both branches, only one entry is kept and the scores are summed.

## Rerank and Fallback

### Key Points

The production path is a **local Cross-Encoder** (`CrossEncoderRerankProvider`, default `BAAI/bge-reranker-base`). Only when `sentence-transformers` is not installed or weights fail to load does it fall back to lexical overlap — **that is not a Cross-Encoder, do not put it on a résumé**.

Once loaded, `python -m eval.runner --task retrieval` should show `hybrid+cross-encoder`.

### Code Summary

```python
# app/providers/reranker.py
pairs = [(query, document) for document in documents]
scores = await asyncio.to_thread(self._predict, model, pairs)
```

### Why

Cross-Encoders score the query and document together, which fits reranking better than dual-tower/RRF approaches. The lexical fallback only exists so CI / environments without weights don't break. pytest's `APP_ENV=testing` does not download models.

## Caching

Policy queries: TTL defaults to 60s (Redis or in-memory).

Queries containing order IDs or "order": **do not cache** (state changes). Implementation: `app/retrieval/cache.py`.

## Evaluation Methodology

> Historical results notice: the figures below were measured on the prior Chinese corpus with `bge-small-zh-v1.5` on 2026-08-22. They do not measure this English adaptation. Current English evaluation status is recorded in [`eval/MEASURED.md`](../eval/MEASURED.md).


65 items / with `bge-small-zh-v1.5` + Cross-Encoder loaded / report `all_20260822T121308Z.json` (not distributed with the repo):

| System | Precision@1 | Recall@3 | MRR |
|---|---|---|---|
| BM25 | 76.9% | 90% | 0.84 |
| bge-small only | 83.1% | 94.6% | 0.89 |
| BM25 + small + RRF | 83.1% | 94.6% | 0.89 |
| Hybrid + Cross-Encoder | **89.2%** | **97.7%** | **0.94** |

The full table and what can and cannot be claimed is in [10](10-evaluation.md). The pipeline from ingest to reranking is in [15](15-ingest-and-retrieval.md).

---

Previous chapter [03](03-architecture.md) · Next chapter [05 · Agents and Tools](05-agents-and-tools.md)
