# Guide 3: Comprehensive Test Suite — Components, Integrations & Webhook Contracts — Agent Execution Guide

**Target repo:** RAG_APP (frontend + FASTAPI)
**Dependency:** Assumes Guide 1 (UI decoupling) and Guide 2 (litellm + auth scaffolding) are fully executed. This guide tests the **post-migration architecture** — `/api/v1/*` routes, the React frontend, litellm generation, and the auth/job_id stub contracts. If either guide is only partially done, stop and confirm scope with the person before proceeding, since several tests below will fail against an incomplete migration by design, not by bug.
**Scope:** Unit tests, integration tests, contract tests for every endpoint (including the auth/OAuth stubs and the not-yet-real webhook surface), frontend component tests, and end-to-end tests across the decoupled frontend/backend boundary. Does NOT include: load/performance testing, penetration testing, or CI pipeline setup (flagged as a natural next step, not built here).

---

## 0. Execution Protocol — READ FIRST

Same sequential-gating protocol as Guides 1 and 2:

1. Execute **one step only**, in order. No batching, no skipping ahead.
2. After each step, report:
   - **Step completed:** `<step number + name>`
   - **Files touched:** `<explicit list>`
   - **Tests written / passing / failing:** `<counts, and which failed and why>`
   - **Deliberately left alone:** `<what you noticed but didn't test, and why>`
   - **Assumptions made:** `<any judgment call not explicit in this guide>`
   - **Ready for review.**
3. Wait for explicit confirmation before the next step.
4. A failing test is not a reason to modify application code under this guide — this is a testing pass, not a bugfix pass. If a test reveals a real defect, report it clearly under "Ready for review" and stop; do not silently patch source to make the test pass.
5. Never mark a step complete with skipped or `xfail`-marked tests unless explicitly noted here as expected (see Section 6, webhook stubs).

---

## 1. Current State Summary (context, not action)

- Backend has no automated tests at all today. This guide builds the suite from zero.
- Frontend (post Guide 1) is a React + Vite app with no test tooling installed yet.
- Real external dependencies in the request path: Supabase Postgres/pgvector, Hugging Face Inference API (embeddings + reranking), and litellm-routed generation (Google AI Studio / Hugging Face). All must be mockable — tests should never hit live paid APIs or the production database by default.
- No webhooks are actually implemented anywhere in the live code. The only webhook reference is a planned future Stripe endpoint in `Documentation/Architecture_plan_final implimentation.md` — not built. The closest things to "webhook-shaped" endpoints that exist post-Guide-2 are the OAuth callback stubs (`/auth/callback/google`, `/auth/callback/github`), which are inbound receiver endpoints in the same architectural family. This guide treats those as the webhook surface to test now, and defines a contract-only test template for the future Stripe webhook (Section 6).

---

## 2. Test Tooling & Directory Layout

**Backend:** `pytest`, `pytest-asyncio`, `httpx` (`AsyncClient` against the FastAPI app via ASGI transport — no real network hop), `pytest-mock` or `unittest.mock` for HF/litellm/DB mocking, `respx` (or `responses`) for mocking outbound HTTP calls to Hugging Face.

**Frontend:** `vitest` + `@testing-library/react` for component tests, `msw` (Mock Service Worker) for mocking `/api/v1/*` calls in isolation from the real backend.

**End-to-end:** `Playwright`, run against real dev servers (frontend `:5173`, backend `:5000`) with a dedicated test Supabase schema and mocked/sandboxed external APIs — not production credentials.

