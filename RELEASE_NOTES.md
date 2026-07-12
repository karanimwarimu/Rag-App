# Release Notes

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adhering to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-12

### Added
- **Full frontend/backend decoupling.** Standalone React + Vite SPA (`frontend/`) replaces the Jinja2 templates; the backend is now a pure JSON API.
- **Two-service architecture.** UI served by Vite/Netlify; API served by FastAPI. No HTML/static serving in the backend.
- **Chat UI rebuilt as a ChatGPT-style dark interface** (message bubbles, streaming indicator, centered composer). The floating assistant (J.A.R.V.I.S.) widget was removed.
- **LLM answer generation enabled via litellm** (cloud-routed, hot-swappable). Default model: `Qwen/Qwen2.5-7B-Instruct` on Hugging Face serverless.
- **Server-Sent Events (SSE) streaming** for `/api/v1/chat` (each frame `data: {"token": "..."}`, ends with `data: [DONE]`).
- **`config.yaml` model-routing layer** (`utilities/llm/config_loader.py`) — provider/model selection + fallback. Swap models by editing `config.yaml` + restart; no code change.
- **Versioned API routes.** `/send_prompt` → `POST /api/v1/chat`, `/File_Upload` → `POST /api/v1/upload`.
- **CORS restricted** to `FRONTEND_ORIGIN` (comma-separated allow-list) instead of `*`.
- **Auth/job scaffolding.** `POST /api/v1/auth/*` structural stubs (return `501`) and `user_id`/`job_id` request fields on chat/upload.
- **Landing page, auth shell** (Login/SignUp/ForgotPassword/OAuth) and a routing matrix with `VITE_SKIP_AUTH` soft-gating.
- **Web Link Uploader stub page** (behind `VITE_ENABLE_LINK_UPLOADER`).
- **Deployment assets:** `FASTAPI/Dockerfile`, `FASTAPI/.dockerignore`, `frontend/netlify.toml`, and README Deployment section (Render + Netlify).

### Changed
- Removed Jinja2 template serving and the `/static` mount; deleted `TEMPLATE/` and `STATIC/`; moved UI images to `frontend/public/IMAGES/`.
- Removed dead local-model config (`modelpath`, `n_ctx`, `n_threads`, `n_gpu_layers`, `model_configuration`) from `configfile.json`.
- `documentloader.py` uses `tempfile` + optional `STORAGE_DIR` (OS-agnostic, no hardcoded paths).
- Fixed `config_loader.py` path resolution (was resolving `config.yaml` one directory too deep, in `utilities/` instead of `FASTAPI/`).
- `requirements.txt` pinned with `litellm==1.92.0` and `PyYAML==6.0.2`.
- Reworked `README.md` to reflect the decoupled architecture, updated repository structure, and deployment guide.

### Removed
- Dead Llama generators: `utilities/rag_textgenerator.py`, `text_generator.py`, `chat_generator.py`.

### Known Issues / Not Yet Implemented
- Auth endpoints are `501` stubs (no real login, tokens, or sessions).
- Virtual assistant backend (`/api/v1/assistant`) not implemented; the UI widget was removed.
- Web Link Uploader is a UI-only stub.
- Blocking rerank call and no connection pooling remain.
- No automated tests / CI.

### Notes
- `config.yaml` is committed (model names only, no secrets). API keys live in `utilities/.env` (git-ignored) or are injected as environment variables by the host (Render).
- Hugging Face embeddings/reranking and litellm LLM calls run remotely; the service needs no GPU and downloads no model weights.

---

## [0.1.0] - 2026-07-10

### Added
- FastAPI service with chat (`/send_prompt`) and ingestion (`/File_Upload`) endpoints.
- Web UIs served by the app: chat (`/chatbot`) and uploader (`/fileuploader`).
- Adaptive, token-aware document chunking (400/600/800 sizes, 20% overlap).
- Serverless embeddings via Hugging Face Inference API (all-MiniLM-L6-v2).
- Vector storage and cosine similarity search with Supabase + pgvector.
- Cross-encoder reranking via Hugging Face Inference API (bge-reranker-large).
- Background ingestion dispatch so uploads return immediately.
- README, repository structure docs, and this release-notes file.

### Changed
- Anchored `.env` loading to the module directory so embedding/reranker keys load regardless of working directory.
- Anchored `configfile.json` reads to `__file__` to remove CWD dependence.
- Chat response now returns clean reranked chunk text instead of Python dict reprs.
- `requirements.txt` deduplicated and cleaned — removed 200+ duplicate entries from multiple `pip freeze` layers.

### Fixed
- Removed dead ChromaDB import from the chat route (eliminated a startup-time `chromadb` dependency and a wrong-project side effect).
- Removed unused `sentence_transformers` and `scikit-learn` imports that blocked app startup.
- Removed stray `np.TXT` scratch file.
- Fixed `TextLoader` encoding for `.txt` files — added `encoding="utf-8"` to prevent `UnicodeDecodeError` on Windows.
- Added graceful fallback for `.docx` loading when `docx2txt` is not installed.
- Fixed Jinja2 template cache crash (`TypeError: unhashable type: 'dict'`) by using explicit `FileSystemLoader` with `cache_size=0`.
- Fixed `FileUploader.js` fetch URL — added missing `http://` prefix to prevent 404.

### Known Issues / Not Yet Implemented
- LLM answer generation was scaffolded but not enabled (now enabled in 0.2.0).
- Frontend calls were hardcoded to LAN IPs and would not work when deployed (now config-driven in 0.2.0).
- No connection pooling, authentication, rate limiting, or automated tests.
- Dead Chroma/Llama code remained in the tree (removed in 0.2.0).

### Notes
- Both encoder models run remotely on the Hugging Face Inference API; the service needs no GPU and downloads no model weights.
- `asyncpg` and `tiktoken` must be present in the environment (added to requirements before deploying).

[0.2.0]: #020
[0.1.0]: #010
