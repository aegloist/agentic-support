# Interview Notes: Tools, Context, and Reliability

Use these notes to explain how the support assistant moves from an answer to a safe business action. The examples use the fictional Northstar Market demo.

## 1. Tools have explicit contracts

Each tool declares its name, input schema, risk level, and return shape. Read-only tools retrieve orders, products, inventory, policies, and shipment events. Write tools submit return or refund requests; cancellation is destructive. The registry and risk checks are under `app/tools/`.

## 2. Why does a write action wait?

The planner can propose a write action, but the executor will not run it until the customer confirms the pending action. Confirmation is tied to the action ID. Idempotency prevents the same confirmed request from creating duplicate effects. See `app/agents/nodes/planner.py`, `executor.py`, and `app/repositories/idempotency.py`.

## 3. How are Skills and MCP different?

Skills narrow the tool set and give the planner an ordered workflow for a type of request. MCP exposes tools through the same registry contract, with local handlers or an optional remote endpoint. Neither bypasses argument validation or the permission checks.

See `app/skills/definitions/`, `app/skills/loader.py`, and `app/mcp/`.

## 4. What happens when a provider fails?

Transient failures use bounded retries with jitter. If dense embeddings or a reranker cannot load, the container can fall back to hash embeddings or lexical reranking. These fallbacks keep the demo responsive but do not establish retrieval quality. The active backend is exposed through capabilities.

See `app/core/retry.py`, `app/providers/`, and `app/services/container.py`.

## 5. How is conversation context kept bounded?

The token-budget code estimates the message and summary size. At configured thresholds it truncates tool payloads, keeps a sliding window of recent turns, or adds a running summary. This is context compression, not long-term user memory.

See `app/memory/budget.py` and `app/memory/compression.py`.

## 6. What can be claimed from evaluation?

The datasets provide regression inputs. Report quality figures only after a run records its model, corpus, dataset, configuration, date, and raw output in `eval/reports/` and `eval/MEASURED.md`.
