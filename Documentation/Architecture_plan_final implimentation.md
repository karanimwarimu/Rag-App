# NEXORA RAG PLATFORM — ENTERPRISE ARCHITECTURE PLAN
## Principal Architect Research & Design Document
### Classification: CONFIDENTIAL — Internal Planning

---

## TABLE OF CONTENTS
1. Executive Summary & Strategic Goals
2. Deployment Mode Architecture (Local / Cloud / Embedded)
3. Core System Architecture — Abstract Layer Design
4. Data Ingestion & Visual RAG Pipeline (UI-1)
5. Chat Orchestration & Search Engine (UI-2)
6. Multi-Tenant Database Schema & RLS Policies
7. Token Metering & Billing Architecture
8. Async Job Processing Pipeline
9. C#/.NET POS Integration Strategy
10. Security & Compliance Framework
11. Performance & Scaling Strategy
12. Technology Stack Decisions with Rationale
13. Project Folder Structure
14. Implementation Roadmap (Phased)
15. Risk Assessment & Mitigation

---

## 1. EXECUTIVE SUMMARY & STRATEGIC GOALS

### Vision
Build a production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform that serves three distinct deployment contexts from a single, unified codebase. The platform must handle document ingestion with visual asset linking, real-time streaming chat with web-intelligence augmentation, and strict tenant isolation with token-based billing.

### Strategic Goals
- **Cross-Deployment Flexibility**: Single codebase, three deployment modes via environment toggle
- **Visual RAG**: Every text chunk must carry image metadata; retrieved images displayed inline with LLM responses
- **Real-Time Web Intelligence**: Nexora crawler integration for live knowledge augmentation
- **Enterprise Multi-Tenancy**: Strict data isolation via Supabase RLS, JWT-based auth, role-based access
- **Token Economics**: Real-time balance deduction, usage metering, Stripe webhook integration
- **Desktop POS Integration**: Headless API optimized for C#/.NET HTTP client consumption

---

## 2. DEPLOYMENT MODE ARCHITECTURE

### 2.1 Mode A: Local / Offline
- **Database**: PostgreSQL + pgvector via Docker Compose (replaces Supabase entirely)
- **LLM**: Ollama running locally (Llama 3 / Mistral)
- **Embeddings**: sentence-transformers via Hugging Face
- **Auth**: Local JWT with symmetric key (HS256)
- **Storage**: Local filesystem with path-based references
- **Queue**: FastAPI BackgroundTasks (sufficient for single-tenant local use)
- **Goal**: Fully air-gapped capable, zero external dependencies

### 2.2 Mode B: Cloud / Deployed
- **Database**: Supabase Auth + PostgreSQL + pgvector (managed)
- **LLM**: Gemini API / HuggingFace Inference Endpoints
- **Embeddings**: Gemini / OpenAI embedding APIs
- **Auth**: Supabase Auth with RS256 JWT, RLS enforced
- **Storage**: Supabase Storage buckets
- **Queue**: Celery + Redis (production-grade, proven at Instagram/Mozilla scale)
- **Billing**: Stripe webhooks for token top-ups
- **Goal**: Fully scalable, thousands of concurrent tenants

### 2.3 Mode C: Headless API / Embedded (POS)
- **Database**: ChromaDB embedded (no separate process)
- **LLM**: Ollama bundled or called via subprocess
- **Embeddings**: sentence-transformers (local)
- **Auth**: None — POS application is the trusted client
- **Storage**: Local filesystem
- **Queue**: asyncio (no separate process, minimal footprint)
- **Goal**: Lightweight background service, optimized for C# HttpClient

---

## 3. CORE SYSTEM ARCHITECTURE — ABSTRACT LAYER DESIGN

### 3.1 The Abstraction Principle
Every service implements an abstract interface. Concrete implementation selected at runtime via `DEPLOYMENT_MODE`. This enables testability (mock implementations), flexibility (swap cloud for local without touching business logic), and maintainability (single source of truth per capability).

### 3.2 Service Abstraction Matrix

| Capability | Local Mode | Cloud Mode | Embedded Mode | Interface |
|-----------|-----------|-----------|--------------|-----------|
| **Auth** | Local JWT (HS256) | Supabase Auth (RS256) | None (bypass) | `AuthProvider` |
| **Vector Store** | pgvector (Docker) | Supabase pgvector | ChromaDB (embedded) | `VectorStore` |
| **Database** | PostgreSQL (Docker) | Supabase PostgreSQL | SQLite/Chroma | `Database` |
| **LLM** | Ollama (local) | Gemini API / HF | Ollama (bundled) | `LLMProvider` |
| **Embeddings** | sentence-transformers | Gemini / OpenAI | sentence-transformers | `EmbeddingProvider` |
| **File Storage** | Local filesystem | Supabase Storage | Local filesystem | `FileStorage` |
| **Queue** | BackgroundTasks | Celery + Redis | asyncio | `TaskQueue` |
| **Web Search** | Disabled | Nexora crawler | Disabled | `WebSearchProvider` |

### 3.3 Dependency Injection Strategy
All services injected via FastAPI `Depends()` with request-scoped resolution. Runtime selection based on `DEPLOYMENT_MODE` env var. Full type safety and testability via dependency overrides in tests.

---

## 4. DATA INGESTION & VISUAL RAG PIPELINE (UI-1)

### 4.1 Document Ingestion Flow
1. **Upload**: Admin UI drag/drop -> FastAPI `/upload` -> Immediate response `{ job_id, status }`
2. **Queue**: Celery/BackgroundTask picks up `process_document_job(job_id)`
3. **Parse**: PyMuPDF + Unstructured + Docling for PDF/TXT/DOCX extraction
4. **Extract Images**: LayoutParser extracts inline images, diagrams, charts
5. **Chunk**: Semantic chunking (512-1024 tokens, 128-token overlap)
6. **Embed**: Generate embeddings per chunk (local: sentence-transformers, cloud: Gemini)
7. **Store**: Upsert to vector DB with rich metadata payload

### 4.2 Visual RAG — Dual-VLM Pattern (Industry Best Practice)

