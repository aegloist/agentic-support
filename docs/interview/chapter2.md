# Chapter 2 · How knowledge becomes a verifiable answer

"Can a custom item be returned under the seven-day no-questions-asked policy?" looks like a question that only needs one sentence found in a policy document, but it actually contains four consecutive judgments: was the document parsed correctly, were exception conditions preserved through chunking, did retrieval find the relevant evidence, and did the model interpret the evidence as a promise beyond the original text? The quality of RAG depends on the weakest link in this chain.

This chapter starts from the files in `knowledge/` and traces how the answer takes shape along offline indexing, online recall, reranking, multi-hop, and generation checks. Rather than listing algorithm names, ask which specific failure each one solves.

## 2.1 The first boundary: a file is not retrieval evidence

`knowledge/` contains Markdown policies on returns, shipping, and more. At startup, [`ingest.py`](../../app/retrieval/ingest.py) reads and parses the files, and after cleaning, deduplication, chunking, and vectorization, builds an index. The filename determines the document category; the category is not the result of automatic model classification. The current knowledge base is fully loaded at startup; changed files require re-ingesting and cannot be called hot updates or incremental deletions.

Chunking turns long documents into locatable evidence units. [`chunking.py`](../../app/retrieval/chunking.py) uses structural information and windows, generating stable IDs for chunks. Stable IDs let the same evidence be tracked across retrieval results, citations, and evaluation. If chunks are too large, subject-irrelevant rules get pushed into the context together; if too small, "seven-day" and "custom-item exceptions" may scatter into different segments, and the model reads only half. So chunk size is not merely a performance parameter — it also determines whether business exceptions can be expressed at all.

```text
Knowledge files → parse/clean → structural chunking → stable IDs → BM25 and vector indexes
```

Production parsing can call Unstructured to handle many file types; tests or missing dependencies fall back to a simplified Markdown path. Parsing quality differs across formats, and PDF/image support must never be equated to stable OCR quality. For concrete paths and limitations, see the [Parsing and Retrieval Handbook](../15-ingest-and-retrieval.md).

## 2.2 The second boundary: user phrasing is not index phrasing

Users might say "the headphones I bought broke", while the document title reads "After-sales and Warranty for Electronics". [`QueryRewriter`](../../app/retrieval/query_rewrite.py) tries to turn the query into a retrieval-friendlier form; on model failure there is a fallback. But rewriting may also alter factual constraints, so the system still hands the original question and the retrieval results together to later generation and checking.

For single-hop policy questions, the [`retrieval_node`](../../app/agents/nodes/retrieval.py) takes the first rewritten query, runs Hybrid retrieval, then reranks. For `MULTI` questions, the node calls [`SelfRAGLoop`](../../app/retrieval/self_rag.py): each hop rewrites, retrieves, reranks, and judges whether the evidence is sufficient; if not, `missing_aspect` points to what the next hop lacks. The loop is bounded by `max_retrieval_hops`, not by the model saying "continue" indefinitely.

## 2.3 The third boundary: recall and ranking carry different duties

[`HybridRetriever`](../../app/retrieval/hybrid.py) uses BM25 and vector retrieval at the same time. BM25 is sensitive to exact words in policies — model numbers and rule names; the vector path covers synonyms and semantically close phrasings. The score scales of the two paths differ, so [`fusion.py`](../../app/retrieval/fusion.py) merges rankings with RRF instead of adding raw scores. If one path fails, the other can still return results; only when both paths return nothing does the retrieval fail.

Recall is responsible for "don't miss"; reranking is responsible for "put the most suitable first". [`reranker.py`](../../app/retrieval/reranker.py) can load a local Cross-Encoder to rescore candidates. The configured local reranker defaults to `BAAI/bge-reranker-base`; lexical fallback results must be reported separately from Cross-Encoder results.

Compare BM25, dense retrieval, fusion, and reranking on the same questions to measure each stage's contribution. Hybrid retrieval does not guarantee a quality improvement.

See [evaluation status](../../eval/MEASURED.md). Quality scores require a run against the current corpus and configuration.

## 2.4 The fourth boundary: finding a document does not mean the answer is grounded

The generation node takes at most the top few pieces of evidence, together with tool results and the user's question, and maps the model's `citation_chunk_ids` into citations — see [`generate.py`](../../app/agents/nodes/generate.py). If the model call fails, the system produces an extractive fallback answer; if there is no reliable evidence, it asks for more information or escalates to a human.

After the answer is generated, [`faithfulness.py`](../../app/agents/nodes/faithfulness.py) calls an LLM to check whether it is supported by the evidence; unsupported answers get one rewrite attempt, then fall back to an extractive answer. This "faithfulness" is a model judgment, not a logical proof. When the checker is unavailable, [`hallucination.py`](../../app/guardrails/hallucination.py) returns `checker_unavailable`; so you cannot claim every answer received strong verification.

On the streaming path, model tokens may reach the frontend before the faithfulness check finishes. When the final answer is corrected afterward, the user may have already seen the old segment. This is a real trade-off of the current implementation: a faster first-token experience in exchange for possible inconsistency between mid-stream text and the final answer. For production improvements, consider buffering content pending verification or marking the stream as a draft — but these are not currently implemented behaviors.

## 2.5 How to read retrieval metrics

P@1 asks "is the top-ranked evidence relevant", R@3 asks "did relevant evidence make the top three", and generation Faithfulness asks "can the answer be derived from the evidence". The three are not interchangeable. The runner compares document stems with gold labels, and generation evaluation can use the generator as judge. These choices and the small end-to-end dataset limit how far a measured result can be generalized.

See [evaluation status](../../eval/MEASURED.md). Quality scores require a run against the current corpus and configuration.

## Chapter summary

- Offline stages decide evidence granularity; online stages decide which evidence enters the context.
- Hybrid is a recall strategy, RRF is a fusion method, and the Cross-Encoder is candidate reranking; measure each stage's contribution separately.
- Multi-hop only serves questions that need extra evidence, and is bounded by the hop limit.
- Citations and faithfulness checks improve verifiability, but cannot turn model judgment into an absolute guarantee.

**Continue reading**: [Chapter 3 · When the system starts acting](chapter3.md). For question-by-question answers on chunking, rewriting, RRF, and multi-hop, see the [question bank for this chapter](02-adaptive-rag-chunking-hybrid.md).
