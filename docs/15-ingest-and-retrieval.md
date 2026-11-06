# 15 · Parsing, Chunking, Vectorization and Retrieval

> One-liner: a full ingest turns policies into chunks with stable IDs; at question time Adaptive decides whether to retrieve, Hybrid fuses ranks, and the Cross-Encoder does fine-grained reranking.

## Outline

1. [Parsing and Preprocessing](#parsing-and-preprocessing)
2. [Chunking Strategy](#chunking-strategy)
3. [Vectorization](#vectorization)
4. [Vector Database](#vector-database)
5. [Retrieval Strategy](#retrieval-strategy)
6. [Reranking](#reranking)
7. [Evaluation Protocol](#evaluation-protocol)

Covers: `app/retrieval/`, `app/providers/embeddings.py`, `app/providers/reranker.py`, `knowledge/`.

---

## Parsing and Preprocessing

### Key points

The production path uses the open-source Unstructured `partition`, routed by file type. Supported: `.md` `.pdf` `.docx` `.pptx` `.html` and common image formats.

Unstructured lives in the `.[docs]` extra, **not in the main dependencies**. With `APP_ENV=testing` or when the extra is not installed: `.md` goes through `chunk_markdown`, other formats are skipped.

### Pipeline

```text
knowledge/*
  → parse_path (Unstructured; Markdown heading split if dependencies are missing)
  → normalize + mask_pii (non-.md only)
  → exact SHA1 dedup
  → embed → BM25 index + vector upsert
```

### Why

Policy corpora are hand-written Markdown; heading-based splitting is enough. Unstructured is there for PDFs/scans operations throw over the wall, not to replace clean `.md`.

---

## Chunking Strategy

### Key points

Two layers, not semantic adaptive splitting: structural first (`Title` → `section`), then a sliding window.

- `MAX_CHUNK_CHARS=500`, `OVERLAP_CHARS=60`
- Tables are chunked standalone; the sliding window must not cut through them
- `chunk_id` forbids uuid4: use `{document_id}_{two-digit index}` for citation stability

### Why

Policy clauses are written under headings — "7-day no-reason return" and "custom goods" should not share a chunk. 500/60 keeps one policy article from being crammed into a single chunk. uuid4 would change every ingest and break citations and eval.gold matching.

---

## Vectorization

### Key points

Embed **the chunk body**, L2-normalized. The query side uses the same model family.

Priority:

1. `EMBEDDING_API_KEY` + `BASE_URL` configured → remote OpenAI-compatible API
2. Otherwise local `BAAI/bge-small-en-v1.5` (384 dims)
3. Load failure or `APP_ENV=testing` → hash vector fallback (CI placeholder, ~no semantics)

Do **not** describe the hash fallback as semantic retrieval.

### Code summary

```python
# app/providers/embeddings.py
def build_embedding_provider(settings, *, model=None):
    if settings.embedding_configured:
        return OpenAICompatibleEmbeddingProvider(settings)
    local = BgeM3EmbeddingProvider(settings, model=model)  # defaults to the small model; class name is legacy
    if local.available:
        return local
    return HashEmbeddingProvider(dim=settings.embedding_dim)
```

`KnowledgeIngestor.load`: after dedup, `embed([chunk.content for chunk in chunks])`, then `build_records`.

---

## Vector Database

### Key points

If `QDRANT_URL` is set, use Qdrant; the default collection is `cs_knowledge`, distance **COSINE**, and dims must match the embedding model (512 for local small).

If Qdrant is unreachable or startup fails → fall back to `InMemoryVectorStore` (in-process brute-force cosine). BM25 keeps working independently.

Writes are upserts: the same `chunk_id` overwrites. There is no delete API; a full re-ingest replaces.

Payload carries `chunk_id` / `document_id` / `title` / `content` / `section` / `chunk_index` / `policy_version`; retrieval results are rehydrated into `RetrievedChunk`.

### Code summary

```python
# app/retrieval/ingest.py
if qdrant_url:
    store = QdrantVectorStore(qdrant_url, qdrant_collection, embedding_dim)
    try:
        await asyncio.to_thread(store.ensure_collection)
        await asyncio.to_thread(store.upsert, records)
    except Exception:
        logger.warning("qdrant_ingest_failed_using_memory")
# In-memory fallback
```

No Elasticsearch. At the current 39-doc scale, in-memory BM25 + optional Qdrant is enough.

---

## Retrieval Strategy

### Key points

Not every query retrieves. Adaptive picks a strategy first:

| complexity | strategy | retrieval |
|---|---|---|
| simple | `direct` | none |
| single_hop | `single` | rewrite → Hybrid → rerank, `top_k=3` |
| multi_hop | `multi` | Self-RAG up to 3 hops, `top_k=8` |
| tool_required | `agent` | tools; policy queries go through `search_knowledge` |
| out_of_scope | `refuse` | none |

LLM routing failure falls back to rules (intent, order-ID regex, multi-hop cues).

### Hybrid fusion

BM25 and vector each run in their own try/except; fusion is RRF: `1/(k+rank)`, `k=60` is the Cormack et al. default, **not a tuned parameter of this repo**. BM25 scores and cosine similarity are on different scales — never add them directly; only rank-based fusion is valid.

### Code summary

```python
# app/retrieval/hybrid.py
try:
    lexical = self._bm25.search(query, top_k=top_k)
except Exception as exc:
    lexical_error = exc
try:
    dense = await self._vector.search(query, top_k=top_k)
except Exception as exc:
    dense_error = exc
if not lexical and not dense:
    raise RetrievalError("both lexical and dense retrievers failed")
```

---

## Reranking

### Key points

After retrieval, a **local Cross-Encoder** `BAAI/bge-reranker-base` Scores (query, document) **pairs jointly**, not a second pass of the embedding model.

If `.[rerank]` is not installed, weights fail to load, or `testing` skips it → fall back to lexical overlap (that fallback is **not** a Cross-Encoder). Default `rerank_top_n=5`.

### Code summary

```python
# app/providers/reranker.py
pairs = [(query, document) for document in documents]
scores = await asyncio.to_thread(self._predict, model, pairs)

# app/retrieval/reranker.py
# Reorder RetrievedChunk by (original index, score) returned per provider, source="rerank"
```

### Why

RRF can only say "both channels ranked it high"; it cannot judge "does this chunk actually answer the question". The Cross-Encoder sees the full query+chunk, which is what close-paraphrase policy queries need.

---

## Evaluation Protocol

No model-quality result is published yet. Record the current corpus, dataset, model configuration, and raw run output before reporting scores. See [evaluation status](../eval/MEASURED.md).

---

Previous: [14](14-evaluation-report.md) · [Back to contents](README.md)