**Stage 1 — Ingestion Summarizer** (Fast, lightweight VLM):
- Processes every extracted image during document parsing
- Generates structured summary: title, visual type, contextual summary, text transcription
- Summary becomes the `content` field of the image chunk for vector indexing
- Original image stored in file storage with stable URL reference

**Stage 2 — Retrieval VLM** (Powerful, accurate VLM):
- At query time, when an image chunk is retrieved, system fetches original image
- Sends image + user question to VLM for detailed analysis
- VLM output injected into unified context alongside text chunks
- Text LLM synthesizes final answer from all evidence types

**Critical Design Decision — Unified Context:**
The retrieval VLM output does NOT go directly to the user. It gets injected into a unified context string with text chunks and table chunks. A single text LLM reads the combined context and produces the final answer. This cross-referencing catches VLM hallucinations and fills gaps.

### 4.3 Image Metadata Schema (per chunk)
```json
{
  "image_urls": ["https://cdn.../page12_fig1.png", "https://cdn.../page12_fig2.png"],
  "image_captions": ["Q3 revenue pie chart", "YoY growth comparison"],
  "image_types": ["chart", "diagram"],
  "image_page_numbers": [12, 12],
  "vlm_summary": "Ingestion-time summary for retrieval indexing",
  "vlm_summary_embedding": [0.1, 0.2, ...],
  "image_storage_path": "tenants/{tenant_id}/docs/{doc_id}/images/{img_id}.png"
}
```

---

## 5. CHAT ORCHESTRATION & SEARCH ENGINE (UI-2)

### 5.1 RAG Query Flow
1. **User Query** -> FastAPI endpoint
2. **Intent Classification**: Lightweight LLM call classifies as `RAG_ONLY` / `WEB_REQUIRED` / `HYBRID`
3. **Vector Search** (always runs):
   - Embed query -> pgvector ANN search with `tenant_id` pre-filter
   - Cross-encoder reranker: top 20 -> top 5
4. **Web Search** (conditional — `HYBRID` or `WEB_REQUIRED`):
   - Nexora query engine -> Firecrawl deep scrape -> chunk -> embed on-the-fly
   - Web chunks tagged: `{ source: "web", url: "...", fetched_at }`
5. **Context Assembly**: Merge + deduplicate + sort by relevance + respect token budget + include VLM image analysis
6. **LLM Generation** (Streaming):
   - Pre-flight token estimate (quota check via `FOR UPDATE` row lock)
   - Stream tokens via SSE
   - Post-hoc exact token count for billing
7. **Response Enrichment**: Parse image references -> inject image cards into UI stream

### 5.2 Streaming Architecture
- **SSE** (text/event-stream) for token-by-token delivery
- Event types: `token`, `image`, `citation`, `done`, `error`
- Final event carries full usage metadata: `{ "type": "done", "usage": { "input_tokens": 1234, "output_tokens": 567 } }`
- **WebSocket** alternative for bidirectional communication (user interrupt)

---

## 6. MULTI-TENANT DATABASE SCHEMA & RLS POLICIES

### 6.1 Schema Design Philosophy
- Every domain table: non-null `tenant_id` FK to `tenants(id)`
- Every domain table: non-null `user_id` FK to `auth.users(id)` (cloud mode)
- RLS **ENABLED** on every table — deny by default
- No soft tenancy — every row belongs to exactly one tenant

### 6.2 Complete Database Schema

```sql
-- CORE TENANCY
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free','starter','pro','enterprise')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','cancelled')),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('super_admin','admin','member','viewer')),
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, user_id)
);

-- TOKEN METERING & BILLING
CREATE TABLE public.token_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    balance_tokens BIGINT NOT NULL DEFAULT 0,
    reserved_tokens BIGINT NOT NULL DEFAULT 0,
    total_spent_tokens BIGINT NOT NULL DEFAULT 0,
    total_spent_cents INTEGER NOT NULL DEFAULT 0,
    last_topup_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, user_id)
);

CREATE TABLE public.token_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('debit','credit','refund','adjustment')),
    amount_tokens BIGINT NOT NULL,
    amount_cents INTEGER,
    balance_after BIGINT NOT NULL,
    session_id UUID,
    request_id TEXT,
    model_id TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    metadata JSONB DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.token_pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL UNIQUE,
    model_name TEXT NOT NULL,
    input_token_price_per_1m NUMERIC(10,6) NOT NULL,
    output_token_price_per_1m NUMERIC(10,6) NOT NULL,
    context_window INTEGER,
    context_multiplier NUMERIC(3,2) DEFAULT 1.00,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- DOCUMENTS
CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf','txt','docx','md','html')),
    file_size_bytes BIGINT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
    metadata JSONB DEFAULT '{}',
    chunk_count INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    token_count INTEGER NOT NULL,
    page_number INTEGER,
    section_heading TEXT,
    parent_chunk_id UUID REFERENCES public.document_chunks(id),
    image_urls TEXT[] DEFAULT '{}',
    image_captions TEXT[] DEFAULT '{}',
    image_types TEXT[] DEFAULT '{}',
    vlm_summary TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(document_id, chunk_index)
);

-- ASYNC JOBS
CREATE TABLE public.document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID REFERENCES public.documents(id) ON DELETE SET NULL,
    job_type TEXT NOT NULL CHECK (job_type IN ('upload','parse','chunk','embed','full_pipeline')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','processing','completed','failed','cancelled')),
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- CHAT
CREATE TABLE public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    model_id TEXT NOT NULL DEFAULT 'gemini-2.0-flash',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived','deleted')),
    metadata JSONB DEFAULT '{}',
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text' CHECK (content_type IN ('text','image','mixed')),
    image_urls TEXT[] DEFAULT '{}',
    retrieved_chunks JSONB DEFAULT '[]',
    token_usage JSONB,
    latency_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- WEB SEARCH RESULTS
CREATE TABLE public.web_search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_title TEXT,
    content_snippet TEXT,
    content_chunk_id UUID,
    relevance_score NUMERIC(5,4),
    fetched_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);
```