```
RAG_APP/
├── FASTAPI/
│   └── tests/
│       ├── conftest.py                    # shared fixtures: test app, mock DB, mock HF, mock litellm
│       ├── unit/
│       │   ├── test_chunking.py
│       │   ├── test_embedding.py
│       │   ├── test_reranking.py
│       │   ├── test_llm_manager.py
│       │   └── test_config_loader.py
│       ├── integration/
│       │   ├── test_ingestion_pipeline.py
│       │   ├── test_chat_pipeline.py
│       │   └── test_db_layer.py
│       └── contract/
│           ├── test_upload_endpoint.py
│           ├── test_chat_endpoint.py
│           ├── test_chat_streaming.py
│           ├── test_auth_stub_endpoints.py
│           └── test_cors.py
├── frontend/
│   └── src/
│       └── __tests__/
│           ├── components/
│           │   ├── ChatWorkspace.test.jsx
│           │   ├── UploadWorkspace.test.jsx
│           │   ├── LoginForm.test.jsx
│           │   ├── SignUpForm.test.jsx
│           │   ├── ForgotPasswordForm.test.jsx
│           │   ├── OAuthButtons.test.jsx
│           │   ├── GlobalAssistantWidget.test.jsx
│           │   └── LinkUploaderStub.test.jsx
│           ├── context/
│           │   └── SessionContext.test.jsx
│           └── api/
│               ├── chat.test.js
│               └── upload.test.js
└── e2e/
    ├── playwright.config.ts
    ├── fixtures/
    │   └── test-files/                    # sample .txt/.pdf/.docx for upload tests
    └── specs/
        ├── ingestion-flow.spec.ts
        ├── chat-flow.spec.ts
        ├── landing-and-nav.spec.ts
        └── auth-stub-flow.spec.ts
```

---

## 3. Step-by-Step Test Implementation Roadmap

### Step 1 — Backend test scaffolding and fixtures
- Add `pytest`, `pytest-asyncio`, `httpx`, `pytest-mock`, `respx` to `requirements.txt` (dev-only group if the project distinguishes one).
- Build `FASTAPI/tests/conftest.py` with:
  - An `AsyncClient` fixture wired to the FastAPI app via `httpx.ASGITransport` (no live server needed).
  - A mock DB fixture that either points at a dedicated test schema/table in Supabase or fully mocks `asyncpg` calls — state which you chose and why in your report; a real test schema is preferable if credentials are available, since it also exercises the pgvector query itself.
  - A mock HF fixture using `respx` to intercept calls to the embedding and reranking endpoints with deterministic fake vectors/scores.
  - A mock litellm fixture that patches `litellm.acompletion` to return a deterministic canned response, so tests never call a real paid model.
- Do not write any actual test cases in this step — fixtures only.

