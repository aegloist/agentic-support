# Interview Notes: Adaptive Retrieval and Search

Use these notes to explain how the English demo chooses a path and finds policy evidence. Keep claims tied to the current code and identify unmeasured behavior honestly.

## 1. What happens to a policy document?

Files under `knowledge/` are parsed at startup, normalized, split into chunks, embedded, and indexed. Markdown uses heading-based splitting. Chunk IDs are stable across ingest runs so citations continue to refer to the same source chunk.

Start at `app/retrieval/ingest.py`, then follow `unstructured_parser.py`, `cleaning.py`, and `chunking.py`.

## 2. How does the system choose retrieval depth?

The intent classifier identifies the request type. The complexity router then selects a direct answer, one retrieval pass, iterative retrieval, a tool plan, or refusal. This avoids searching policy text for a greeting and avoids treating an order lookup as a general policy question.

The route logic is in `app/retrieval/adaptive.py`; graph transitions are in `app/agents/graph.py`.

## 3. How does hybrid retrieval work?

BM25 finds exact terms and product identifiers. Dense embeddings find semantically similar wording. Reciprocal-rank fusion combines their ranked lists without comparing the raw scores from different systems. An optional cross-encoder reranks the fused candidates.

The relevant files are `app/retrieval/bm25.py`, `vector.py`, `fusion.py`, `hybrid.py`, and `reranker.py`.

No retrieval-quality result is published yet. Evaluate the current corpus and embedding configuration before reporting scores.

## 4. What does multi-hop retrieval add?

The Self-RAG loop grades retrieved evidence for relevance and sufficiency. If evidence is missing, it rewrites the query and retrieves again, up to a configured hop limit. Repeated chunks are deduplicated, and the result set is capped before reranking.

The loop is in `app/retrieval/self_rag.py`. Its grader and rewrite instructions are in `app/prompts/self_rag.py` and `app/prompts/query_rewrite.py`.

## 5. What would you measure?

Use English customer questions with expected source document IDs. Report Precision@1, Recall@3, Hit@k, and MRR for BM25, dense retrieval, fusion, and reranking. Record model, dimensions, corpus, dataset, and run date. See `eval/dataset/rag_eval.jsonl` and `eval/MEASURED.md`.