### 6.3 Row-Level Security (RLS) Policies

```sql
-- Enable RLS on all tables
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.web_search_results ENABLE ROW LEVEL SECURITY;

-- Helper Functions
CREATE OR REPLACE FUNCTION public.get_user_tenants()
RETURNS TABLE (tenant_id UUID, role TEXT)
LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT tu.tenant_id, tu.role FROM public.tenant_users tu WHERE tu.user_id = auth.uid(); $$;

CREATE OR REPLACE FUNCTION public.has_tenant_role(p_tenant_id UUID, p_roles TEXT[])
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$ BEGIN RETURN EXISTS (
    SELECT 1 FROM public.tenant_users
    WHERE tenant_id = p_tenant_id AND user_id = auth.uid() AND role = ANY(p_roles)
); END; $$;

CREATE OR REPLACE FUNCTION public.is_tenant_member(p_tenant_id UUID)
RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT EXISTS (SELECT 1 FROM public.tenant_users WHERE tenant_id = p_tenant_id AND user_id = auth.uid()); $$;

-- TENANTS: members read, admins update
CREATE POLICY "tenant_members_read" ON public.tenants FOR SELECT TO authenticated
    USING (public.is_tenant_member(id));
CREATE POLICY "tenant_admins_update" ON public.tenants FOR UPDATE TO authenticated
    USING (public.has_tenant_role(id, ARRAY['super_admin','admin']));

-- TENANT_USERS: members read, admins write
CREATE POLICY "tenant_users_members_read" ON public.tenant_users FOR SELECT TO authenticated
    USING (public.is_tenant_member(tenant_id));
CREATE POLICY "tenant_users_admins_write" ON public.tenant_users FOR ALL TO authenticated
    USING (public.has_tenant_role(tenant_id, ARRAY['super_admin','admin']));

-- TOKEN_BALANCES: self read, admin read, service write
CREATE POLICY "token_balances_self_read" ON public.token_balances FOR SELECT TO authenticated
    USING (user_id = auth.uid());
CREATE POLICY "token_balances_admin_read" ON public.token_balances FOR SELECT TO authenticated
    USING (public.has_tenant_role(tenant_id, ARRAY['super_admin','admin']));
CREATE POLICY "token_balances_service_write" ON public.token_balances FOR ALL TO service_role USING (true);

-- TOKEN_TRANSACTIONS: self read, service insert
CREATE POLICY "token_transactions_self_read" ON public.token_transactions FOR SELECT TO authenticated
    USING (user_id = auth.uid());
CREATE POLICY "token_transactions_service_insert" ON public.token_transactions FOR INSERT TO service_role
    WITH CHECK (true);

-- DOCUMENTS: tenant read, tenant insert, owner/admin update/delete
CREATE POLICY "documents_tenant_read" ON public.documents FOR SELECT TO authenticated
    USING (public.is_tenant_member(tenant_id));
CREATE POLICY "documents_tenant_insert" ON public.documents FOR INSERT TO authenticated
    WITH CHECK (public.is_tenant_member(tenant_id));
CREATE POLICY "documents_owner_or_admin_update" ON public.documents FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR public.has_tenant_role(tenant_id, ARRAY['super_admin','admin']));
CREATE POLICY "documents_owner_or_admin_delete" ON public.documents FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR public.has_tenant_role(tenant_id, ARRAY['super_admin','admin']));

-- DOCUMENT_CHUNKS: tenant read (for RAG), service write (background workers)
CREATE POLICY "document_chunks_tenant_read" ON public.document_chunks FOR SELECT TO authenticated
    USING (public.is_tenant_member(tenant_id));
CREATE POLICY "document_chunks_service_write" ON public.document_chunks FOR ALL TO service_role USING (true);

-- DOCUMENT_JOBS: user read, service write
CREATE POLICY "document_jobs_user_read" ON public.document_jobs FOR SELECT TO authenticated
    USING (user_id = auth.uid());
CREATE POLICY "document_jobs_service_write" ON public.document_jobs FOR ALL TO service_role USING (true);

-- CHAT_SESSIONS: user CRUD, admin read
CREATE POLICY "chat_sessions_user_crud" ON public.chat_sessions FOR ALL TO authenticated
    USING (user_id = auth.uid());
CREATE POLICY "chat_sessions_admin_read" ON public.chat_sessions FOR SELECT TO authenticated
    USING (public.has_tenant_role(tenant_id, ARRAY['super_admin','admin']));

-- CHAT_MESSAGES: user CRUD via session ownership
CREATE POLICY "chat_messages_user_crud" ON public.chat_messages FOR ALL TO authenticated
    USING (session_id IN (SELECT id FROM public.chat_sessions WHERE user_id = auth.uid()));

-- WEB_SEARCH_RESULTS: user read via session ownership
CREATE POLICY "web_search_results_user_read" ON public.web_search_results FOR SELECT TO authenticated
    USING (session_id IN (SELECT id FROM public.chat_sessions WHERE user_id = auth.uid()));

-- PERFORMANCE INDEXES
CREATE INDEX idx_documents_tenant_id ON public.documents(tenant_id);
CREATE INDEX idx_documents_user_id ON public.documents(user_id);
CREATE INDEX idx_documents_status ON public.documents(status);
CREATE INDEX idx_document_chunks_tenant_id ON public.document_chunks(tenant_id);
CREATE INDEX idx_document_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding ON public.document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX idx_chat_sessions_tenant_id ON public.chat_sessions(tenant_id);
CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON public.chat_messages(session_id);
CREATE INDEX idx_token_transactions_user_id ON public.token_transactions(user_id);
CREATE INDEX idx_token_transactions_request_id ON public.token_transactions(request_id);
CREATE INDEX idx_web_search_results_session_id ON public.web_search_results(session_id);
```

---

## 7. TOKEN METERING & BILLING ARCHITECTURE

### 7.1 Four-Phase Token Lifecycle

