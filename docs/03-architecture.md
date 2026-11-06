# 03 · System Architecture

> In one sentence: the Graph is compiled once in-process; a fresh DB session is created per request and handed to tools via contextvars — never bake connections into the graph.

## Chapter Contents

1. [Layering](#layering)
2. [Startup and Request Lifecycle](#startup-and-request-lifecycle)
3. [Request-Scoped DB Session](#request-scoped-db-session)
4. [LangGraph State Machine](#langgraph-state-machine)
5. [State Design](#state-design)
6. [Directory Responsibilities](#directory-responsibilities)
7. [The Three Questions of Technology Choice](#technology-choices-the-three-questions)

Covers: `app/main.py`, `app/services/chat_service.py`, `app/agents/graph.py`, `app/core/request_scope.py`.

## Layering

```text
Request
  → API           protocol, Pydantic, trace_id
  → ChatService   rate limiting, UoW, invokes the compiled Graph
  → LangGraph     guardrail → intent → routing → retrieval|planning → generation → faithfulness → compression
  → Retriever / ToolRegistry / Repository
  → Provider      DeepSeek / Embedding / Cross-Encoder
  → SQLite|Postgres · in-memory vectors|Qdrant · optional Redis
```

Use this one for the interview whiteboard (same framework as [13 · Interview Script](13-interview-engineering-rag.md)):

```text
┌─────────────────────────────────────────────────────────┐
│ Access   FastAPI · SSE · rate limiting · ChatService      │
├─────────────────────────────────────────────────────────┤
│ Orchestration   guardrail → intent → Adaptive five-way routing   │
│        Direct / Refuse / Single / Multi / Agent         │
│        → generation → faithfulness → compression        │
├──────────────────────┬──────────────────────────────────┤
│ Retrieval  rewrite BM25    │ Tools  15 + Skill + MCP + HITL   │
│       RRF vector      │      read-failure Fallback      │
│       Self-RAG ≤3     │                                 │
├──────────────────────┴──────────────────────────────────┤
│ Foundation   DeepSeek · Cross-Encoder · DB · Redis · Qdrant/in-memory │
└─────────────────────────────────────────────────────────┘
```

### Key Points

The API contains no business logic; the Graph only orchestrates; SQL lives in repositories; models live in providers. Tests can use a Fake LLM plus SQLite.

### Why

Swapping protocols (HTTP → internal RPC) only touches `app/api/`. Swapping models only touches `providers/`. Swapping retrieval implementations does not change node names. This is the standard interview answer to "why not just one `chat()` function".

## Startup and Request Lifecycle

### Key Points

On process start: `build_container` inside `lifespan` (creates tables, ingests the knowledge base, compiles the Graph).

Per HTTP request: middleware binds `trace_id` → `ChatService.chat` opens a session → `graph.ainvoke` → commit.

### Code Summary

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = await build_container(get_settings())
    app.state.container = container
    try:
        yield
    finally:
        await container.aclose()


@app.middleware("http")
async def request_context(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or new_trace_id()
    tokens = bind_request_context(trace_id=trace_id, request_id=request_id)
    request.state.trace_id = trace_id
    try:
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response
    finally:
        reset_request_context(tokens)
```

```python
# app/services/chat_service.py  (compiles the graph at construction time)
self._graph = build_graph(
    llm=llm, settings=settings, retriever=retriever,
    reranker=reranker, registry=self.registry,
)
```

### Why

The graph is compiled once: the Retriever/LLM inside node closures are process-level singletons, avoiding a fresh `StateGraph.compile()` per request.

The `trace_id` comes in from the request header and is written back to the response header, so nginx / frontend / logs can be correlated.

## Request-Scoped DB Session

### Key Points

Tools run inside graph nodes, but a SQLAlchemy session cannot be stored on the compiled graph — that would cross-wire requests. Use `contextvars`.

### Code Summary

```python
# app/core/request_scope.py
_db_session: ContextVar[AsyncSession | None] = ContextVar("db_session", default=None)

def get_db_session() -> AsyncSession:
    session = _db_session.get()
    if session is None:
        raise RuntimeError("no request-scoped database session")
    return session

@asynccontextmanager
async def request_session(factory) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        token = _db_session.set(session)
        try:
            yield session
        finally:
            _db_session.reset(token)
```

`ChatService.chat` wraps itself in `async with request_session(...)`, and tools fetch the current request's connection via `get_db_session()`. Commit at the end; roll back on exception.

### Why

LangGraph node signatures are `state -> partial state`; there is nowhere to "pass in the db". Stuffing the session into `AgentState` would make the state non-serializable and hard to test. contextvars are the async-safe, request-level slot.

## LangGraph State Machine

### Key Points

Node names must not collide with `AgentState` keys (hence `classify_intent`, not `intent`).

Conditional edges branch five ways based only on `strategy`.

### Code Summary

```python
# app/agents/graph.py
def _route_after_complexity(state: AgentState) -> str:
    strategy = state.get("strategy") or RetrievalStrategy.SINGLE
    return {
        RetrievalStrategy.DIRECT: "generate_answer",
        RetrievalStrategy.REFUSE: "refuse_answer",
        RetrievalStrategy.SINGLE: "retrieve_docs",
        RetrievalStrategy.MULTI: "retrieve_docs",
        RetrievalStrategy.AGENT: "plan_tasks",
    }[strategy]
```

```text
START → apply_guardrail
          ├ refused → refuse_answer → compact_memory → END
          └ classify_intent → route_complexity
                 ├ DIRECT / generation
                 ├ REFUSE / refusal
                 ├ SINGLE|MULTI / retrieve_docs → generate_answer
                 └ AGENT / plan_tasks → execute_tools → generate_answer
          → check_faithfulness → compact_memory → END
```

Both `SINGLE` and `MULTI` enter `retrieve_docs`; inside the node, `strategy` decides whether to run Self-RAG (see [04](04-adaptive-rag.md)).

### Why

Conditional edges are clearer than "another if inside generate": SSE can report progress per node name; `MAX_AGENT_STEPS` stays bounded; unit tests can run just `planner_node`.

## State Design

### Key Points

`AgentState` is `TypedDict, total=False`: dicts returned by nodes **replace** the listed keys.

Do **not** use `Annotated[list, add]` to append messages infinitely — compression is done explicitly in `compact_memory`.

### Code Summary

```python
# app/agents/state.py
class AgentState(TypedDict, total=False):
    user_query: str
    intent: IntentResult | None
    strategy: RetrievalStrategy | None
    retrieved_chunks: list[RetrievedChunk]
    plan: AgentPlan | None
    tool_results: list[ToolResult]
    pending_action: ActionProposal | None
    final_answer: str | None
    token_usage: TokenUsage
    latency: LatencyBreakdown
```

### Why

Automatic reducer append would blow the 128k token budget in long sessions and makes assertions impossible. An explicit compression node keeps "when to summarize" measurable and observable.

## Directory Responsibilities

| Path | Responsibility |
|---|---|
| `app/api/` | routes, DI |
| `app/schemas/` | request/response/retrieval/order schemas |
| `app/services/` | ChatService, container, seeding |
| `app/agents/` | state machine and nodes |
| `app/retrieval/` | parsing, cleaning, chunking, BM25, vectors, RRF, Adaptive, Self-RAG |
| `app/tools/` | 15 tools, permissions, Registry |
| `app/mcp/` | MCP → the same `Tool` interface |
| `app/skills/` | on-demand workflow JSON |
| `app/repositories/` | orders/sessions/idempotency |
| `app/providers/` | LLM / Embedding / Rerank |
| `app/guardrails/` | injection, boundaries, faithfulness |
| `app/memory/` | token budget |
| `app/prompts/` | versioned templates |
| `app/observability/` | logs, metrics, context |

## Technology Choices (The Three Questions)

Every middleware should answer: why this, why not X, and what happens without it.

| Component | Why | What if not |
|---|---|---|
| LangGraph | conditional edges, step caps, testable nodes | routing smeared into one function |
| FastAPI | validation, OpenAPI, SSE | hand-rolled protocol |
| DeepSeek | OpenAI-compatible, isolated behind `LLMProvider` | tests use a Fake |
| RRF | BM25 and cosine have different scales; fuse **rank** | adding scores skews one branch |
| Cross-Encoder | joint query+doc scoring | paraphrased policy questions rank unstably on lexical/RRF alone |
| Qdrant | independently deployable, stable point ids | in-memory vector store also works locally |
| Postgres | orders/audit/idempotency | local SQLite |
| Redis | rate limiting + policy caching; fails open | in-process implementation |

Kafka / Celery / ES are **not** included: no real need for outbound queues or a retrieval log lake.

---

Previous chapter [02](02-getting-started.md) · Next chapter [04 · Retrieval](04-adaptive-rag.md)
