# 09 · Security and Guardrails

> In one line: user queries and retrieved content are both untrusted; write tools default to deny; orders show up as "not found" for non-owners.

## In this chapter

1. [Secrets](#secrets)
2. [Prompt Injection](#prompt-injection)
3. [Query boundaries](#query-boundaries)
4. [Tool chain](#tool-chain)
5. [Write operations](#write-operations)
6. [Dependency degradation](#dependency-degradation)

Covers: `app/guardrails/`, `app/tools/permissions.py`, `app/config/settings.py`.

## Secrets

- `.env` is gitignored; the image does not COPY `.env`
- Typed as `SecretStr` to avoid leaking via `str(settings)`
- If a secret ever lands in chat history → rotate it in the provider console

### Code summary

```python
# app/config/settings.py
deepseek_api_key: SecretStr = SecretStr("")
admin_api_token: SecretStr = SecretStr("")
```

Admin surface: with `APP_ENV=production` and no `ADMIN_API_TOKEN` configured → admin returns 401 outright. Comparison uses `hmac.compare_digest`.

## Prompt Injection

### Key points

Two layers: ① a regex on the user query blocks obvious jailbreaks; ② retrieved/tool content is treated as data, and the answer prompt carries `UNTRUSTED_CONTEXT_BANNER`. If `Ignore previous instructions` appears in the knowledge base, it must never be escalated to a system instruction.

### Code summary

```python
# app/guardrails/injection.py
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"(ignore|disregard)\s+(the\s+)?(above|previous|preceding)\s+(instructions?|prompts?)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"system\s*prompt", re.I),
)

def detect_prompt_injection(text: str) -> None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise GuardrailError(..., error_code=ErrorCode.PROMPT_INJECTION_BLOCKED)
```

The guardrail node sits at the very front of the Graph: `apply_guardrail` → on a hit, `refuse_answer`, no tool calls.

Unit tests: `tests/unit/test_guardrails.py`, `tests/e2e/test_chat_api.py`.

### Why

Regex alone cannot stop stealthy injections, so retrieved content never enters the system role. The banner is `UNTRUSTED_CONTEXT_BANNER` in `app/core/constants.py`.

## Query boundaries

Out-of-scope topics (illegal, political, medical diagnosis, stock tips, etc.) → `QUERY_OUT_OF_SCOPE` / `strategy=refuse`. Implementation: `app/guardrails/boundary.py` + the `out_of_scope` intent.

## Tool chain

```text
LLM JSON → Schema (Pydantic) → business validation (order visibility) → permissions (HITL) → Tool.execute
```

### Code summary

```python
# app/tools/base.py
def parse(self, arguments) -> BaseModel:
    return self.input_model.model_validate(arguments)  # failure → InvalidRequestError

async def run(self, arguments, context) -> ToolResult:
    parsed = self.parse(arguments)
    return await self.execute(parsed, context)
```

Orders uniformly show as "not found" to non-owners, including `u_demo` and `anonymous`; read/write is only allowed when the order's `user_id` matches the value in the request. Demo orders belong solely to `u_demo`. The current API has no identity authentication yet, so callers can still fill in `user_id` themselves — it therefore cannot be exposed directly to untrusted clients; in production, authentication must happen at a trusted gateway that binds the user identity, and authorization must not rely on the `user_id` in the request body.

`order_id` regex `^[A-Za-z0-9_-]+$`. SQL uses bound parameters; `ILIKE` escapes `%` and `_`.

## Write operations

Refunds/cancellations require confirmation. Timeout retries rely on idempotency keys. The audit log records only `trace_id` + action + `order_id`. See [05 · HITL](05-agents-and-tools.md#hitl-and-idempotency) for details.

## Dependency degradation

| Dependency | On failure |
|---|---|
| Redis | In-memory rate limiting / cache (not shared across replicas) |
| Qdrant | In-memory vector ingest |
| Embedding / local bge-small | If loading fails: hash placeholder; if loaded: local `BAAI/bge-small-en-v1.5` |
| Cross-Encoder | If weights not loaded: lexical overlap; if loaded: local `bge-reranker-base` |
| DeepSeek | Fake at startup; 503 for in-flight requests at runtime — never fabricates a successful answer |

---

Previous chapter [08](08-reliability.md) · Next [10 · Evaluation](10-evaluation.md)
