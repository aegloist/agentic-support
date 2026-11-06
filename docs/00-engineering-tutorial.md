# Agentic Support Engineering Guide

This guide traces the current English support demo from a customer message to a cited answer or confirmed tool action. It links to the implementation rather than claiming unmeasured model quality.

## Contents

- [Request flow](#request-flow)
- [Routing](#routing)
- [Search and evidence](#search-and-evidence)
- [Tool safety](#tool-safety)
- [Evaluation](#evaluation)
- [Deployment limits](#deployment-limits)

## Request flow

FastAPI validates the request and assigns trace IDs. `ChatService` builds graph state, and LangGraph routes the request to a direct answer, retrieval, tools, or refusal. Read `app/main.py`, `app/services/chat_service.py`, and `app/agents/graph.py`.

## Routing

Greetings need no retrieval. General policy questions use search. Multi-condition questions may use iterative retrieval. Account-specific questions use tools. Out-of-scope requests are refused. The routing rules are in `app/agents/nodes/intent.py` and `app/retrieval/adaptive.py`.

Adaptive-RAG is a published method name for complexity-aware retrieval. Agentic Support is the project name.

## Search and evidence

Files in `knowledge/` are parsed, chunked, embedded, and indexed. BM25 handles exact terms, dense vectors handle semantic similarity, reciprocal-rank fusion combines ranked lists, and an optional cross-encoder reranks candidates. Rebuild the index after changing the corpus or embedding model. See [ingestion and retrieval](15-ingest-and-retrieval.md).

The policy corpus and prompts are English. No English model-quality results have been measured; see `eval/MEASURED.md`.

## Tool safety

Read-only tools retrieve demo account data. Write actions create pending proposals and wait for explicit confirmation. Permissions, schemas, and idempotency are implemented under `app/tools/` and `app/agents/nodes/`.

## Evaluation

Use English questions and expected policy documents. The starter set checks intent, retrieval, refusal, and tool paths; it does not establish production quality. Record the active model, embedding dimensions, corpus, dataset, date, and raw report. See [evaluation](10-evaluation.md).

## Deployment limits

The API trusts request-supplied `user_id`, and demo orders are local fixtures. Do not expose it to untrusted users until authentication and ownership checks are enforced. See [security](09-security.md) and [deployment](11-deployment.md).