**Phase 1: Pre-Flight (Quota Check)**
- System estimates input tokens (prompt + RAG context)
- Query: `SELECT balance_tokens FROM token_balances WHERE ... FOR UPDATE` (row lock prevents race conditions)
- If balance < estimated: return HTTP 402 Payment Required
- Reserve estimated: `UPDATE token_balances SET reserved_tokens += estimated`

**Phase 2: Streaming (Real-time Accounting)**
- Incremental token counter during SSE stream
- Running total maintained in memory per request

**Phase 3: Post-Hoc (Final Settlement)**
- Calculate: `cost = (input_tokens * input_price) + (output_tokens * output_price)`
- Atomic transaction:
  ```sql
  BEGIN;
    UPDATE token_balances
    SET balance_tokens = balance_tokens - actual_cost,
        reserved_tokens = reserved_tokens - estimated_cost,
        total_spent_tokens = total_spent_tokens + actual_cost
    WHERE tenant_id = ? AND user_id = ?;
    INSERT INTO token_transactions (...);
  COMMIT;
  ```
- If actual < estimated: refund difference to balance
- If actual > estimated: deduct additional (rare edge case)

**Phase 4: Reconciliation (Background)**
- Cron job every 5 minutes
- Find stale reservations (transactions without completion signal)
- Release reserved tokens back to balance
- Log orphaned reservations for investigation

### 7.2 Stripe Webhook Integration
- `POST /api/billing/create-checkout-session` -> Stripe Checkout with metadata `{ tenant_id, user_id, token_package_id }`
- `POST /api/webhooks/stripe` -> Verify signature -> Credit tokens on `checkout.session.completed`
- Idempotency: check `request_id` before any balance update
- Event types: `checkout.session.completed`, `invoice.payment_failed`, `customer.subscription.updated`

### 7.3 Token Pricing Model

| Model | Input/1M | Output/1M | Context | Multiplier |
|-------|---------|----------|---------|-----------|
| gemini-2.0-flash | $0.075 | $0.30 | 1M | 1.0 |
| gemini-2.0-pro | $1.25 | $5.00 | 2M | 1.0 |
| llama-3.1-70b (local) | $0.00 | $0.00 | 128K | 1.0 |
| text-embedding-004 | $0.00 | — | 8K | 1.0 |

Markup: 20-30% on cloud provider costs. Local models priced into subscription tiers.

---

## 8. ASYNC JOB PROCESSING PIPELINE

### 8.1 Queue Strategy by Deployment Mode
- **Cloud**: Celery + Redis (proven at Instagram/Mozilla scale, Flower monitoring, horizontal scaling)
- **Local**: FastAPI BackgroundTasks (simpler, no extra infrastructure)
- **Embedded**: asyncio (no separate process, minimal footprint)

### 8.2 Job State Machine
```
QUEUED -> PROCESSING -> [COMPLETED | FAILED | QUEUED(retry)]
```
Max retries: 3 with exponential backoff (60s, 120s, 240s)

### 8.3 Task Types
- `process_document_pipeline`: parse -> extract images -> chunk -> embed -> store (with progress: 10% -> 30% -> 50% -> 70% -> 100%)
- `process_web_search`: Nexora search -> Firecrawl -> chunk -> store_temp
- `reconcile_token_reservations`: cleanup stale reservations every 5 min

### 8.4 Progress Tracking
- Real-time updates via WebSocket/SSE
- Job status stored in `document_jobs` table
- Frontend polls or listens for status changes

---

## 9. C#/.NET POS INTEGRATION STRATEGY

### 9.1 API Contract (Auto-generated from OpenAPI)
```csharp
public interface INexoraClient {
    Task<UploadResponse> UploadDocumentAsync(Stream file, string name, string type);
    Task<JobStatusResponse> GetJobStatusAsync(Guid jobId);
    IAsyncEnumerable<ChatStreamEvent> StreamChatAsync(Guid sessionId, string message);
    Task<ChatResponse> ChatAsync(Guid sessionId, string message); // sync for POS
    Task<List<RetrievedChunk>> SearchKnowledgeBaseAsync(string query, int topK = 5);
    Task<TokenBalanceResponse> GetTokenBalanceAsync();
    Task<HealthStatus> GetHealthAsync();
}

public record ChatStreamEvent {
    public string Type { get; init; } = "token"; // "token", "image", "done", "error"
    public string? Content { get; init; }
    public string? ImageUrl { get; init; }
    public string? ImageCaption { get; init; }
    public TokenUsage? Usage { get; init; }
}
```

### 9.2 Embedded Mode Differences
- No auth layer (X-POS-Client-ID header optional)
- Base URL: `http://localhost:8000`
- Sync chat endpoint for POS synchronous workflows
- Batch ingestion for POS transaction data
- Local file paths instead of CDN URLs

### 9.3 POS-Specific Endpoints
- `POST /api/v1/pos/ingest-sale-data` — batch POS data ingestion
- `POST /api/v1/pos/ingest-inventory-update` — inventory change updates
- `GET /api/v1/pos/query-product-info?q={query}` — quick product lookup (top-3)
- `POST /api/v1/pos/chat` — synchronous chat (non-streaming, full JSON response)
- `GET /api/v1/pos/health` — system health, model loaded, vector store status

---

## 10. SECURITY & COMPLIANCE FRAMEWORK

### 10.1 Threat Model & Mitigations

| Threat | Mitigation |
|--------|-----------|
| Tenant data leakage | RLS on ALL tables; `tenant_id` filtering in every query; never trust client-provided tenant_id |
| JWT token theft | Short expiry (15 min access, 7 day refresh); RS256 in cloud; never use `raw_user_meta_data` for auth |
| Token balance manipulation | `FOR UPDATE` row locking; `service_role` only for billing operations; idempotent transactions |
| File upload abuse | 50MB limit; MIME type validation; ClamAV virus scanning; storage bucket RLS |
| Prompt injection | Input sanitization; system prompt hardening; output validation |
| Rate limiting | Per-tenant Redis sliding window; per-user rate limits on chat endpoints |
| Data at rest | AES-256 encryption for file storage; TLS 1.3 in transit; encrypted backups |

