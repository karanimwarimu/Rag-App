# Guide 2: Backend Decoupling, Multi-Model Routing (litellm), and API Hardening — Agent Execution Guide

**Target repo:** RAG_APP / FASTAPI
**Dependency:** Assumes Guide 1 Steps 4–5 already executed (Jinja2/static serving removed, routes renamed to `/api/v1/chat` and `/api/v1/upload`, CORS restricted to `FRONTEND_ORIGIN`). If those steps haven't run yet, stop and confirm before proceeding — this guide builds directly on that route layout.
**Scope:** Re-enable LLM answer generation via litellm (cloud-hosted, hot-swappable), remove all hardcoded local paths, and add non-functional auth/job_id scaffolding matching Guide 1's frontend contracts. Does NOT include: real auth logic, real OAuth flows, embedding/reranking pipeline changes (those stay on direct HF Inference API calls, unchanged).

---

## 0. Execution Protocol — READ FIRST

Same sequential-gating protocol as Guide 1:

1. Execute **one step only**, in order. No batching, no skipping ahead.
2. After each step, report:
   - **Step completed:** `<step number + name>`
   - **Files touched:** `<explicit list>`
   - **Deliberately left alone:** `<what you noticed but didn't touch, and why>`
   - **Assumptions made:** `<any judgment call not explicit in this guide>`
   - **Ready for review.**
3. Wait for explicit confirmation before the next step.
4. If a step depends on an undocumented decision, stop and ask.
5. Do not touch the embedding (`embedddocuments.py`) or reranking (`results_reranker.py`) pipelines under this guide — they are explicitly out of scope.

---

## 1. Current State Summary (context, not action)

- `chatbot.py` line 55 currently has LLM generation disabled: `final_response_text = context_str  # await text_Generator(...)`. There is no working generation step at all right now — this guide's main job is turning it on, cloud-routed.
- `configfile.json` has a hardcoded local path: `"modelpath": "F:/BIG (II)/MODEL(II)/mistral/mistral-7b-instruct-v0.1.Q4_K_M.gguf"` — Windows-specific, dead weight, must be removed entirely (not just relocated).
- Dead code exists for local generation: `rag_textgenerator.py`, `text_generator.py`, `chat_generator.py` (all unused Llama-based generators) — candidates for deletion once litellm generation is confirmed working, not before.
- `FASTAPI/utilities/.env` currently holds `Embedding_KEY` and `reranker_KEY` for direct HF Inference API calls to `all-MiniLM-L6-v2` and `bge-reranker-large` — these stay exactly as they are.
- No connection pooling exists (`asyncpg.connect()` per request) and `rerank_chunks` makes a blocking `requests.post` inside an async handler — both noted here but are **not** in scope for this guide; flag them but do not fix them as part of this pass.

---

## 2. Target Directory Layout (additions only)

```
FASTAPI/
├── app_server.py                     # add auth router mount (Step 5)
├── config.yaml                       # NEW — model routing config
├── config.example.yaml               # NEW — committed template
├── routes/
│   ├── chatbot.py                    # modified: call llm_manager instead of stub (Step 3)
│   ├── fileupload.py                 # unchanged
│   └── auth.py                       # NEW — mock/shell auth routes (Step 5)
├── utilities/
│   ├── .env                          # add LLM provider keys (Step 2)
│   ├── .env.example                  # NEW — committed template
│   ├── llm/
│   │   ├── llm_manager.py            # NEW — litellm abstraction layer
│   │   └── config_loader.py          # NEW — parses config.yaml, validates schema
│   ├── schemas/
│   │   └── contracts.py              # NEW — shared Pydantic models (user_id, job_id, session)
│   ├── rag_textgenerator.py          # DELETE in Step 6 (dead code)
│   ├── text_generator.py             # DELETE in Step 6 (dead code)
│   └── chat_generator.py             # DELETE in Step 6 (dead code)
```

---

## 3. Step-by-Step Backend Migration Roadmap

