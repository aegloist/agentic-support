# Agentic Support

An English-language e-commerce support assistant built with FastAPI, LangGraph, hybrid search, and a React chat workspace. Customers can ask about store policies, look up demo orders, and request supported actions with explicit confirmation.

This repository contains an adapted and extended project. The current English policy corpus and evaluation set are demonstration material. Live model quality, payment and carrier integrations, and production deployment have not been verified.

## What it does

- Routes greetings, policy questions, multi-condition questions, account-specific requests, and out-of-scope requests to separate paths.
- Combines BM25 lexical retrieval with dense embeddings and reciprocal-rank fusion; optional cross-encoder reranking is available.
- Grounds policy answers in retrieved passages and attaches source citations.
- Uses tools for demo orders, shipment status, product data, returns, refunds, and cancellations.
- Requires customer confirmation before write or destructive actions.
- Provides a streaming chat UI, local conversation history, API health and capability endpoints, and Docker configurations.

## Run locally

Requirements: Python 3.11+, Node.js supported by the frontend, and Docker for the container setup.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Configure AUTH_TOKENS in .env before using chat (instructions below).
uvicorn app.asgi:app --reload --port 8002
```

Chat requires a support access token. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`, then set `AUTH_TOKENS={"u_demo":"YOUR_GENERATED_TOKEN"}` in `.env`. Each unique token identifies one user. Keep it out of Git and frontend build settings. Send it as `Authorization: Bearer ...`; `/api/v1/auth/me` verifies it. To connect the CLI to the API, set `SUPPORT_API_TOKEN` in the CLI process environment. Local CLI mode is a trusted operator process.

The API starts in offline demonstration mode when no model credentials are configured. Offline mode returns source excerpts or verified demo data instead of pretending to generate a full model answer. Set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` for your chosen OpenAI-compatible generation provider. Its chat endpoint must accept `response_format={"type":"json_object"}`. This transport is verified with mocked responses; run a real smoke test with your key before claiming provider compatibility. Local `BAAI/bge-small-en-v1.5` embeddings remain the default; install `.[rerank]` to load local weights. Without those dependencies the runtime uses test/hash embeddings, reported as `bm25+hash` by `/capabilities`. See [configuration](docs/07-configuration.md).

In another terminal, start the web app:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The development server proxies API requests to the local FastAPI service.

## Example

```bash
curl -s http://127.0.0.1:8002/api/v1/chat \
  -H 'content-type: application/json' \
  -H "Authorization: Bearer $SUPPORT_API_TOKEN" \
  -d '{"message":"Can I return a custom mug that arrived damaged?","user_id":"u_demo"}'
```

Seed sample orders with `python -m app.cli --help` for CLI usage and `scripts/seed_demo.py` for the demo seeding entry point. `ORD10001` is shipped, `ORD10002` is delivered, and `ORD10003` is paid but not shipped. Mutating requests return a pending action; confirm it explicitly before execution.

## Architecture

```mermaid
flowchart LR
  U[Web / CLI / HTTP] --> API[FastAPI]
  API --> C[Chat service]
  C --> G[LangGraph routing]
  G --> D[Direct answer]
  G --> R[BM25 + embeddings + fusion + reranking]
  G --> T[Permission-checked tools]
  G --> X[Refusal]
  D --> A[Evidence check and answer]
  R --> A
  T --> A
  X --> A
  A --> O[Answer + citations + trace ID]
```

See [architecture](docs/03-architecture.md), [retrieval](docs/15-ingest-and-retrieval.md), and [tool safety](docs/05-agents-and-tools.md).

## Evaluation

The evaluation datasets provide regression cases for support questions. Model-quality evaluation has not been run yet. See [evaluation status and method](eval/MEASURED.md) and [evaluation guide](docs/10-evaluation.md).

Run checks with `pytest -q` and `cd frontend && npm test && npm run build`.

See [local verification](docs/verification.md) for the checked API workflow, test results, and remaining live-model and browser-verification gaps.

## Security and deployment limits

The private demo verifies bearer tokens against a server-configured user map and ignores caller-provided user IDs. Token issuance and revocation are operator-managed; this is not a public registration system. Local browser history and demonstration orders remain local. Conversation reads and writes are scoped to that authenticated user, including streaming requests. Do not put credentials in source control. Review [security](docs/09-security.md) and [deployment](docs/11-deployment.md).

## Project structure

- `app/`: API, graph nodes, providers, retrieval, tools, and persistence
- `knowledge/`: fictional English store policies
- `frontend/`: React and TypeScript chat interface
- `eval/`: evaluation runner and English starter datasets
- `tests/`: unit, integration, and API tests
- `docs/`: focused English implementation guides

The design uses Adaptive-RAG as a published retrieval approach; the name describes the technique, not the project.