### 10.2 Supabase Security Best Practices
- Enable RLS on **every** table immediately upon creation
- Use `(select auth.uid())` instead of `auth.uid()` in policies for performance (evaluates once per query)
- Never expose `service_role` key in client code — server-side only
- Use `SECURITY DEFINER` functions carefully — always add permission checks
- Protect sensitive columns with column-scoped grants or `BEFORE UPDATE` triggers
- Test RLS with pgTap: test both positive (CAN access) and negative (CANNOT access) cases
- RLS silent failures: SELECT/UPDATE/DELETE return 0 rows, not errors — verify state, not exceptions

### 10.3 Compliance Checklist
- [ ] SOC 2 Type II (cloud mode)
- [ ] GDPR: Right to erasure with cascade delete across all tenant tables
- [ ] HIPAA: BAA with Supabase if handling PHI
- [ ] PCI DSS: Stripe handles all payment data — never store card info

---

## 11. PERFORMANCE & SCALING STRATEGY

### 11.1 pgvector Performance Tuning
Based on current benchmarks: HNSW is the recommended default for queries under 5M vectors, with lower p99 latency than IVFFlat and graceful handling of updates. For datasets under 10M vectors per replica, pgvector remains the optimal choice — adding a vector column and HNSW index is a single `CREATE EXTENSION` plus one `CREATE INDEX`. The migration trigger to a dedicated vector database (Pinecone, Qdrant) is when corpus crosses ~15M vectors OR sustained query throughput crosses ~200 QPS OR running multi-tenant SaaS with 100+ namespaces.

**Tuning Parameters:**
- HNSW: `m=16`, `ef_construction=64` for balanced speed/recall
- Use `halfvec` to cut storage in half (2 bytes/dim vs 4)
- `CREATE INDEX CONCURRENTLY` to avoid blocking writes
- For normalized vectors, use inner product (`<#>`) instead of cosine
- Set `maintenance_work_mem` to 1-2GB for large index builds
- Run `VACUUM ANALYZE` after bulk inserts

### 11.2 Caching Strategy

| Layer | Technology | TTL | Purpose |
|-------|-----------|-----|---------|
| Embedding cache | Redis | 24h | Avoid re-embedding identical queries |
| Token balance | Redis | 30s | Reduce DB load on balance checks |
| Document metadata | Redis | 1h | Fast retrieval lookup |
| Web search results | Redis | 5min | Avoid re-crawling same queries |
| LLM responses | Redis | 1h | Cache common queries by content hash |

### 11.3 Performance Targets

| Metric | Target |
|--------|--------|
| Upload -> job_id response | < 500ms |
| 10MB PDF processing | < 30s |
| Vector search (1M vectors, tenant-filtered) | < 200ms |
| LLM first token latency | < 2s |
| Full chat response (streaming) | < 5s |
| Token balance check | < 50ms |
| Concurrent users per tenant | 100+ |

---

## 12. TECHNOLOGY STACK DECISIONS

### 12.1 Final Stack Matrix

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | FastAPI + Python 3.12 | Async-native, excellent DI, OpenAPI auto-gen |
| Frontend UI-1 | Next.js 15 + shadcn/ui | Admin dashboard, file uploads, job monitoring |
| Frontend UI-2 | Next.js 15 + shadcn/ui | Chat interface, SSE streaming, image display |
| Database | PostgreSQL 16 + pgvector | Single system for relational + vector data |
| Auth | Supabase Auth (cloud) / PyJWT (local) | JWT-based, RLS integration |
| Queue | Celery+Redis (cloud) / BackgroundTasks (local) / asyncio (embedded) | Scale-appropriate per mode |
| Embeddings | sentence-transformers (local) / Gemini API (cloud) | Speed vs quality tradeoff |
| LLM | Ollama (local) / Gemini 2.0 (cloud) | Privacy vs capability |
| Doc Parsing | PyMuPDF + Unstructured + Docling | Comprehensive format support |
| Image | PIL + CLIP / Gemini Multimodal | Visual RAG pipeline |
| Web Crawl | Nexora + Firecrawl | Deep content extraction |
| Monitoring | Prometheus + Grafana + Sentry | Metrics, logs, errors |
| Payments | Stripe | Token billing, webhooks |
| Deployment | Docker Compose (local) / Kubernetes (cloud) | Portability vs orchestration |

### 12.2 Embedding Model Selection (2026 MTEB Benchmarks)

| Model | Dimensions | MTEB Score | Use Case |
|-------|-----------|-----------|----------|
| text-embedding-3-large | 3072 | 64.6 | Cloud default (quality) |
| Cohere embed-v4 | 1024 | 66.2 | Cloud alternative |
| nomic-embed-text-v1.5 | 768 | 62.3 | Local premium (quality) |
| all-MiniLM-L6-v2 | 384 | 58.0 | Local default (speed) |
| Qwen3-Embedding-8B | 3584 | 70.58 | Local best (multilingual) |

**Decision**: `nomic-embed-text-v1.5` for local (best balance), `text-embedding-3-large` for cloud.

---

## 13. PROJECT FOLDER STRUCTURE

