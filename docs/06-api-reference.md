# 06 · API Reference

> In one sentence: business denials may return HTTP 200; system failures use 4xx/5xx + `error_code`. Streaming uses SSE, and `token` only carries the displayable answer after validation.

## Conventions

Responses carry `x-trace-id` and `x-request-id`, which can be passed in from request headers. An empty `message` → **422**.

### `GET /api/v1/health`

Process alive, no database check. `{ "status": "ok" }`.

### `GET /api/v1/ready`

Hard dependency: **the database**. Redis / Qdrant / LLM key availability is reported into `dependencies[]`; failures there do **not** flip ready to false.

## `POST /api/v1/chat`

**Request** as defined in `app/schemas/chat.py`. **Response** (`ChatResponse`):

| Field | Meaning |
|---|---|
| `answer` | user-visible answer text |
| `session_id` / `trace_id` | session and trace |
| `intent` / `complexity` / `strategy` | routing explanatory fields |
| `citations` | `document_id` / `title` / `chunk_id` |
| `pending_action` | HITL pending confirmation |
| `refused` | guardrail refusal flag (may still be HTTP 200) |
| `error_code` | business-side denial code (may still be HTTP 200) |
| `token_usage` / `latency` | per-stage milliseconds |

```bash
curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -H 'x-trace-id: tr_debug_001' \
  -d '{"message":"how long until the e-invoice is issued","user_id":"u_demo"}'
```

Routing: `app/api/routes/chat.py` → `container.chat_service.chat(...)`.

## Streaming

### `POST /api/v1/chat/stream`

SSE. Events emit JSON:

| Event | When |
|---|---|
| `started` | request accepted |
| `node` | a LangGraph node finished (e.g. `classify_intent`) |
| `token` | answer text, sent in segments after faithfulness checking |
| `answer` | the final `ChatResponse` |
| `done` | finished |

Implementation: `sse-starlette` + `ChatService.stream`.

## Admin

Admin routes require `x-admin-token` matching the configured `ADMIN_API_TOKEN`; use `hmac.compare_digest` rather than `==`.

## Error Body

System errors use HTTP 4xx/5xx:

```json
{ "error_code": "LLM_TIMEOUT", "message": "DeepSeek request timed out", "trace_id": "tr_..." }
```

| HTTP | Typical `error_code` |
|---|---|
| 400 | `INVALID_REQUEST`, `PROMPT_INJECTION_BLOCKED`, `QUERY_OUT_OF_SCOPE` |
| 401 | `UNAUTHORIZED` |
| 409 | `IDEMPOTENCY_CONFLICT` |
| 422 | validation failure |
| 429 | `RATE_LIMITED` |
| 500 | `INTERNAL_ERROR` (no stack trace in response) |

"Insufficient evidence" is **200 + wording**, not to be conflated with 503. Enum: `app/core/error_codes.py`.

---

Previous chapter [05](05-agents-and-tools.md) · Next chapter [07 · Configuration](07-configuration.md)
