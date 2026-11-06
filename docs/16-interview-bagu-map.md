# Interview and Code Map

This map connects common AI engineering interview topics to the implementation. The project is adapted from an existing system; describe the changes you personally made and the checks you actually ran.

| Topic | Start here | Boundary to explain |
|---|---|---|
| Application architecture | [Architecture](03-architecture.md), `app/agents/graph.py` | One graph with multiple nodes is not a set of separate agents. |
| Intent and routing | `app/agents/nodes/intent.py`, `app/retrieval/adaptive.py` | Labels and route strategies answer different questions. |
| Retrieval | [Retrieval guide](15-ingest-and-retrieval.md), `app/retrieval/` | BM25 and dense retrieval are fused by rank; the English configuration still needs quality measurement. |
| Prompting and tools | [Agents and tools](05-agents-and-tools.md), `app/tools/` | Tool schemas, permissions, and confirmation are enforced in code. |
| Memory and context | `app/memory/` | Compression is not long-term user memory. |
| Reliability | `app/core/retry.py`, `app/services/container.py` | Retries target transient errors; model and vector backends have fallbacks. |
| Evaluation | [Evaluation guide](10-evaluation.md), `eval/` | The evaluation datasets provide regression inputs; model-quality evaluation has not been run yet. |
| Security | [Security guide](09-security.md) | The demo still trusts request-supplied `user_id`; production authentication and ownership checks remain open. |

The previous interview materials referenced external study syllabi. This map records implementation paths in this repository and does not imply those study resources are project dependencies.