```
nexora-rag-platform/
|-- docker/
|   |-- docker-compose.local.yml      # Postgres + pgvector + Ollama
|   |-- docker-compose.cloud.yml      # App + Celery workers + Redis
|   |-- docker-compose.embedded.yml   # Minimal: FastAPI + Chroma + Ollama
|   |-- Dockerfile.api
|   |-- Dockerfile.worker
|
|-- backend/
|   |-- app/
|   |   |-- main.py                   # FastAPI app factory
|   |   |-- config.py                 # Pydantic Settings (deployment mode)
|   |   |-- dependencies.py           # DI container
|   |   |
|   |   |-- api/v1/
|   |   |   |-- router.py             # API aggregator
|   |   |   |-- auth.py               # Login, register, JWT
|   |   |   |-- documents.py          # Upload, list, delete
|   |   |   |-- jobs.py               # Job status, progress
|   |   |   |-- chat.py               # Streaming chat endpoints
|   |   |   |-- search.py             # Vector search, hybrid search
|   |   |   |-- billing.py            # Token balance, checkout
|   |   |   |-- webhooks.py           # Stripe webhooks
|   |   |   |-- pos.py                # POS-specific endpoints
|   |   |
|   |   |-- core/
|   |   |   |-- exceptions.py           # Custom exception hierarchy
|   |   |   |-- security.py             # JWT, password hashing
|   |   |   |-- constants.py            # Enums, defaults
|   |   |   |-- logging.py              # Structured logging (structlog)
|   |   |
|   |   |-- models/
|   |   |   |-- base.py                 # SQLAlchemy base, mixins
|   |   |   |-- tenant.py               # Tenant, TenantUser
|   |   |   |-- document.py             # Document, DocumentChunk
|   |   |   |-- chat.py                 # ChatSession, ChatMessage
|   |   |   |-- billing.py              # TokenBalance, TokenTransaction, TokenPricing
|   |   |   |-- job.py                  # DocumentJob, WebSearchResult
|   |   |
|   |   |-- schemas/
|   |   |   |-- tenant.py, document.py, chat.py, billing.py, job.py
|   |   |
|   |   |-- services/
|   |   |   |-- interfaces.py           # Abstract base classes
|   |   |   |-- auth/
|   |   |   |   |-- local_auth.py       # Local JWT (HS256)
|   |   |   |   |-- supabase_auth.py    # Supabase Auth (RS256)
|   |   |   |-- vector/
|   |   |   |   |-- pgvector_store.py   # PostgreSQL + pgvector
|   |   |   |   |-- chroma_store.py     # ChromaDB embedded
|   |   |   |   |-- supabase_vector.py  # Supabase match_documents RPC
|   |   |   |-- llm/
|   |   |   |   |-- ollama_provider.py
|   |   |   |   |-- gemini_provider.py
|   |   |   |   |-- huggingface_provider.py
|   |   |   |-- embedding/
|   |   |   |   |-- local_embedding.py  # sentence-transformers
|   |   |   |   |-- cloud_embedding.py  # Gemini / OpenAI
|   |   |   |-- storage/
|   |   |   |   |-- local_storage.py
|   |   |   |   |-- supabase_storage.py
|   |   |   |-- queue/
|   |   |   |   |-- celery_queue.py
|   |   |   |   |-- background_queue.py
|   |   |   |-- billing/
|   |   |   |   |-- token_meter.py      # Core metering logic
|   |   |   |   |-- stripe_webhook.py
|   |   |   |-- rag/
|   |   |   |   |-- retriever.py        # Vector search + rerank
|   |   |   |   |-- context_builder.py  # Assemble context from chunks
|   |   |   |   |-- query_classifier.py # Intent detection
|   |   |   |   |-- visual_rag.py       # Image chunk handling
|   |   |   |-- pos/
|   |   |       |-- pos_integration.py  # POS-specific service logic
|   |   |
|   |   |-- tasks/
|   |   |   |-- document_pipeline.py    # Celery tasks for doc processing
|   |   |   |-- web_search.py           # Nexora integration tasks
|   |   |   |-- billing_reconcile.py    # Token reservation cleanup
|   |   |
|   |   |-- utils/
|   |   |   |-- token_counter.py        # tiktoken / model-specific counting
|   |   |   |-- file_parser.py          # PDF, DOCX, TXT parsing
|   |   |   |-- image_extractor.py      # Layout parser for images
|   |   |   |-- chunker.py              # Semantic chunking strategies
|   |   |   |-- validators.py           # File type, size validation
|   |   |
|   |   |-- db/
|   |       |-- session.py              # Async SQLAlchemy session
|   |       |-- migrations/             # Alembic migrations
|   |       |-- supabase/
|   |           |-- schema.sql            # Complete schema + RLS policies
|   |
|   |-- tests/
|   |   |-- conftest.py                 # Pytest fixtures, test DB
|   |   |-- unit/                       # test_auth, test_token_meter, test_chunker
|   |   |-- integration/                # test_document_upload, test_chat_streaming, test_rag_pipeline
|   |   |-- e2e/                        # test_full_workflow
|   |
|   |-- pyproject.toml, alembic.ini, pytest.ini
|
|-- frontend/
|   |-- apps/
|   |   |-- admin-dashboard/            # UI-1: Control Panel
|   |   |   |-- app/                    # Upload, jobs, billing, settings pages
|   |   |   |-- components/           # upload-dropzone, document-card, job-progress, image-preview
|   |   |   |-- lib/api.ts            # Generated API client
|   |   |
|   |   |-- chat-interface/             # UI-2: End-User Chat
|   |       |-- app/                    # Chat home, active session
|   |       |-- components/           # chat-message, chat-input, image-carousel, source-citation, streaming-text
|   |       |-- hooks/                  # use-chat-stream (SSE), use-sessions
|   |
|   |-- packages/
|       |-- ui/                         # Shared shadcn/ui components
|       |-- api-client/                 # Generated OpenAPI TypeScript client
|       |-- types/                      # Shared TypeScript interfaces
|
|-- supabase/
|   |-- migrations/
|   |   |-- 001_initial_schema.sql      # Core tables
|   |   |-- 002_rls_policies.sql        # All RLS policies
|   |   |-- 003_token_system.sql        # Billing tables
|   |   |-- 004_functions.sql           # Helper functions
|   |   |-- 005_indexes.sql             # Performance indexes
|   |-- functions/
|       |-- stripe-webhook/             # Supabase Edge Function
|       |-- token-check/                # Pre-flight token validation
|
|-- infra/
|   |-- terraform/                      # Cloud infrastructure (AWS/GCP)
|   |-- kubernetes/
|   |   |-- api-deployment.yaml
|   |   |-- worker-deployment.yaml
|   |   |-- redis-deployment.yaml
|   |   |-- ingress.yaml
|   |-- scripts/
|       |-- deploy-local.sh
|       |-- deploy-cloud.sh
|       |-- deploy-embedded.sh
|
|-- docs/
|   |-- architecture/                   # System diagrams, data flow, deployment modes
|   |-- api/                            # OpenAPI spec
|   |-- pos-integration/                # C# SDK guide
|   |-- runbooks/                       # Incident response, scaling guide
|
|-- scripts/
|   |-- setup-local.sh                  # One-command local setup
|   |-- setup-embedded.sh               # POS integration setup
|   |-- run-tests.sh
|   |-- generate-client.sh              # Generate C# / TS clients
|
|-- .env.example, .env.local, .env.cloud, .env.embedded
|-- Makefile, README.md, LICENSE
```

