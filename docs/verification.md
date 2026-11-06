# Local verification

Verified on 2026-11-06 with Python 3.14.7 and the existing Node/Vite toolchain.

## Automated checks

- Python suite: 172 passed, one upstream LangChain deprecation warning.
- Coverage: 72.67%, above the existing 70% CI threshold.
- Frontend: six tests passed; TypeScript and production build passed.
- Ruff lint and formatting, mypy, and `git diff --check` passed.
- All three Docker Compose configurations passed `config --quiet`. Images were not built or deployed during this verification.

## Running API checks

The built frontend and API ran locally against an isolated SQLite database with seeded demonstration orders. No external model API was called. Capabilities reported offline generation, hash embeddings, and lexical reranking.

Real HTTP requests verified:

1. Anonymous chat returns 401; the configured access token resolves to its server-side user.
2. A question about standard returns cites `return_policy` and returns the 30-day window.
3. An order lookup returns the seeded shipment status.
4. Requesting cancellation creates a confirmation proposal and leaves the order paid.
5. Another authenticated user cannot confirm that action or read its conversation.
6. The owner confirms the action; the persisted order becomes cancelled.
7. Replaying that confirmation returns the idempotent result.
8. Streaming emits the final answer, and foreign sessions return 404 before the SSE response starts.

The first policy check exposed the fallback reranker's character-based comparison. It now uses English word tokens and ignores common query words; the same HTTP check then returned the correct policy. The existing reranker test covers that example.

## Verification limits

Windows Chrome automation could not connect: WSL interop calls timed out, and the installed harness reported no active browser connection. Browser interaction and visual appearance are not marked verified. The built UI is served successfully, and its authentication request and history isolation have unit coverage.

Live generation quality, local BGE weight loading, remote embeddings, Qdrant, Docker image execution, and public hosting were not verified. The existing multi-instance setup also keeps pending confirmations in each process, so use one API process for the private demo.

## Repeat locally

Configure `AUTH_TOKENS` in the ignored `.env`, then run:

```bash
python -m scripts.seed_demo
uvicorn app.asgi:app --host 127.0.0.1 --port 8002
```

In another terminal, start the frontend with `cd frontend && npm run dev`, open `http://127.0.0.1:5173`, and enter the token associated with `u_demo` in `.env`. Keep the token private. The demo order cancellation changes local sample data, so use a separate database for repeated destructive checks.
