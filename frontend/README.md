# Argus UI — Frontend

React + TypeScript frontend for the Argus Campaign Intelligence System.

## Stack

| Concern | Choice |
|---------|--------|
| Build tool | Vite 4 |
| Framework | React 18 + TypeScript |
| Routing | React Router v6 |
| Markdown rendering | react-markdown v8 + remark-gfm v3 |
| Streaming | fetch + ReadableStream (SSE) |
| State | useState + custom hooks (no global store) |
| Auth | JWT stored in localStorage (dev bypass via env var) |

## Prerequisites

- Node.js ≥ 14.18 (Vite 4 requirement). Note: Vite 5 requires Node ≥ 18.
- Backend running at `http://localhost:8001` — see root `README.md` for setup.

## Getting Started

```bash
cd frontend
npm install
npm run dev       # → http://localhost:5173
```

The Vite dev server proxies `/v1` and `/health` to `http://localhost:8001`, so no CORS configuration is needed during development.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `` (empty) | Backend base URL. Empty = use Vite proxy (dev). Set to absolute URL in production. |
| `VITE_DEV_AUTH` | `true` | Skip JWT auth. Must pair with `ARGUS_PROFILES=develop` on the backend. |

Override defaults in `.env.local` (gitignored).

> **Important:** Keep `VITE_API_BASE_URL` empty in dev. Setting it to `http://localhost:8001` bypasses the Vite proxy and causes CORS failures since the backend has no CORS middleware.

## Running with the Backend

```bash
# Terminal 1 — infrastructure
docker compose up postgres neo4j redis -d

# Terminal 2 — backend (auth disabled)
ARGUS_PROFILES=develop .venv/bin/python -m argus

# Terminal 3 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173`. The backend API docs are at `http://localhost:8001/docs`.

## Project Structure

```
frontend/
├── index.html
├── vite.config.ts          # Dev proxy: /v1 and /health → localhost:8001
├── .env                    # VITE_API_BASE_URL= (empty), VITE_DEV_AUTH=true
├── .env.production         # VITE_API_BASE_URL=https://api.yourdomain.com
└── src/
    ├── main.tsx            # Entry: BrowserRouter + AuthProvider + GlobalStyles
    ├── App.tsx             # Route definitions + sidebar wiring
    ├── vite-env.d.ts       # Vite import.meta.env types
    ├── design/
    │   ├── tokens.ts       # Colors, SKILLS, COLLECTIONS, CLIENTS constants
    │   └── GlobalStyles.tsx # Keyframes, scrollbar, react-markdown table styles
    ├── api/
    │   ├── types.ts        # TypeScript types matching backend response shapes
    │   ├── client.ts       # Base fetch wrapper (auth header, 401 event)
    │   ├── chat.ts         # chatStream() — SSE via fetch+ReadableStream
    │   └── ingest.ts       # uploadFile(), listDocuments(), deleteDocument()
    ├── auth/
    │   ├── AuthContext.tsx # { token, skill, clientId, devMode }
    │   └── useAuth.ts
    ├── hooks/
    │   ├── useChat.ts      # Message state machine + real SSE streaming
    │   ├── useIngest.ts    # Upload queue + 5-second polling
    │   └── useQueryHistory.ts # localStorage-backed recent query list
    ├── components/
    │   ├── layout/Sidebar.tsx
    │   ├── chat/           # ChatView, MessageBubble, StreamingBubble, SourceCard, GraphNode, ...
    │   ├── ingest/         # IngestView, DropZone, CollectionPicker, JobQueue
    │   ├── collections/    # CollectionsView (static — stats endpoint pending)
    │   ├── feedback/       # FeedbackView (stub — Langfuse integration pending)
    │   └── ui/             # Badge, Logo, Spinner, ErrorBanner
    └── pages/              # Thin route wrappers: ChatPage, IngestPage, ...
```

## Routes

| Path | View |
|------|------|
| `/` | Redirect → `/chat` |
| `/chat` | Chat interface with SSE streaming |
| `/ingest` | File upload + document queue |
| `/collections` | pgvector + Neo4j stats dashboard |
| `/feedback` | Eval history (stub) |

## Auth

### Dev mode (`VITE_DEV_AUTH=true`)
No token is sent. The backend (`ARGUS_PROFILES=develop`) uses its `default_skill` and `default_client_id` from `settings-develop.yaml`. The sidebar skill and client selectors are informational only in this mode.

### Production mode (`VITE_DEV_AUTH=false`)
A JWT Bearer token is expected in `localStorage` under key `argus_token`. Claims are decoded client-side (no signature verification — that is the server's job):

```
{ sub, skill, client_id, exp }
```

On a 401 response, the token is cleared and a `argus:unauthorized` custom event fires. A login page is not yet implemented.

## SSE Streaming

The `/v1/chat` endpoint streams tokens via Server-Sent Events. Because `EventSource` does not support POST requests, streaming is implemented with `fetch + ReadableStream` in `src/api/chat.ts`.

Three event types from the backend:

```
event: token   data: {"token": "..."}
event: done    data: {"answer":"...", "sources":[...], "session_id":"..."}
event: error   data: {"detail": "..."}    ← guardrail block or server error
```

## Backend `Source` Response Shape

The `/v1/chat` response returns sources with these fields (matched in `src/api/types.ts`):

```ts
{
  index: number;
  source_file: string;   // filename (NOT "file")
  collection: string;
  page: number | null;
  client_id: string;
  score: number;         // RRF score, typically 0.01–0.10 range (NOT "relevance")
}
```

## Known Limitations

- **Collections view** — vector counts are static placeholders. A `/v1/collections/stats` backend endpoint is needed for live data.
- **Feedback view** — thumbs up/down ratings are stored in `localStorage` only. Langfuse integration is pending.
- **Node version** — Vite 4 is used because the environment runs Node 17. Upgrade to Vite 5 when Node ≥ 18 is available.
- **react-markdown** — pinned to v8 (`remark-gfm` v3). v9/v4 are ESM-only and fail to pre-bundle under Vite 4's esbuild. Do not upgrade until Vite 5 is available.
- **No login page** — auth flow for production tokens is not yet implemented.

## Troubleshooting

**Blank screen on load**
- Check browser DevTools console for module errors.
- Ensure `react-markdown` is v8 and `remark-gfm` is v3 — v9/v4 cause a silent crash with Vite 4.
- Ensure `VITE_API_BASE_URL` is empty in `.env` (not `http://localhost:8001`).

**API calls failing / CORS errors**
- `VITE_API_BASE_URL` must be empty in dev so requests go through the Vite proxy.
- Backend must be running: `ARGUS_PROFILES=develop .venv/bin/python -m argus`.

**Streaming not working / LangGraph pickle error**
- Backend error: `cannot pickle '_thread.RLock' object` — this was fixed by removing component instances from LangGraph state. Ensure `rag_graph.py` fetches components via `get_injector()` inside each node, not from `state`.

## Available Scripts

```bash
npm run dev       # Start dev server at localhost:5173
npm run build     # TypeScript check + production build → dist/
npm run preview   # Serve the production build locally
```
