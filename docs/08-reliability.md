# 08 · Reliability and Observability

> In one line: split your timeouts; retry only transient errors with full jitter; rate limiting fails open when Redis is down, authentication fails closed.

## In this chapter

1. [Timeouts](#timeouts)
2. [Retries](#retries)
3. [Failure semantics](#failure-semantics)
4. [Health checks](#health-checks)
5. [Logs and metrics](#logs-and-metrics)

Covers: `app/core/retry.py`, `app/providers/deepseek.py`, `app/observability/`.

## Timeouts

### Key points

`httpx.Timeout(connect=3, read=LLM_TIMEOUT_SECONDS, write=10, pool=5)`. Never allow the default infinite read. Qdrant gets 5s; sync calls are wrapped in `asyncio.to_thread`.

### Code summary

```python
# app/providers/deepseek.py
self._client = httpx.AsyncClient(
    base_url=settings.deepseek_base_url.rstrip("/"),
    timeout=httpx.Timeout(connect=3.0, read=settings.llm_timeout_seconds, write=10.0, pool=5.0),
)
```

## Retries

### Key points

Full jitter: `sleep = random(0, min(cap, base * 2^attempt))`. Instances won't slam the provider at the same instant.
**Retry**: timeouts, connection errors, 408/429/502/503/504.
**Don't retry**: 400, 401, 403, 404, 422.

### Code summary

```python
# app/core/retry.py
RETRYABLE_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})
NON_RETRYABLE_HTTP_STATUS = frozenset({400, 401, 403, 404, 422})

def _full_jitter_delay(attempt: int, base: float, cap: float) -> float:
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0.0, ceiling)
```

`DeepSeekProvider.generate` is wrapped in `with_exponential_backoff`. **Streams are never retried mid-flight** (tokens have already been pushed to the user).

Unit tests: `tests/unit/test_retry.py`.

### Why

If 401s were retried, one bad key would multiply into a string of invalid billed calls. Exponential backoff without jitter wakes every replica at the same moment (retry storm).

## Failure semantics

| Situation | To the user | Layer |
|---|---|---|
| Insufficient policy evidence | 200, uncertain / handoff | Business |
| Injection, out-of-scope | 200, `refused=true` | Guardrails |
| DeepSeek timeout | `LLM_TIMEOUT` | HTTP 503 |
| Both retrieval paths fail | `VECTOR_DB_UNAVAILABLE` | HTTP 503 |
| Database down | `DATABASE_UNAVAILABLE` | HTTP 503 |
| Rate limited | `RATE_LIMITED` | HTTP 429; Redis down → **fail-open** |

Rate limiting fails open: a broken rate limiter must not take down the entire support service. Authentication is the opposite — it must fail closed.

## Health checks

- liveness = `/api/v1/health`
- readiness = `/api/v1/ready` (DB is the deciding dependency)

Do not make the LLM health check a real `chat/completions` call.

## Logs and metrics

JSON lines: `timestamp`, `level`, `logger`, `trace_id`, `request_id`. `mask_pii` is applied. Never log API keys. Prompts/tools are not persisted in full by default.

`GET /metrics`: request volume, strategy/intent, per-section intent/retrieval/llm/tool latencies, tool `ok|denied|error|idempotent|fallback`, tokens, hallucination count.

Troubleshooting: look at the per-section timings first. In eval requests with multi-second P95, the LLM usually dominates. Use `x-trace-id` to stitch HTTP → intent → retrieval → tools.

---

Previous chapter [07](07-configuration.md) · Next [09 · Security](09-security.md)
