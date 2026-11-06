# Engineering Documentation Guide

This guide describes how to keep project documentation useful, accurate, and tied to code that exists. It is a short writing standard for future edits, not a product feature.

## Explain a mechanism

For each technical topic, answer four questions:

1. What problem does it solve?
2. Where is the implementation?
3. What trade-off does it make?
4. What limitation should a reader know?

Use a concrete support question to introduce the problem, then trace the request through the relevant code. Link to the implementation instead of copying large code blocks that can drift.

## Keep evidence separate from claims

State whether a result is measured, inferred, or planned. A benchmark claim should link to its dataset, command, model configuration, run date, and raw report. Model-quality evaluation has not been run yet. Describe the current datasets as regression inputs until a model evaluation produces a saved report.

## Keep setup reproducible

Document the supported Python and Node versions, required environment variables, startup commands, and expected local behavior. Never include credentials, private customer data, or machine-specific paths. Note when a command needs external model credentials or downloads.

## Keep architecture current

Describe the code as it is now. Explain API flow, graph routes, retrieval, tools, confirmation, data stores, and security boundaries. Move dated migration notes into Git history rather than leaving contradictory descriptions in the current guide.

## English product terminology

Use “Agentic Support” for the product. Use “Adaptive-RAG” only when naming the published retrieval method. Store and UI examples should use the fictional Northstar Market policies and English customer questions.

## Suggested reading order

Start with `README.md`, then read [Architecture](03-architecture.md), [Adaptive Retrieval](04-adaptive-rag.md), [Agents and Tools](05-agents-and-tools.md), [Security](09-security.md), and [Evaluation](10-evaluation.md). The runnable code remains the source of truth.
