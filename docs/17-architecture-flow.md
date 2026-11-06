# Request Flow

The API accepts a support message, assigns request and trace IDs, and sends the request through the LangGraph workflow. The graph selects a direct answer, retrieval, tools, or refusal. Write actions pause for customer confirmation. The final response includes citations when retrieved evidence supports them.

```mermaid
flowchart LR
  U[Customer] --> API[FastAPI request validation]
  API --> S[ChatService]
  S --> G[Safety and routing graph]
  G -->|Greeting or simple message| D[Direct answer]
  G -->|Policy question| R[Hybrid retrieval]
  G -->|Order or product action| T[Permission-checked tools]
  G -->|Unsafe or unrelated request| F[Refusal]
  R --> A[Grounded answer and evidence check]
  T --> C{Write action?}
  C -->|Yes| H[Pending action and customer confirmation]
  C -->|No| A
  H --> A
  D --> A
  F --> A
  A --> O[Answer, citations, trace ID]
```

The graph is implemented in `app/agents/graph.py`; API and lifecycle wiring are in `app/main.py` and `app/services/container.py`. For retrieval details, see [04 · Adaptive Retrieval](04-adaptive-rag.md). For tool permissions and confirmation, see [05 · Agents and Tools](05-agents-and-tools.md).