### Step 1 — Install and scaffold litellm
- Add `litellm` to `requirements.txt`, pinned to a current stable version (verify latest stable on PyPI at execution time rather than assuming a version number here).
- Create `FASTAPI/utilities/llm/llm_manager.py` as an empty module with a single documented function signature for now:
  ```python
  async def generate_answer(prompt: str, context: str, model_override: str | None = None) -> str:
      raise NotImplementedError
  ```
- Do not wire this into `chatbot.py` yet — that's Step 3.

### Step 2 — Config layer: `config.yaml` + `.env` split
- Create `FASTAPI/config.example.yaml`:
  ```yaml
  llm:
    provider: google          # google | huggingface
    selected_model: gemini/gemini-1.5-flash
    fallback_model: huggingface/meta-llama/Meta-Llama-3-8B-Instruct
    max_tokens: 1024
    temperature: 0.2
    timeout_seconds: 30
  ```
  Note: verify the exact litellm model-string prefixes for Google AI Studio vs Vertex AI, and for Hugging Face serverless vs dedicated endpoints, against current litellm documentation at execution time — provider prefixes have changed across litellm versions and should not be assumed stable from this guide alone.
- Create `FASTAPI/utilities/config_loader.py` (or place under `utilities/llm/`) that:
  - Loads `config.yaml` (fails loudly with a clear error if missing — do not silently fall back).
  - Loads API keys from `.env` (`GOOGLE_API_KEY`, `HUGGINGFACE_API_KEY`) — keys never live in `config.yaml`, only provider/model selection does.
  - Exposes a single `get_llm_config()` accessor used by `llm_manager.py`.
- Update `FASTAPI/utilities/.env.example` to add:
  ```
  GOOGLE_API_KEY=
  HUGGINGFACE_API_KEY=
  ```
- Remove `"modelpath"` entirely from `configfile.json` — confirm in your report that this key no longer exists anywhere in the file.

### Step 3 — Implement `llm_manager.py` and wire into `/api/v1/chat`
- Implement `generate_answer()` using `litellm.acompletion` (async), reading the selected model from `get_llm_config()`. Build the message payload from the retrieved+reranked context (already produced by the existing pipeline) plus the user's prompt — do not change how context is retrieved, reranked, or formatted.
- Add provider fallback: if the primary provider call fails or times out (using `timeout_seconds` from config), retry once against `fallback_model` before raising.
- In `chatbot.py`, replace the disabled line:
  ```python
  final_response_text = context_str  # await text_Generator(...)
  ```
  with a real call to `generate_answer(prompt=user_prompt, context=context_str)`. Preserve the existing response shape contract (`{"RESULT": ...}` / no-match shape) unless Step 4 changes it.
- Do not implement streaming in this step — first get non-streaming generation working end-to-end and confirmed, streaming is Step 4.

### Step 4 — Streaming support (SSE)
- Extend `/api/v1/chat` to support server-sent events via `litellm.acompletion(..., stream=True)`, using FastAPI's `StreamingResponse`.
- This should be additive: keep a non-streaming code path available (e.g. via a query param or request field `stream: bool`) so the frontend's fallback logic from Guide 1 Step 2 has something to fall back to.
- Confirm this works against the frontend's streaming-ready fetch client from Guide 1 before considering this step done — if Guide 1 hasn't been executed yet, test with a raw `curl -N` request instead and note that in your report.

### Step 5 — Auth/job_id scaffolding (mock only, no logic)
- Create `FASTAPI/utilities/schemas/contracts.py` with shared Pydantic models:
  ```python
  class SessionContext(BaseModel):
      user_id: str | None = None
      is_authenticated: bool = False

  class JobStatus(BaseModel):
      job_id: str
      status: Literal["pending", "processing", "complete", "failed"]
      user_id: str | None = None
  ```