---

## 14. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
- Project scaffolding (FastAPI, Next.js, Docker)
- Abstract service interfaces (Auth, Vector, LLM, Storage, Queue)
- Local mode implementation (Ollama, PostgreSQL + pgvector)
- Basic document upload (PDF, TXT, DOCX) with PyMuPDF
- Simple RAG pipeline (chunk -> embed -> store -> retrieve -> generate)

### Phase 2: Multi-Tenancy & Auth (Weeks 3-4)
- Supabase schema with RLS policies
- Supabase Auth integration (cloud mode)
- Local JWT auth (local mode)
- Tenant isolation testing (cross-tenant data leakage tests)
- Role-based access control (super_admin, admin, member, viewer)

### Phase 3: Visual RAG (Weeks 5-6)
- Image extraction from PDFs (LayoutParser / PyMuPDF)
- Image metadata attachment to chunks
- Ingestion VLM (summary generation)
- Retrieval VLM integration
- Unified context assembly
- Frontend image display in chat responses

### Phase 4: Async Processing & Jobs (Weeks 7-8)
- Celery + Redis setup (cloud)
- BackgroundTasks (local)
- Job status tracking API
- Progress reporting (WebSocket / SSE)
- Retry logic with exponential backoff
- Dead letter queue for failed jobs

### Phase 5: Token Metering & Billing (Weeks 9-10)
- Token balance schema
- Pre-flight quota checking with row locking
- Streaming token accounting
- Post-hoc settlement
- Stripe Checkout integration
- Webhook handling (checkout.session.completed)
- Token transaction ledger
- Admin dashboard for usage analytics

### Phase 6: Nexora Web Search Integration (Weeks 11-12)
- Query intent classifier
- Nexora crawler integration hook
- Firecrawl deep scraping
- On-the-fly chunking and embedding of web content
- Web result TTL and caching
- Hybrid context assembly (vector + web)

### Phase 7: Embedded/POS Mode (Weeks 13-14)
- ChromaDB embedded integration
- No-auth mode for POS
- C# client SDK generation from OpenAPI
- POS-specific endpoints
- Batch ingestion API
- Sync vs async chat endpoints
- Local model bundling strategy

