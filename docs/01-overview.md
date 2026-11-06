# 01 · Product and Problem Definition

> In one sentence: pick Direct / Single / Multi / Agent / Refuse based on question complexity, instead of running one `top_k` vector search against every query.

## What to solve

| Current state | Failure mode | This repo |
|---|---|---|
| FAQ keyword-based support | Long-tail policy questions miss | BM25 + vector + RRF; `top_k` varies with complexity |
| Standard single-hop RAG | Multi-constraint questions (custom order + expired + quality) fall apart | Adaptive routing to Self-RAG multi-hop |
| Unguarded generation | Hallucinations, unauthorized refunds, prompt injection | Faithfulness checks, HITL, injection detection |
| Long-session agents | Token bloat | 128k budget with 50% / 70% / 85% three-tier compression |

### Key points

Strategy is an enum, not string magic. The graph's conditional edges dispatch on `RetrievalStrategy`.

### Code summary

```python
# app/core/enums.py
class RetrievalStrategy(str, Enum):
    DIRECT = "direct"    # greetings, no retrieval
    SINGLE = "single"    # one-hop hybrid
    MULTI = "multi"      # Self-RAG multi-hop
    AGENT = "agent"      # Planner + tools
    REFUSE = "refuse"    # out of scope / boundaries
```

### Why

Squeeze "retrieve or not, how many hops, call a tool or not" into a single enum so you can: test routing in isolation, expose `strategy` in SSE, and meter per-strategy metrics in Prometheus. If it lives inside one big `if query:` block, you cannot explain the failure paths clearly in an interview.

## User-visible behavior

1. Policy questions → retrieve from the knowledge base, always attaching `citations` where possible.
2. `ORD10001` questions → `strategy=agent`, read-only tools look up the order.
3. Refund / cancellation requests → return `pending_action`, only writing to the database after confirmation.
4. Injected or out-of-scope prompts → `refused=true`, tools never run.

Seed orders live in [02 · Quick Start](02-getting-started.md).

## Success criteria (engineering, not a demo)

- Business failures and system failures are separated: `error_code` + HTTP status; "insufficient evidence" is 200 copy, not a 503.
- External calls have timeouts; 429/5xx can be retried, 401/403 cannot.
- RRF, routing, compression, and permissions are all unit-testable (`tests/unit/`).
- Resume numbers must come from `python -m eval.runner`; see [10](10-evaluation.md).

## Non-goals

- No real carrier or payment gateway integrations (orders are repository seed data).

For details, see [12 · Limitations](12-limitations.md).

---

[Documentation home](README.md) · Next chapter [02 · Quick Start](02-getting-started.md)
