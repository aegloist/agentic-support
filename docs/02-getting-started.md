# 02 · Quick Start

> Goal: a successful `POST /api/v1/chat` on your machine within 5 minutes. Defaults to **SQLite + in-memory vectors**; Docker not required.

## Environment and installation

- Python **3.11+** (verified on 3.12)
- Optional `DEEPSEEK_API_KEY` (without it, offline demo mode: shows retrieved source text or verifiable business state)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Local bge-small retrieval + Cross-Encoder rerank: pip install -e ".[rerank]"
# Unstructured parsing for PDF/Office/HTML/images: pip install -e ".[docs]"
# System packages: poppler, tesseract (with chi_sim), libreoffice for Office files
```

Minimal `.env`:

```bash
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./data/local/app.db
DEEPSEEK_API_KEY=sk-...   # optional; offline demo mode without it
```

## What happens at startup

### Key points

`lifespan` calls `build_container`: creates tables, ingests `knowledge/`, compiles the Graph.

### Code summary

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container(get_settings())  # ingest + compile graph
    app.state.container = container
    try:
        yield
    finally:
        await container.aclose()
```

## Health checks and the first question

- `/health`: process alive
- `/ready`: the database is a hard dependency

```bash
curl -s localhost:8002/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Can a custom mug past 7 days still be returned for quality issues","user_id":"u_demo"}'
```

## Demo orders and HITL

| Order | Status | Item |
|---|---|---|
| `ORD10001` | Shipped | Noise-cancelling headphones |
| `ORD10002` | Delivered | Custom mug |
| `ORD10003` | Paid, not shipped | T-shirt |

Cancelling an unshipped order returns `pending_action`:

```bash
curl -s localhost:8002/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Cancel order ORD10003","user_id":"u_demo"}'
# Fill in the session_id and pending_action.action_id from the last response:
curl -s localhost:8002/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Confirm cancellation","user_id":"u_demo","session_id":"sess_...","confirm_action_id":"act_..."}'
```

See [05 · Agents and Tools](05-agents-and-tools.md).

## Tests

```bash
pytest -q
python -m eval.runner --task retrieval
```

## Web frontend

Keep the API running on port 8002, then in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to port 8002; production builds go through `npm run build` into `frontend/dist`, which FastAPI serves at `/`.

Next: [11 · Deployment](11-deployment.md), [06 · API](06-api-reference.md).
