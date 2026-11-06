# 11 · Deployment and Operations

> In one line: the default Compose setup uses SQLite and the built-in retriever, a single container starts both the API and the Web UI; Redis, Qdrant, and Postgres can still be brought in as needed; `.env` never goes into the image.

## In this chapter

1. [Local](#local)
2. [Docker Compose](#docker-compose)
3. [Production checklist](#production-checklist)
4. [Scaling, knowledge base, rollback](#scaling-knowledge-base-rollback)

## Local

SQLite + in-memory vectors — see [02](02-getting-started.md).

## Docker Compose

Copy `.env.example` to `.env` and configure `AUTH_TOKENS` before starting. Each token must be unique, randomly generated, and at least 32 characters long. Chat is authenticated; the web sign-in form asks for the access token. `LLM_*` selects the generation endpoint; the default demo intentionally uses hash embeddings and lexical reranking unless a real embedding API is configured.

```bash
docker compose up --build -d
```

Once started, visit `http://127.0.0.1:8000`; stop with `docker compose down`. Data is persisted in the Compose volume `adaptive-rag-data`.

### Three run modes

| Mode | Compose file | Components | Use case |
|---|---|---|---|
| Default demo | `docker-compose.yml` | API, frontend, SQLite | Fewest dependencies, auto degradation |
| Single-node production | `docker-compose.single.yml` | API, frontend, PostgreSQL, Redis | Long-running single node |
| Multi-instance experiment | `docker-compose.multi.yml` | Nginx, dual API, PostgreSQL, Redis, Qdrant | Experimental: pending confirmations remain process-local |

```bash
# Set the database password first for single-node and multi-instance modes
export POSTGRES_PASSWORD='change-this-password'
docker compose -f docker-compose.single.yml up --build -d
docker compose -f docker-compose.multi.yml up --build -d
```

The single-node and multi-instance images install `.[rerank]`. When local Embedding / Cross-Encoder is enabled, the first start may download models; without an LLM key it still answers using offline evidence.

| Container | Role | API port |
|---|---|---|
| `api` | FastAPI | 8000 |

### Code summary

```yaml
# docker-compose.yml
api:
  environment:
    DATABASE_URL: sqlite+aiosqlite:///./data/local/app.db
    REDIS_URL: ""
    QDRANT_URL: ""
    APP_ENV: production
```

Health checks hit `http://127.0.0.1:8000/api/v1/health`. Image runs non-root, and COPY comes before `pip install .`.

## Production checklist

- [ ] `APP_ENV=production`, `LOG_LEVEL=INFO`
- [ ] `ADMIN_API_TOKEN` is set
- [ ] `DATABASE_URL` points to Postgres, connection pool reviewed
- [ ] Real embedding gateway (otherwise treat BM25 as the primary retrieval surface externally)
- [ ] After `pip install -e ".[rerank]"`, rerun retrieval; the report must contain `hybrid+cross-encoder`
- [ ] After `pip install -e ".[docs]"`, verify ingest with real PDFs/scans; after any chunking change, rerun `--task retrieval`
- [x] `u_demo` / `anonymous` global order reads are disabled
- [x] Private-demo bearer tokens bind identity on the server; the request-body user ID is ignored
- [x] Conversation and order access is checked against the authenticated user
- [ ] HTTPS, token provisioning, and revocation process reviewed before deployment
- [ ] liveness / readiness separated (see [08](08-reliability.md#health-checks))
- [ ] No secrets in logs, images, or README
- [ ] Long-running Postgres uses Alembic (startup still runs `create_all` for now)

## Scaling, knowledge base, rollback

Use one API process for the current private demo. Conversation history lives in the DB, but pending confirmations live in memory for 15 minutes. A restart discards pending confirmations, and the experimental multi-instance layout can route a confirmation to another process. Do not describe that layout as verified for confirmed actions. In-process rate limiting is not shared across replicas → configure Redis in production. The Graph is compiled once per process.

After changing documents in `knowledge/`, restart the API. `chunk_id` values are stable under identical chunking, and Qdrant upsert overwrites. No CMS. Production ingest uses Unstructured; the system package needs poppler, tesseract (`eng`), and libreoffice for Office files. After any parser change, rerun `--task retrieval`.

Rolling back the image also discards in-memory pending confirmations. Persistent database changes must be considered separately. Alembic `0002` added the refunds table; schema rollback requires an explicit `downgrade`.

---

Previous chapter [10](10-evaluation.md) · Next [12 · Limitations](12-limitations.md)