### Step 2 — Unit tests: chunking, embedding, reranking, config
- `test_chunking.py`: verify adaptive chunk sizing (400/600/800 token thresholds) against short/medium/long fixture documents, verify 20% overlap, verify `chunk_uuid`/`chunk_id`/`source` metadata is stamped correctly.
- `test_embedding.py`: verify the embedding function calls the HF client with correct parameters (via the mock fixture) and that output vectors are L2-normalized.
- `test_reranking.py`: verify `rerank_chunks` correctly selects top-`k`=2 by score against a mocked HF reranker response, and correctly handles an empty/no-match input.
- `test_llm_manager.py`: verify `generate_answer()` selects the model from `config.yaml` correctly, verify the fallback path triggers when the primary provider mock raises a timeout/error, verify it does not silently swallow a failure if both primary and fallback fail (should raise, not return empty string).
- `test_config_loader.py`: verify `get_llm_config()` fails loudly (raises, doesn't default silently) when `config.yaml` is missing or malformed; verify it correctly reads `GOOGLE_API_KEY`/`HUGGINGFACE_API_KEY` from environment rather than from the yaml file.

### Step 3 — Integration tests: full pipeline flows
- `test_ingestion_pipeline.py`: upload a fixture `.txt`/`.pdf`/`.docx` end-to-end through validate → metadata → load → chunk → embed (mocked) → store (test DB or mocked), asserting the final row(s) landed with correct `id`, `text`, `embedding` dimensionality (384), and `metadata` shape.
- `test_chat_pipeline.py`: seed a known chunk into the test DB, send a `/api/v1/chat` request whose prompt should retrieve it, assert the retrieved chunk was passed into the (mocked) litellm call as part of the context, and assert the final response shape matches contract.
- `test_db_layer.py`: test `query_supabase()` directly against a real test schema (if available) verifying cosine-distance ordering behaves as expected with a small known vector set; if a live test DB isn't available, mark this test `skip` with a clear reason rather than mocking away the one thing this test exists to verify.

### Step 4 — Contract tests: every endpoint
- `test_upload_endpoint.py`: valid extension → 200 + expected message shape; disallowed extension → 400; missing file field → 422; optional `user_id`/`job_id` fields accepted and echoed/ignored per current (non-enforced) contract.
- `test_chat_endpoint.py`: valid prompt → 200 with `RESULT` shape (non-stream); no-match case → the documented `{"answer": ..., "sources": []}` shape; missing `prompt` field → 422.
- `test_chat_streaming.py`: `stream: true` request returns `text/event-stream` content-type and yields at least one chunk before completion; confirm the non-streaming fallback path still works when `stream` is omitted or `false`.
- `test_auth_stub_endpoints.py`: every stub route (`/api/v1/auth/login`, `/signup`, `/forgot-password`, `/callback/google`, `/callback/github`) returns `501` with a clear JSON body — not a 404, not a 500, not a silent 200. This is the primary regression guard against someone accidentally wiring in partial auth logic without finishing it.
- `test_cors.py`: request from `FRONTEND_ORIGIN` succeeds; request from an arbitrary other origin is rejected by CORS headers; confirm `allow_origins=["*"]` is gone for good (this test should fail loudly if that regresses).

### Step 5 — Frontend component tests
- Install `vitest`, `@testing-library/react`, `msw` in `frontend/`.
- For each component listed in the directory layout above, test: renders without crashing, key interactive elements are present (form fields, buttons), form submission calls the expected stubbed API function (assert via mock, not a real network call), and error/loading states render correctly where applicable.
- `SessionContext.test.jsx`: verify default state respects the `VITE_SKIP_AUTH` flag behavior defined in Guide 1 Step 8, verify `login()`/`logout()` state transitions work even though they're stubs.
- `chat.test.js` / `upload.test.js` (the `api/` layer): using `msw`, verify these modules call the correct URL built from `VITE_API_BASE_URL`, handle a mocked streaming response correctly, and handle a mocked error response without throwing an unhandled rejection.

### Step 6 — Webhook / callback contract tests (see Section 6 for full detail)
- Confirm `test_auth_stub_endpoints.py` (Step 4) already covers the two real inbound receiver endpoints that exist today (`/auth/callback/google`, `/auth/callback/github`).
- Add a **contract-only, intentionally skipped** test file `test_stripe_webhook_contract.py` documenting the expected future payload shape and signature-verification behavior from the architecture doc, marked `@pytest.mark.skip(reason="not implemented — contract placeholder, see Architecture_plan_final implimentation.md §7.2")`. This exists so the shape is version-controlled and reviewable now, without pretending a real webhook exists.

### Step 7 — End-to-end tests (Playwright)
- `ingestion-flow.spec.ts`: launch both dev servers (or point at a docker-compose stack if Section 7 of the Docker guide is done by this point), upload a real fixture file through the actual UI, and assert the success state renders — this is the one place actually hitting a real (test-scoped) Supabase instance and real HF calls end-to-end; use a dedicated test API budget/key if available, and note in your report if you had to skip this due to lacking test credentials.
- `chat-flow.spec.ts`: type a question into the real Chat UI, assert a response renders (streaming or not), assert no console errors.
- `landing-and-nav.spec.ts`: navigate from `/` through login/signup forms (asserting they render and are submittable, not asserting real auth success), through to `/app/chat` and `/app/upload`, confirming routing and the global assistant widget render on every page.
- `auth-stub-flow.spec.ts`: click through OAuth buttons and confirm the graceful "coming soon"/stub UI state renders rather than a broken network error.

### Step 8 — Documentation update
- Update `README.md`'s Testing section to replace "Automated tests are not yet included" with instructions for running each suite (`pytest`, `npm run test`, `npx playwright test`), and note what requires live credentials vs. what's fully mocked.

---

## 4. Coverage Matrix

| Layer | Component | Test type | What it verifies |
|---|---|---|---|
| Backend | Chunking | Unit | Adaptive sizing, overlap, metadata stamping |
| Backend | Embedding | Unit (mocked HF) | Correct call params, L2 normalization |
| Backend | Reranking | Unit (mocked HF) | Top-k selection, empty-input handling |
| Backend | `llm_manager.py` | Unit (mocked litellm) | Model selection from config, fallback logic |
| Backend | `config_loader.py` | Unit | Fails loudly on missing/malformed config |
| Backend | Ingestion pipeline | Integration | End-to-end upload → store, correct row shape |
| Backend | Chat pipeline | Integration | Retrieval → context → generation, correct response shape |
| Backend | pgvector query | Integration (real test DB) | Cosine-distance ordering correctness |
| Backend | `/api/v1/upload` | Contract | Status codes, validation, optional fields |
| Backend | `/api/v1/chat` | Contract | Response shapes, no-match case |
| Backend | `/api/v1/chat` streaming | Contract | SSE content-type, chunked delivery, fallback |
| Backend | `/api/v1/auth/*` stubs | Contract | Consistent `501`, never silent success |
| Backend | CORS | Contract | Only `FRONTEND_ORIGIN` allowed |
| Frontend | Auth forms | Component | Render, field presence, stub call on submit |
| Frontend | Chat/Upload workspaces | Component | Render, interaction, mocked API calls |
| Frontend | `SessionContext` | Component | Default state, login/logout stub transitions |
| Frontend | `api/chat.js`, `api/upload.js` | Component (msw) | Correct URL construction, error handling |
| Cross-boundary | Full ingestion | E2E | Real UI → real backend → real DB (test-scoped) |
| Cross-boundary | Full chat | E2E | Real UI → real backend → real generation |
| Cross-boundary | Navigation/landing | E2E | Routing, auth form rendering, assistant widget placement |
| Cross-boundary | OAuth stub UX | E2E | Graceful degradation, no broken states |

---

## 5. Environment & Credentials Needed for Thorough Execution

- A **dedicated test Supabase project or schema** (not production) with `pgvector` enabled — required for Section 3/7's real-DB tests. If unavailable, those specific tests should be explicitly `skip`ped with a reason, not deleted or faked.
- **HF Inference API test key** — a real key with a small quota is enough; nearly all tests mock this, but the E2E ingestion/chat specs in Step 7 hit it for real.
- **A real (small-budget) Google AI Studio or HF-hosted model key** for the same reason — Step 7's `chat-flow.spec.ts` is the only place a real generation call happens.
- None of the above are needed for Steps 1–6, which are fully mocked by design — flag clearly in your report if Step 7 had to be partially skipped due to missing credentials, rather than silently faking those specs as passing.

---

## 6. Webhook Contract Note (see Step 6)

There is no live webhook in this codebase today. The two OAuth callback stub endpoints are the nearest architectural equivalent and are fully covered as contract tests in Step 4. The future Stripe webhook is documented only — Step 6 adds a version-controlled, explicitly-skipped test describing its expected shape (signature header verification, event-type payload structure) so that when it's actually built, the test already exists and just needs its `skip` marker removed.

---

## 7. Explicit Non-Goals (do not implement under this guide)

- Load testing, stress testing, or performance benchmarking.
- Security penetration testing or fuzzing.
- CI/CD pipeline wiring (GitHub Actions, etc.) — natural next step, separate guide.
- Implementing the real Stripe webhook or real OAuth logic — this guide only tests the stub/contract layer.
- Fixing any bug a test uncovers — report it, don't patch it, under this guide.
