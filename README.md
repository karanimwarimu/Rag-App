# RAG_APP

> Retrieval-Augmented Generation (RAG) chatbot — upload your documents, ask questions, and get answers grounded in your own data.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

## Overview

**RAG_APP** is a FastAPI + React (Vite) Retrieval-Augmented Generation service. Documents are ingested through a web UI, split into chunks, embedded with Hugging Face's serverless Inference API, and stored in a **Supabase Postgres + pgvector** vector store. At query time, the user prompt is embedded, the most relevant chunks are retrieved via cosine similarity, reranked with a cross-encoder, and then **answered by a cloud-hosted LLM routed through [litellm](https://github.com/BerriAI/litellm)** (default: Qwen2.5-7B-Instruct on Hugging Face serverless). Answers stream back to the UI over Server-Sent Events.

The frontend and backend are **fully decoupled**: the backend is a pure JSON API (no templates, no static serving), and the frontend is a standalone React + Vite SPA that resolves the API base URL from configuration.

## Features

- **Decoupled two-service architecture** — FastAPI JSON API (`:5000`) + standalone React/Vite SPA (`:5173` locally, Netlify in prod).
- **Document ingestion** — drag-and-drop UI supporting `.docx`, `.txt`, `.pdf`, `.png`, `.jpeg`, `.jpg`.
- **Adaptive, token-aware chunking** — chunk size scales with document length (400 / 600 / 800 tokens, 20% overlap).
- **Serverless embeddings & reranking** — `all-MiniLM-L6-v2` for retrieval, `bge-reranker-large` cross-encoder for relevance ranking, both via HF Inference API.
- **Cloud LLM answer generation** — litellm routes to a configurable provider/model with automatic fallback, hot-swappable via `config.yaml`.
- **Streaming answers (SSE)** — `/api/v1/chat` streams tokens via Server-Sent Events.
- **ChatGPT-style chat UI** — dark, message-bubble interface.
- **Background ingestion** — heavy embed/store work is dispatched as a background task so uploads return immediately.
- **Auth/job scaffolding** — `/api/v1/auth/*` structural stubs (return `501`) and `user_id`/`job_id` request fields, ready for a future real implementation.

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────────────────┐
│   React + Vite (SPA)    │         │              FastAPI (API only)            │
│   frontend/  :5173      │  HTTP   │              :5000                         │
│                         │ ──────▶ │                                            │
│  /            Landing   │ JSON    │  POST /api/v1/chat    (RAG + litellm gen) │
│  /app/chat    Chat      │         │  POST /api/v1/upload  (ingestion)          │
│  /app/upload  Upload    │         │  POST /api/v1/auth/* (501 stubs)          │
│  /app/links   (stub)    │         │                                            │
│                         │         │  embed → pgvector search → rerank → litellm│
└─────────────────────────┘         └───────────────────┬──────────────────────┘
                                                         │
                                                         ▼
                                          Supabase Postgres + pgvector
```

**Ingestion pipeline**
`UploadWorkspace → POST /api/v1/upload → validate → metadata → load (LangChain) → chunk → embed (HF) → store (Supabase)`

**Chat pipeline**
`ChatWorkspace → POST /api/v1/chat → embed prompt (HF) → pgvector search → format context → rerank (HF) → litellm generate (streaming SSE)`

## Tech Stack

| Layer | Technology |
|-------|------------|
| API framework | FastAPI, Uvicorn, Starlette |
| Frontend | React 18, Vite 5, React Router 6, Tailwind CSS 3 |
| Database driver | `asyncpg` (Supabase Postgres + `pgvector`) |
| LLM routing | `litellm` (Google AI Studio / Hugging Face serverless) |
| Embeddings / Reranking | Hugging Face Inference API (`huggingface_hub`, `requests`) |
| Document loading | LangChain community loaders, `unstructured` |
| Chunking | LangChain `RecursiveCharacterTextSplitter` (tiktoken encoder) |
| Config | `config.yaml` (model routing) + `.env` (secrets, via python-dotenv) |

## Repository Structure

```
RAG_APP/
├── frontend/                        # Standalone React + Vite SPA
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── netlify.toml                 # Netlify build config
│   ├── .env.example
│   ├── public/IMAGES/
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                  # router root (routing matrix)
│       ├── config/
│       │   ├── env.js               # typed VITE_* reads (throws if base URL missing)
│       │   └── constants.js         # ALLOWED_EXTENSIONS (mirrors backend)
│       ├── api/
│       │   ├── chat.js              # POST /api/v1/chat (streaming-ready)
│       │   └── upload.js            # POST /api/v1/upload
│       ├── context/
│       │   └── SessionContext.jsx   # auth state (soft-gated via VITE_SKIP_AUTH)
│       ├── components/
│       │   ├── layout/Shell.jsx
│       │   └── auth/ (Login/SignUp/ForgotPassword/OAuthButtons)
│       └── pages/ (Landing, ChatWorkspace, UploadWorkspace, LinkUploaderStub)
├── FASTAPI/                        # Pure API service
│   ├── app_server.py               # app, CORS, router mounts
│   ├── config.yaml                 # model routing (runtime)
│   ├── config.example.yaml
│   ├── configfile.json             # Allowed_Extensions, embedding/reranker model
│   ├── run.py
│   ├── Dockerfile                  # container build (Render)
│   ├── .dockerignore
│   ├── requirements.txt            # pinned deps (incl. litellm, PyYAML)
│   ├── routes/
│   │   ├── chatbot.py              # POST /api/v1/chat (RAG + litellm, SSE)
│   │   ├── fileupload.py           # POST /api/v1/upload
│   │   └── auth.py                 # POST /api/v1/auth/* (501 stubs)
│   └── utilities/
│       ├── .env / .env.example     # Embedding_KEY, reranker_KEY, LLM keys, FRONTEND_ORIGIN
│       ├── llm/
│       │   ├── llm_manager.py       # litellm abstraction (generate + stream + fallback)
│       │   └── config_loader.py     # parses config.yaml
│       ├── schemas/contracts.py     # SessionContext, JobStatus (Pydantic)
│       ├── embedddocuments.py       # HF feature-extraction embeddings
│       ├── results_reranker.py      # HF bge-reranker-large reranking
│       ├── formatfromchroma.py      # context formatting/rechunk helpers
│       ├── documentloader.py        # LangChain loaders (tempfile / STORAGE_DIR)
│       ├── chunkdocuments.py        # adaptive token-aware chunking
│       ├── extractmetada.py / validateFile.py / metadata.py
│       └── database/ (supabase_connect, store_DB, retrieve_DB, .env)
├── Documentation/
│   └── Architecture_plan_final implimentation.md
├── requirements.txt
├── .gitignore
├── README.md
└── RELEASE_NOTES.md
```

## Prerequisites

- **Python 3.11+** and **Node.js 18+** (for the frontend).
- A **Supabase** project with the `pgvector` extension enabled and a `documents` table.
- A **Hugging Face** API token (`Embedding_KEY`, `reranker_KEY`) for embeddings/reranking.
- An **LLM provider key** for answer generation — `HUGGINGFACE_API_KEY` (used by litellm for Qwen) and/or `GOOGLE_API_KEY` (Gemini), configured via `config.yaml`.
- System libraries for document parsing: **Poppler** (`pdftotext`) for PDFs and **Tesseract** for OCR/image text extraction (preinstalled in the Docker image).

## Installation

```bash
# Backend (conda example)
conda create -n ragapp python=3.11 -y
conda activate ragapp
cd RAG_APP/FASTAPI
pip install -r requirements.txt

# Frontend
cd RAG_APP/frontend
npm install
```

## Configuration

### Backend — `FASTAPI/utilities/.env` (git-ignored; copy from `.env.example`)
```
Embedding_KEY=hf_xxxxxxxx
reranker_KEY=hf_xxxxxxxx
HUGGINGFACE_API_KEY=xxxxx       # used by litellm for Qwen
GOOGLE_API_KEY=xxxxx            # used by litellm for Gemini (optional)
FRONTEND_ORIGIN=http://localhost:5173   # CORS allow-list (comma-separated OK)
```

### Backend — `FASTAPI/config.yaml` (runtime model routing; no secrets)
```yaml
llm:
  provider: huggingface
  selected_model: huggingface/Qwen/Qwen2.5-7B-Instruct
  fallback_model: huggingface/Qwen/Qwen2.5-7B-Instruct
  max_tokens: 1024
  temperature: 0.2
  timeout_seconds: 30
```
To switch models, edit `selected_model` (and `provider` if crossing vendors) in `config.yaml` and restart. No code change required.

### Frontend — `frontend/.env` (git-ignored; copy from `.env.example`)
```
VITE_API_BASE_URL=http://localhost:5000
VITE_ENABLE_WEBSOCKET_CHAT=false
VITE_ENABLE_LINK_UPLOADER=false
VITE_SKIP_AUTH=true
```

### Database schema (Supabase)
```sql
create extension if not exists vector;
create table if not exists documents (
    id        text primary key,
    text      text,
    embedding vector(384),
    metadata  jsonb
);
```

## Usage

Start both services in separate terminals:

```bash
# Backend API (terminal 1)
cd RAG_APP/FASTAPI
uvicorn app_server:app --host 0.0.0.0 --port 5000 --reload
# or: python run.py

# Frontend (terminal 2)
cd RAG_APP/frontend
npm run dev
```

| URL | Purpose |
|-----|---------|
| `http://localhost:5173/` | Landing page |
| `http://localhost:5173/app/chat` | Chat interface |
| `http://localhost:5173/app/upload` | Document upload interface |
| `http://localhost:5000/docs` | Backend API docs |

> `VITE_SKIP_AUTH=true` keeps the workspaces open during this transitional phase. Set it to `false` to enforce the auth redirect (the backend auth routes are still `501` stubs).

## API Reference

### POST /api/v1/chat
Retrieve, rerank, and **generate** an answer.
- **Request:** `{ "prompt": "...", "stream": false, "user_id": null, "job_id": null }`
- **Response (non-stream):** `{ "RESULT": "<generated answer>" }`
- **Response (stream: true):** Server-Sent Events, each frame `data: {"token": "..."}` ending with `data: [DONE]`.
- **No match:** `{ "answer": "I couldn't find relevant information...", "sources": [] }`

### POST /api/v1/upload
Upload a single document for ingestion (processed in a background task).
- **Field:** `file` (multipart), optional `user_id`, `job_id`.
- **200:** `{ "message": "File '<name>' uploaded successfully." }`

### POST /api/v1/auth/login · /signup · /forgot-password · GET /api/v1/auth/callback/{google,github}
Structural stubs only — all return **HTTP 501 Not Implemented**.

### GET /chatbot · GET /fileuploader
**Removed.** The backend no longer serves HTML/static assets; the standalone frontend owns all UI.

## Deployment

The app is two independently deployable services: a **FastAPI backend** (JSON API) and a **React/Vite frontend** (static SPA).

### Backend on Render (Docker — recommended)

1. Push the repo; the `FASTAPI/Dockerfile` builds the image (build context = `FASTAPI/`).
2. Render → New → **Web Service** → connect repo → **Environment: Docker**.
3. Start command (Render injects `PORT`):
   ```
   uvicorn app_server:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables (same shape as `FASTAPI/utilities/.env`; **do not commit secrets**):
   | Variable | Purpose |
   |----------|---------|
   | `Embedding_KEY` | Hugging Face embeddings |
   | `reranker_KEY` | Hugging Face reranker |
   | `GOOGLE_API_KEY` | litellm → Gemini (optional) |
   | `HUGGINGFACE_API_KEY` | litellm → HF serverless (Qwen) |
   | `FRONTEND_ORIGIN` | `https://<your-netlify-app>.netlify.app` (CORS allow-list) |
5. `config.yaml` (committed, no secrets) selects the LLM — edit + redeploy to swap models.

> Render can also use its Python buildpack instead of Docker (root `FASTAPI/`, build `pip install -r requirements.txt`, same start command). Docker is recommended so Poppler/Tesseract system libs are reproducible.

### Frontend on Netlify

1. Netlify → New site from Git → connect repo.
2. **Base directory:** `frontend`
3. **Build command:** `npm run build`  (uses `frontend/netlify.toml`)
4. **Publish directory:** `dist`
5. Add build environment variable (inlined at build time):
   | Variable | Value |
   |----------|-------|
   | `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com` |
6. Deploy. To change the backend URL later, redeploy (Netlify → Deploys → Trigger deploy).

> **Vite caveat:** `VITE_*` vars are inlined when `npm run build` runs, not at runtime. Set `VITE_API_BASE_URL` *before* building; a changed URL requires a rebuild.

### Local container check
```bash
docker build -f FASTAPI/Dockerfile -t rag-backend FASTAPI
docker run --rm -p 5000:5000 --env-file FASTAPI/utilities/.env rag-backend
```

## Known Limitations

- **Auth is stubbed** — `/api/v1/auth/*` return `501`; no real login, hashing, tokens, or sessions yet.
- **Virtual assistant removed** — the floating widget was dropped; no `/api/v1/assistant` backend exists.
- **Web Link Uploader is a UI stub** — `/app/links` is inert, hidden unless `VITE_ENABLE_LINK_UPLOADER=true`.
- **Blocking rerank call** — `results_reranker.py` uses a synchronous `requests.post` inside the async handler (not yet made async).
- **No connection pooling** — new `asyncpg` connection per request.
- **No automated tests / CI**.
- **Dead code remains** — `utilities/storeembeddedfiles.py` (legacy ChromaDB store) and `utilities/postprocessors.py` are unused.

## Roadmap

- [ ] Implement real auth (`/api/v1/auth/*`): password hashing, JWT issuance, Supabase Auth.
- [ ] Real `/api/v1/assistant` backend + link-ingestion pipeline.
- [ ] Migrate `/api/v1/documents/{id}` DELETE + job-status polling.
- [ ] Async reranker (`httpx.AsyncClient`) with retry/backoff + HF rate-limit handling.
- [ ] `asyncpg` connection pool + HNSW index on `documents.embedding`.
- [ ] Remove dead Chroma/Llama code; add automated test suite + CI.
- [ ] Health-check endpoint (`/health`).

## License

MIT License — see the LICENSE file for details.
