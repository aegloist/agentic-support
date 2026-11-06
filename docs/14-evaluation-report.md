# 14 · Evaluation Report

## Current status

Model-quality evaluation has not been run for the current corpus and model configuration. No accuracy, retrieval-quality, hallucination-reduction, or live latency score is published.

Automated checks verify application behavior. See [local verification](verification.md) for the recorded test results and checked API workflows, and [evaluation status](../eval/MEASURED.md) for model-quality status.

## Evaluation datasets

| Dataset | Purpose |
|---|---|
| `eval/dataset/intent_100.jsonl` | Support intent classification |
| `eval/dataset/rag_eval.jsonl` | Policy retrieval and evidence-supported generation |
| `eval/dataset/e2e_eval.jsonl` | Refusal, tools, and complete response paths |

Expected document IDs and answer phrases must match the policies in `knowledge/`. These datasets are regression inputs, not measured results.

## Reproduction

Use the commands in the [evaluation guide](10-evaluation.md). Generation and end-to-end model evaluation require provider credentials. Record the actual embedding and reranking backends; hash embeddings and lexical reranking do not measure semantic model quality.

## Reporting a result

For every published score, retain the raw runner output and record:

- The task, command, run date, and repository revision.
- The dataset and corpus versions.
- The generation provider and model, embedding model and dimensions, and reranker backend.
- The baseline, metric definitions, and failures.

Compare BM25, dense retrieval, fusion, and reranking on the same questions. Report keyword evidence checks alongside model-judged faithfulness, since a model judging its own answers can be optimistic. Treat the small end-to-end set as regression coverage rather than a production-quality guarantee.

Previous: [13 · Engineering interview guide](13-interview-engineering-rag.md) · Next: [15 · Ingest and retrieval](15-ingest-and-retrieval.md)
