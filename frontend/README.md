# Agentic Support Web Frontend

A chat workbench built with React, TypeScript, and Vite. The UI follows a ChatGPT-style layout with streaming answers, source citations, local session search, and human-confirmation cards.

The streaming endpoint only sends displayable text after the answer passes validation; it never exposes the model's internal JSON, retrieval strategy, or timing information to the user. While generation is in progress, the page shows a waiting state.

## Running locally

Requires Node.js 20.19+ or 22.12+, plus npm.

Start FastAPI from the repository root first (default dev port 8002), then in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8002` by default; you can also point at a different API address via `VITE_API_BASE`.

## Build and checks

```bash
npm test
npm run build
```

The build output goes to `frontend/dist`. Once FastAPI detects that directory, it serves the pages at `/`; the Docker image builds and copies it automatically during the Node build stage.

## Data and identity boundaries

- The browser stores the session list and visible messages in versioned `localStorage`, keeping at most 50 sessions with at most 100 messages each. The backend currently has no history-list endpoint; after clearing browser data or switching browsers, the local list is not restored.
- The `session_id` returned by the backend is saved with the session and reused for follow-up turns.
- Pending confirmations are kept in the server process for 15 minutes; if the service restarts or the request lands on a different process, the operation must be initiated again.
- `VITE_DEMO_USER_ID` defaults to `u_demo` and is for local demo purposes only. The backend **does not yet authenticate** the `user_id` in requests. Before deploying to untrusted users, a trusted authentication layer must bind identity on the server side.
- `VITE_API_BASE` can point to a separately deployed API; in that case the API must explicitly allow the frontend's origin.