### Phase 8: Production Hardening (Weeks 15-16)
- Kubernetes deployment manifests
- Prometheus + Grafana monitoring
- Sentry error tracking
- Rate limiting (per tenant via Redis sliding window)
- Input validation hardening
- Load testing (k6 / Locust)
- Security audit (penetration testing)
- Documentation (API docs, runbooks, C# SDK guide)

---

## 15. RISK ASSESSMENT & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Embedding model change requires re-indexing | High | High | Version embeddings; support multiple models simultaneously during migration |
| pgvector performance degrades at scale | Medium | High | Monitor vector count; have Qdrant/Pinecone migration path ready at ~15M vectors |
| Token balance race conditions | Medium | Critical | `FOR UPDATE` row locking; idempotent transactions with `request_id` |
| VLM hallucinations in visual RAG | High | Medium | Unified context approach; text LLM as final arbiter; confidence scoring |
| Celery worker crashes during job | Medium | Medium | Task retries with backoff; dead letter queue; job status persistence |
| Stripe webhook delivery failures | Low | High | Webhook retry logic; manual reconciliation endpoint; idempotency keys |
| Local mode dependency drift | Medium | Medium | Lock dependency versions; Docker images for reproducibility |
| POS integration latency | Medium | High | Local model cache; sync endpoints; SQLite local cache |
| RLS policy bypass (CVE-style) | Low | Critical | Automated RLS testing with pgTap; never trust `raw_user_meta_data`; use `security invoker` |
| Service role key leak | Low | Critical | Server-side only; rotate via Supabase new key model; GitHub secret scanning |

---

## APPENDIX: KEY DESIGN PATTERNS

### A.1 Abstract Factory Pattern (Service Selection)
Runtime selection of concrete implementations based on `DEPLOYMENT_MODE`. All business logic depends on interfaces, not implementations.

### A.2 Unit of Work Pattern (Token Transactions)
Atomic balance update + transaction recording within a single database transaction with row locking (`FOR UPDATE`).

### A.3 Circuit Breaker Pattern (LLM Provider)
If primary LLM fails, fallback to secondary, then tertiary. Track circuit state per provider to avoid cascading failures.

### A.4 CQRS Pattern (Read vs Write)
Document chunks written by background workers (service_role), read by chat endpoints (authenticated via RLS). Separate optimized read models from write models.

---

*Document Version: 1.0*
*Author: Principal Architect*
*Date: 2026-07-09*
*Classification: Internal Planning Document*


> tesaract to be implimented fully , image return , maybe metadata (storage , links retrieval)
> jarvis 
> file upload 
> 

## 2. Decoupling Frontend & Backend Architecture

### 2.1 Findings from the audits
- Both frontends (`FileUploader.js`, `RagChatApp.js`) contain **hardcoded IPs** (`http://192.168.0.100:5000`, `http://192.168.100.45:5000`, and a phantom `:8000` for image chat that has no backend route at all). This means the frontend is physically coupled to one developer's LAN address, not to a service contract.
- The image-chat endpoint, `/delete/<filename>`, and `/assistant` are all called by frontend JS but **do not exist** in either backend. This means the "interface" between frontend and backend was never formally defined — routes were added to the UI speculatively.
- There is no WebSocket or streaming contract on either side, despite the recommended fix priority list explicitly calling for streaming.

### 2.2 Required boundary definition
1. Define the backend as a **standalone, network-agnostic API service** that exposes only versioned, documented REST routes plus one streaming channel. Nothing in the backend may assume it is being called from a specific frontend origin or IP.
2. Define the frontend as a **pure client** that resolves the backend's base URL from an environment/config value injected at build or runtime — never a literal IP string in source.
3. Formalize the following interface contract as the only communication surface between the two layers:
   - Upload intake route (multipart form submission) that returns a job identifier synchronously and nothing else.
   - Job-status polling route, keyed by job identifier, returning ingestion state (queued/processing/complete/failed) — this closes the "no upload status tracking" gap identified in both audits.
   - Document management routes for listing and deleting ingested documents by source identifier — this closes the missing `/delete/<filename>` gap, but as a properly namespaced route rather than the ad hoc path the old frontend guessed at.
   - Chat route that accepts a prompt (and optional image reference) and responds via a streaming channel (Server-Sent Events or WebSocket) rather than a single buffered JSON payload — this closes the "no streaming" gap called out as a P1 issue in the audit and directly fixes the "LLM bypassed / raw chunks returned" critical bug, since a streaming contract forces the generation step to actually exist.
   - Health/readiness route for monitoring, replacing the currently absent `/health`.
4. Remove the speculative `/assistant` and image-chat routes from the frontend entirely until they are formally specified on the backend side; do not leave client calls pointing at endpoints that don't exist.
5. Any port number, hostname, or protocol must be resolved from configuration, never embedded in a JS/TS literal.

### 2.3 Acceptance checklist
- [ ] Zero IP literals or hardcoded ports remain in frontend source.
- [ ] Every route the frontend calls has a corresponding, implemented backend route — no orphaned client calls.
- [ ] Chat delivery is streaming, not single-shot JSON.
- [ ] Upload returns a job id immediately; status is separately queryable.
# Answer 2: Proposed Architecture for 3-Target Deployment

## Current Problem

Your `app_server.py` is __monolithic__ — it serves HTML templates, static files, AND API routes all from one process. This doesn't scale to 3 targets.

## Proposed Architecture

```javascript
┌─────────────────────────────────────────────────────────┐
│                    LANDING PAGE                          │
│              (Simple static HTML/CSS)                    │
│           localhost:5000  →  links to:                   │
│              /chatbot  →  Chat UI                        │
│              /fileuploader  →  Upload UI                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────┐    ┌──────────────────────────────┐
│   WEB FRONTEND      │    │   DESKTOP APP                │
│  (Static HTML/JS)   │    │  (Electron / Tauri / PyQt)   │
│                     │    │                              │
│  - Chat UI          │    │  - Same UI but local         │
│  - File Uploader    │    │  - Can run fully offline     │
│  - Landing Page     │    │  - Embeds its own frontend   │
└─────────┬───────────┘    └───────────┬──────────────────┘
          │                            │
          └──────────┬─────────────────┘
                     │ HTTP REST API
                     ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND API LAYER (FastAPI)                 │
│                                                         │
│  /api/chat/send_prompt     →  Chat + RAG pipeline       │
│  /api/files/upload         →  File ingestion            │
│  /api/files/list           →  List uploaded docs        │
│  /api/files/delete/{id}    →  Delete document           │
│  /api/health               →  Health check              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CORE ENGINE (shared by all)                    │    │
│  │  - Embedding (HF API)                           │    │
│  │  - Vector Store (Supabase pgvector)             │    │
│  │  - Reranker (cross-encoder)                     │    │
│  │  - LLM (OpenAI / local Mistral)                 │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Separation Strategy

### 1. Backend → Pure API (no templates, no static files)

```javascript
FASTAPI/
├── api/                    # API routes only
│   ├── __init__.py
│   ├── chat.py             # POST /api/chat/send_prompt
│   ├── files.py            # POST /api/files/upload, DELETE /api/files/{id}
│   └── health.py           # GET /api/health
├── core/                   # Shared business logic
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── reranker.py
│   └── llm.py              # OpenAI / local model abstraction
├── app.py                  # FastAPI app, no templates, no static mount
└── run.py
```

### 2. Web Frontend → Standalone Static Site

```javascript
STATIC/
├── index.html              # Landing page (links to /chat and /upload)
├── chat/
│   ├── index.html
│   └── app.js              # Calls http://localhost:5000/api/chat/send_prompt
├── upload/
│   ├── index.html
│   └── app.js              # Calls http://localhost:5000/api/files/upload
└── shared/
    ├── css/
    └── js/                 # Shared utilities
```

__Served by:__ A simple static file server (Nginx, or a separate lightweight FastAPI instance on port 8080)

### 3. Desktop App → Local-First Client

```javascript
desktop/
├── main.py                 # PyQt/PySide entry point
├── ui/                     # Same HTML/JS but packaged locally
│   ├── chat/
│   └── upload/
├── local_api.py            # Calls localhost:5000 or embedded server
└── build.py                # PyInstaller packaging script
```

__Options:__

- __Electron__ (JS-based, heavy but familiar)
- __Tauri__ (Rust-based, lightweight, secure)
- __PyQt/PySide__ (Python-native, can embed the FastAPI server directly)

### 4. Landing Page

A simple `index.html` at the root that shows two cards:

- __Chat Assistant__ → links to `/chat/`
- __Document Upload__ → links to `/upload/`

## Migration Path (Minimal Changes)

### Step 1: Add `/api/` prefix to all routes

```python
# In app_server.py, change:
app.include_router(chat_route, prefix="")
app.include_router(uploadfile_route, prefix="")

# To:
app.include_router(chat_route, prefix="/api")
app.include_router(uploadfile_route, prefix="/api")
```

### Step 2: Create a landing page route

```python
@app.get('/', response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

### Step 3: Update frontend JS to call `/api/...` endpoints

```javascript
// FileUploader.js → change to:
fetch('/api/files/upload', ...)

// RagChatApp.js → change to:
fetch('/api/chat/send_prompt', ...)
```

### Step 4: Separate the static frontend (optional, for desktop)

Move `TEMPLATE/` and `STATIC/` into a `frontend/` directory that can be served independently.
