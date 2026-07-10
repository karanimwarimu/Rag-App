# Release Notes

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adhering to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- LLM answer generation is scaffolded but not enabled.
- Frontend calls are hardcoded to LAN IPs and will not work when deployed.
- `DELETE /delete/{filename}` and `POST /assistant` endpoints referenced by the UI are not implemented.
- No connection pooling, authentication, rate limiting, or automated tests.
- Dead Chroma/Llama code remains in the tree.

### Notes
- Both encoder models run remotely on the Hugging Face Inference API; the service needs no GPU and downloads no model weights.
- `asyncpg` and `tiktoken` must be present in the environment (add to requirements before deploying).

[0.1.0]: #0.1.0