# RAG_APP

> Retrieval-Augmented Generation (RAG) chatbot — upload your documents, ask questions, and get answers grounded in your own data.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License](#license)

## Overview
**RAG_APP** is a FastAPI-based Retrieval-Augmented Generation service. Documents are ingested through a web UI, split into chunks, embedded with Hugging Face's serverless Inference API, and stored in a **Supabase Postgres + pgvector** vector store. At query time, the user prompt is embedded, the most relevant chunks are retrieved via cosine similarity, reranked with a cross-encoder, and returned as the answer context.

> **v0.1.0 note:** The final LLM answer-generation step is scaffolded but **not yet enabled** — the local Mistral/Llama generator is reserved for a future desktop build. The `/send_prompt` endpoint currently returns the reranked, retrieved context. See [Roadmap](#roadmap).

Both the embedding model (`sentence-transformers/all-MiniLM-L6-v2`) and the reranker (`BAAI/bge-reranker-large`) are invoked **remotely via the Hugging Face Inference API**, so the service itself requires no GPU and downloads no model weights.

## Features
- **Document ingestion** — drag-and-drop UI supporting `.docx`, `.txt`, `.pdf`, `.png`, `.jpeg`, `.jpg`.
- **Adaptive, token-aware chunking** — chunk size scales with document length (400 / 600 / 800 tokens, 20% overlap).
- **Serverless embeddings & reranking** — all-MiniLM-L6-v2 for retrieval, bge-reranker-large cross-encoder for relevance ranking, both via HF Inference API.
- **Vector storage & similarity search** — Supabase Postgres + `pgvector` with cosine-distance (`<=>`) retrieval.
- **Unified web app** — chat UI and uploader UI served by the same FastAPI process (Jinja2 templates + static assets).
- **Background ingestion** — heavy embed/store work is dispatched as a background task so uploads return immediately.

## Architecture

```
                  ┌─────────────────────────────────────────────────────┐
                  │                    FastAPI                           │
                  │              (single service, port 5000)             │
                  │                                                     │
Browser ──────────►  GET /chatbot · GET /fileuploader (Jinja2 + STATIC) │
                       │                         │                      │
                       ▼                         ▼                      │
                  POST /File_Upload         POST /send_prompt            │
                       │                         │                      │
                       ▼                         ▼                      │
              validate → metadata →         embed prompt (HF) ──┐       │
              load → chunk → embed (HF)     pgvector search     │       │
                       │                    format context       │       │
                       ▼                    rerank (HF) ────────┤       │
              store_DB (Supabase)           prepare_context      │       │
                       │                         │              │       │
                       └──────────┬──────────────┘              │       │
                                  ▼                             ▼       │
                         Supabase Postgres + pgvector          response  │
                  └─────────────────────────────────────────────────────┘
```

**Ingestion pipeline**
`FileUploader.html → FileUploader.js → POST /File_Upload → validate → extract metadata → load (LangChain) → chunk → embed (HF) → store (Supabase)`

**Chat pipeline**
`RagChatApp.html → RagChatApp.js → POST /send_prompt → embed prompt (HF) → pgvector search → format context → rerank (HF) → response`

## Tech Stack
| Layer | Technology |
|-------|------------|
| Web framework | FastAPI, Uvicorn, Starlette |
| Database driver | `asyncpg` (Supabase Postgres + `pgvector`) |
| Embeddings / Reranking | Hugging Face Inference API (`huggingface_hub`, `requests`) |
| Document loading | LangChain community loaders, `unstructured` |
| Chunking | LangChain `RecursiveCharacterTextSplitter` (tiktoken encoder) |
| Frontend | HTML + Tailwind CSS (CDN) + vanilla JavaScript |
| Config | `configfile.json` + `.env` (python-dotenv) |

## Repository Structure

```
RAG_APP/
├── Documentation/           # Design & remediation notes
│   ├── Architecture_plan_final implimentation.md
│   ├── current.md
│   └── RAG_Remediation_Guide_fixone.md
├── FASTAPI/
│   ├── app_server.py        # FastAPI app, routers, static/template mounting, CORS
│   ├── configfile.json      # Model names, allowed extensions, paths
│   ├── run.py               # Uvicorn entrypoint (host 0.0.0.0:5000, reload=True)
│   ├── routes/
│   │   ├── chatbot.py       # POST /send_prompt — retrieval + rerank
│   │   └── fileupload.py    # POST /File_Upload — ingestion orchestration
│   └── utilities/
│       ├── .env             # Embedding_KEY, reranker_KEY (git-ignored)
│       ├── validateFile.py  # Extension whitelist
│       ├── extractmetada.py # File size / timestamp metadata
│       ├── documentloader.py# LangChain loaders per extension (incl. OCR)
│       ├── chunkdocuments.py# Adaptive token-aware chunking
│       ├── embedddocuments.py# HF feature-extraction embeddings
│       ├── formatfromchroma.py# Context formatting / rechunk helpers
│       ├── results_reranker.py# HF bge-reranker-large reranking
│       ├── postprocessors.py# (legacy) rerank/trim/dedup helpers — unused
│       ├── metadata.py      # Metadata sanitization for JSON storage
│       ├── storeembeddedfiles.py# (legacy) ChromaDB store — dead code
│       ├── rag_textgenerator.py# (legacy) Llama generator — unused
│       ├── text_generator.py# (legacy) Llama generator — unused
│       ├── chat_generator.py# (legacy) Llama + in-memory history — unused
│       └── database/
│           ├── .env         # Supabase connection (git-ignored)
│           ├── supabase_connect.py# asyncpg connection factory
│           ├── store_DB.py  # Insert embedded chunks into pgvector
│           └── retrieve_DB.py# Cosine-distance similarity search
├── STATIC/
│   ├── CSS/                 # FileUploader.css, RagChatApp.css
│   ├── IMAGES/              # UI assets (png)
│   └── JS/
│       ├── FileUploader.js  # Upload queue, delete/assistant widgets
│       └── RagChatApp.js    # Chat UI, retry/backoff, image attach
├── TEMPLATE/
│   ├── FileUploader.html    # Uploader page
│   └── RagChatApp.html      # Chat page
├── requirements.txt         # Pinned dependency manifest
├── .gitignore
├── RELEASE_NOTES.md
└── README.md
```

## Prerequisites
- **Python 3.11+**
- A **Supabase** project with the `pgvector` extension enabled and a `documents` table (see [Configuration](#configuration)).
- A **Hugging Face** API token with Inference API access (`Embedding_KEY`, `reranker_KEY`).
- System libraries for document parsing: **Poppler** (`pdftotext`) for PDFs and **Tesseract** for OCR/image text extraction.

## Installation

```bash
cd RAG_APP
python -m venv ragvenv
source ragvenv/bin/activate        # Windows: ragvenv\Scripts\activate
pip install -r requirements.txt
```

Install system dependencies (Debian/Ubuntu):
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

## Configuration

### Environment variables
Create the two `.env` files (already git-ignored). They are not committed.

**FASTAPI/utilities/.env**
```
Embedding_KEY=hf_xxxxxxxxxxxxxxxx
reranker_KEY=hf_xxxxxxxxxxxxxxxx
```

**FASTAPI/utilities/database/.env**
```
SUPABASE_DB_HOST=aws-0-<region>.pooler.supabase.com
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.<project-ref>
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_POOLMODE=transaction
```

On hosted platforms (e.g. Render) set these as environment variables instead of `.env` files.

### configfile.json (key settings)
```json
{
  "Allowed_Extensions": [".docx", ".txt", ".pdf", ".png", ".jpeg", ".jpg"],
  "Embedding Model": "sentence-transformers/all-MiniLM-L6-v2",
  "cross_encoder_reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
  "modelpath": "F:/BIG (II)/MODEL(II)/mistral/mistral-7b-instruct-v0.1.Q4_K_M.gguf"
}
```

### Database schema
```sql
create extension if not exists vector;
create table if not exists documents (
    id        text primary key,
    text      text,
    embedding vector(384),
    metadata  jsonb
);
-- create index on documents using hnsw (embedding vector_cosine_ops);
```

## Usage

```bash
cd FASTAPI
uvicorn app_server:app --host 0.0.0.0 --port 5000 --reload
# or: python run.py
```

| URL | Purpose |
|-----|---------|
| `http://localhost:5000/chatbot` | Chat interface |
| `http://localhost:5000/fileuploader` | Document upload interface |

## API Reference

### POST /File_Upload
Upload a single document for ingestion.

| Field | Type | Notes |
|-------|------|-------|
| `file` | multipart/form-data | One of the allowed extensions |

**200** → `{ "message": "File '<name>' uploaded successfully." }` (processing continues in background)
**400** → extension not allowed

### POST /send_prompt
Retrieve and rerank context for a prompt.

**Request:** `{ "prompt": "What does the document say about X?" }`

**200 (results)** → `{ "RESULT": "<reranked context text>" }`
**200 (no match)** → `{ "answer": "I couldn't find relevant information...", "sources": [] }`

### GET /chatbot / GET /fileuploader
Serve the chat and uploader UIs.

## Development

```bash
pip install -r requirements.txt
uvicorn app_server:app --reload --port 5000
```

Targets Python 3.11+. Linting/formatting (e.g. `ruff`, `black`) recommended but not yet enforced.

## Testing

Automated tests are not yet included in v0.1.0. Manual smoke test:

1. `POST /File_Upload` with a `.txt` file → success message.
2. Confirm rows appear in the Supabase `documents` table.
3. `POST /send_prompt` with a question → `RESULT` payload.

## Known Limitations

- **LLM generation disabled** — `/send_prompt` returns retrieved+reranked context, not a generated answer.
- **Frontend endpoints hardcoded to LAN IPs**; will not work off the local network.
- **Missing endpoints** — `DELETE /delete/{filename}` and `POST /assistant` referenced by UI but not implemented.
- **OCR/empty chunks** — images with no extracted text still produce placeholder chunks.
- **No connection pooling** — new `asyncpg` connection per request.
- **No auth / rate limiting** — CORS `allow_origins=["*"]`.
- **Blocking rerank call** — synchronous `requests.post` inside an async handler.
- **Dead code** — ChromaDB store and three Llama generators remain unused.
- **No automated tests / CI**.

## Roadmap

- [ ] Enable LLM answer generation (local Mistral/Llama for desktop; hosted LLM for web)
- [ ] Frontend: relative URLs / configurable base URL; implement `/delete` and `/assistant`
- [ ] `asyncpg` connection pool + DB index (HNSW/IVFFlat)
- [ ] Filter empty/OCR chunks before embedding
- [ ] Async reranker (`httpx.AsyncClient`) with retry/backoff + HF rate-limit handling
- [ ] Auth, rate limiting, request validation
- [ ] Automated test suite + CI
- [ ] Remove dead Chroma/Llama code; add `__init__.py` packages
- [ ] Deployment guide (e.g. Render) + health-check endpoint

See `RELEASE_NOTES.md` for version history.

## License

MIT License — see the LICENSE file for details.