- Create `FASTAPI/routes/auth.py` with shell routes — no real logic, no password hashing, no token issuance, no DB writes:
  - `POST /api/v1/auth/login` → returns `501 Not Implemented` with a clear JSON message.
  - `POST /api/v1/auth/signup` → same.
  - `POST /api/v1/auth/forgot-password` → same.
  - `GET /api/v1/auth/callback/google` → same.
  - `GET /api/v1/auth/callback/github` → same.
  - Each route's request/response Pydantic models should still be fully defined (matching real-world shapes) even though the logic is a stub — this is what makes them "structural contracts," not just dead endpoints.
- Add `user_id: str | None` and `job_id: str | None` as optional fields (headers or body, your call — state which in your report) on `/api/v1/upload` and `/api/v1/chat` request contracts, unused by current logic but present so the frontend can start sending them without breaking anything.
- Mount `auth.py`'s router in `app_server.py`.

### Step 6 — Remove hardcoded paths and dead code
- Audit `documentloader.py` for any hardcoded temp-file paths; replace with `tempfile` module usage (OS-agnostic, no assumptions about `/tmp` existing on Windows).
- Add a `STORAGE_DIR` env var (default via `tempfile.gettempdir()` if unset) for any file-system scratch space the ingestion pipeline uses.
- Delete `rag_textgenerator.py`, `text_generator.py`, `chat_generator.py` — confirm generation works via litellm first (Step 3/4) before deleting these.
- Confirm no remaining references to the deleted files anywhere in the codebase (grep before deleting).

### Step 7 — Documentation update
- Update `README.md`: remove the "LLM generation disabled" line from Known Limitations, document the new `config.yaml` model-switching workflow, document the new `/api/v1/auth/*` stub routes and their `501` behavior, and add `config.yaml`/`.env` setup to the Configuration section.

---

## 4. `config.yaml` / `.env.example` Reference

**`config.yaml`** — model routing only, no secrets:
```yaml
llm:
  provider: google
  selected_model: gemini/gemini-1.5-flash
  fallback_model: huggingface/meta-llama/Meta-Llama-3-8B-Instruct
  max_tokens: 1024
  temperature: 0.2
  timeout_seconds: 30
```

**`.env.example`** (`FASTAPI/utilities/.env.example`) — secrets only:
```
Embedding_KEY=
reranker_KEY=
GOOGLE_API_KEY=
HUGGINGFACE_API_KEY=
```

**`FASTAPI/utilities/database/.env.example`** — unchanged from current setup:
```
SUPABASE_DB_HOST=
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=
SUPABASE_DB_PASSWORD=
SUPABASE_DB_POOLMODE=transaction
```

To switch models: change `selected_model` (and `provider` if crossing vendors) in `config.yaml` and restart the service. No source code changes required — `llm_manager.py` reads this value at call time via `get_llm_config()`.

---

## 5. API Endpoint & Validation Contracts

| Endpoint | Method | Request shape | Response shape | Status |
|---|---|---|---|---|
| `/api/v1/chat` | POST | `{prompt: str, stream?: bool, user_id?: str, job_id?: str}` | `{RESULT: str}` (non-stream) or SSE token stream | **Live after Step 3/4** |
| `/api/v1/upload` | POST | multipart `file`, optional `user_id`, `job_id` | `{message: str, job_id?: str}` | Live (renamed in Guide 1) |
| `/api/v1/auth/login` | POST | `{email: str, password: str}` | `501` stub | **Mock only** |
| `/api/v1/auth/signup` | POST | `{email: str, password: str}` | `501` stub | **Mock only** |
| `/api/v1/auth/forgot-password` | POST | `{email: str}` | `501` stub | **Mock only** |
| `/api/v1/auth/callback/google` | GET | query params (OAuth standard) | `501` stub | **Mock only** |
| `/api/v1/auth/callback/github` | GET | query params (OAuth standard) | `501` stub | **Mock only** |

---

## 6. Explicit Non-Goals (do not implement under this guide)

- Real password hashing, token issuance, session persistence, or DB-backed user records.
- Real OAuth provider integration (Google/GitHub).
- Changes to embedding or reranking logic/providers.
- Connection pooling fix or the blocking-rerank-call fix (tracked separately).
- Docker/deployment changes (separate guide).
