# Adaptive-RAG E-commerce Customer Support · Project Interview Book

A support system moving from answering policy questions to executing order operations must solve three problems at once: **how to choose an execution path, how to find trustworthy evidence, and how to constrain actions with side effects.** This book unfolds along the lifecycle of a single request rather than arranging technical terms into a Q&A table.

The chapter structure references [the table of contents of "Deep Understanding of AI Agents: Design Principles and Engineering Practice"](https://github.com/bojieli/ai-agent-book/tree/main/book): starting from concrete scenarios, progressively explaining mechanisms, source code, and engineering trade-offs. Interview dimensions come from [zero2Agent](https://github.com/ranxi2001/zero2Agent/tree/main/learn-agent-interview); all project descriptions defer to this repository.

The [17-dimension zero2Agent mapping table](../16-interview-bagu-map.md) can be used to find gaps by role. Historical metrics have been verified against the [measured records](../../eval/MEASURED.md) and the [evaluation report](../14-evaluation-report.md); the numbers in the three chapters are not live production results.

## Follow-up question material

After reading the main text, use these materials to practice the interviewer's continuous follow-up questions. They are organized by question, keeping the "short answer + source code details" format, and complement the three chapters' narratives.

| Question bank | Content |
|---|---|
| [Workflow, planning, intent and evaluation](01-langgraph-planning-intent.md) | State machine, Planner/Executor, streaming, retry, intent numbers |
| [Adaptive-RAG and retrieval](02-adaptive-rag-chunking-hybrid.md) | Parsing and chunking, rewriting, Hybrid, multi-hop, recall metrics |
| [Rerank, memory, Skill/MCP and guardrails](03-rerank-memory-skill-mcp.md) | Metric conventions, context budget, tool access and hallucination governance |

> **Answering principle**: for each capability, first point out the business failure it solves, then point to the implementing files, and finally state the test or evaluation method. Where nothing is implemented (multi-agent teams, model training, node checkpointing, GPU platforms), state the boundary explicitly.
