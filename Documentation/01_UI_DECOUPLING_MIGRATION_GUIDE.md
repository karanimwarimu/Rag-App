# Guide 1: UI Decoupling, Landing Page & Modular Expansion — Agent Execution Guide

**Target repo:** RAG_APP
**Stack decision:** React + Vite (new standalone frontend, replaces Jinja2 templates)
**Scope:** Frontend/backend decoupling, landing page, auth UI shell, global assistant placement, tool routing. Does NOT include: real backend auth endpoints, LLM streaming backend, or the web link ingestor backend — those are future work, stubbed only.

---

## 0. Execution Protocol — READ FIRST

You are executing this guide under strict sequential gating:

1. Execute **one step only**, in order. Do not skip ahead or batch multiple steps into one turn.
2. After each step, stop and report back in this exact format:
   - **Step completed:** `<step number + name>`
   - **Files touched:** `<explicit list of file paths created/modified/deleted>`
   - **Deliberately left alone:** `<anything that looked related but you did not touch, and why>`
   - **Assumptions made:** `<any judgment call you made that wasn't explicit in this guide>`
   - **Ready for review.**
3. Do not proceed to the next step until you receive explicit confirmation (e.g. "proceed" / "go to step N").
4. If a step depends on a decision not specified in this guide, stop and ask rather than guessing.
5. Never touch files outside the explicit scope of the current step, even if you notice unrelated issues — note them under "Deliberately left alone" instead.

---

## 1. Current State Summary (context, not action)

- FastAPI (`FASTAPI/app_server.py`) currently serves two Jinja2-rendered pages (`GET /chatbot`, `GET /fileuploader`) plus static assets, alongside the API routes (`POST /File_Upload`, `POST /send_prompt`). CORS is `allow_origins=["*"]`.
- `STATIC/JS/RagChatApp.js` and `STATIC/JS/FileUploader.js` call hardcoded LAN IPs (`192.168.100.3:5000`, `192.168.0.100:8000`) and reference endpoints that don't exist server-side (`/delete/{filename}`, `/assistant`, `/chat-with-image`).
- `/send_prompt` is a synchronous JSON endpoint. LLM generation is disabled — it returns raw reranked chunk text as `RESULT`, not a generated streaming answer.
- There is no auth system anywhere in the backend — no user table, no session, no token issuance.
- The "virtual assistant" referenced in the old `FileUploader.js` has no working backend route; it's currently a dead UI reference.

---

## 2. Target Directory Layout

```
RAG_APP/
├── FASTAPI/                          # UNCHANGED except app_server.py + CORS (Step 5)
│   ├── app_server.py
│   ├── configfile.json
│   ├── run.py
│   ├── routes/
│   ├── utilities/
│   └── ...
├── frontend/                         # NEW — standalone React + Vite app
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   ├── .env                          # git-ignored
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                   # router root
│   │   ├── config/
│   │   │   └── env.js                # reads import.meta.env.VITE_*
│   │   ├── api/
│   │   │   ├── client.js             # fetch wrapper, base URL from env
│   │   │   ├── chat.js                # /api/v1/chat calls
│   │   │   ├── upload.js              # /api/v1/upload calls
│   │   │   └── assistant.js           # stubbed, points at future /api/v1/assistant
│   │   ├── context/
│   │   │   └── SessionContext.jsx     # user_id, auth token placeholder state
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── NavBar.jsx
│   │   │   │   └── Shell.jsx
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.jsx
│   │   │   │   ├── SignUpForm.jsx
│   │   │   │   ├── ForgotPasswordForm.jsx
│   │   │   │   └── OAuthButtons.jsx
│   │   │   └── assistant/
│   │   │       └── GlobalAssistantWidget.jsx
│   │   ├── pages/
│   │   │   ├── Landing.jsx
│   │   │   ├── ChatWorkspace.jsx
│   │   │   ├── UploadWorkspace.jsx
│   │   │   └── LinkUploaderStub.jsx   # future placeholder page
│   │   └── styles/
│   │       └── (Tailwind config, since CDN Tailwind is dropped for a proper build)
│   └── public/
│       └── IMAGES/                   # moved from STATIC/IMAGES
├── STATIC/                           # DEPRECATED after Step 4 — kept until Step 6 confirms parity, then deleted
├── TEMPLATE/                         # DEPRECATED — deleted in Step 4
├── Documentation/
└── README.md                         # updated in final step
```

---

## 3. Step-by-Step Migration Roadmap

### Step 1 — Scaffold the frontend app
- Create `frontend/` using Vite's React template (`npm create vite@latest frontend -- --template react`).
- Install Tailwind CSS properly (PostCSS pipeline, not CDN) since the app is now a real build.
- Create `frontend/.env.example` with:
  ```
  VITE_API_BASE_URL=http://localhost:5000
  VITE_ENABLE_WEBSOCKET_CHAT=false
  VITE_ENABLE_LINK_UPLOADER=false
  ```
- Create `frontend/src/config/env.js` exporting typed reads of these vars (throw a clear error at startup if `VITE_API_BASE_URL` is missing).
- Do not touch `FASTAPI/`, `STATIC/`, or `TEMPLATE/` in this step.

### Step 2 — Extract the Chat interface
- Build `pages/ChatWorkspace.jsx` reproducing the functional behavior of `RagChatApp.html` + `RagChatApp.js`, translated to React state/hooks.
- All network calls go through `src/api/chat.js`, which reads `VITE_API_BASE_URL` — no hardcoded IPs, no relative paths that assume same-origin.
- The chat client should be written against a **streaming-ready contract**: attempt `fetch` with a readable stream reader against `${VITE_API_BASE_URL}/api/v1/chat`, falling back to a single JSON response if the backend doesn't stream. Note in code comments that the backend does not yet stream — this is forward-compatible scaffolding only.
- Do not implement `/delete`, `/assistant`, or `/chat-with-image` calls — those were dead references in the old JS. Confirm they're dropped, not carried forward.

### Step 3 — Extract the File Uploader interface
- Build `pages/UploadWorkspace.jsx` reproducing `FileUploader.html` + `FileUploader.js` functionality: drag-and-drop, extension validation (mirror `Allowed_Extensions` from `configfile.json` — expose this list via a small config endpoint or duplicate it explicitly in frontend config, your call, but state which you chose), upload progress state, and success/error handling.
- Calls go through `src/api/upload.js` → `${VITE_API_BASE_URL}/api/v1/upload` (see Step 5 for backend route renaming).
- Remove the old embedded virtual-assistant widget from this page entirely — it moves to the landing page in Step 7.

### Step 4 — Retire Jinja2 template serving
- In `FASTAPI/app_server.py`, remove the `GET /chatbot` and `GET /fileuploader` routes and the Jinja2Templates/StaticFiles mounts that only exist to serve them.
- Delete `TEMPLATE/FileUploader.html` and `TEMPLATE/RagChatApp.html`.
- Move any still-needed static assets (e.g. `STATIC/IMAGES/*`) into `frontend/public/IMAGES/`, then delete `STATIC/`.
- Confirm `FASTAPI/app_server.py` after this step only exposes API routes (list them explicitly in your report).

### Step 5 — Normalize backend API routes + CORS
- Rename routes to a versioned API convention: `POST /File_Upload` → `POST /api/v1/upload`, `POST /send_prompt` → `POST /api/v1/chat`. Keep the underlying handler logic untouched — this is a routing-layer change only.
- Restrict CORS in `app_server.py` from `allow_origins=["*"]` to an explicit list read from a backend `.env` var, e.g. `FRONTEND_ORIGIN=http://localhost:5173` (Vite's default dev port). Document this in `FASTAPI/utilities/.env.example`.
- Do not change request/response payload shapes in this step — that's out of scope for this guide.

### Step 6 — Parity check
- Run both apps side by side (`uvicorn` on :5000, `npm run dev` on :5173) and confirm chat + upload workflows work end-to-end through the new frontend.
- Only after this is confirmed working, delete the now-empty `STATIC/` and `TEMPLATE/` directories if not already removed in Step 4.

### Step 7 — Global virtual assistant placement
- Build `components/assistant/GlobalAssistantWidget.jsx` as a persistent, dismissible component mounted at the `Shell.jsx` layout level (so it's available on every page, not just one workspace).
- Wire it to `src/api/assistant.js`, which should call `${VITE_API_BASE_URL}/api/v1/assistant`. This backend route does not exist yet — implement the frontend to handle a 404/501 gracefully (e.g. "Assistant coming soon" state) rather than throwing.

### Step 8 — Landing page, auth shell, and routing
See Section 4 below for the full blueprint. Build:
- `pages/Landing.jsx`
- `components/auth/LoginForm.jsx`, `SignUpForm.jsx`, `ForgotPasswordForm.jsx`, `OAuthButtons.jsx`
- `context/SessionContext.jsx`
- Client-side routing (React Router) mapping `/`, `/login`, `/signup`, `/app/chat`, `/app/upload`, `/app/links` (stub).

### Step 9 — Web Link Uploader stub
- Create `pages/LinkUploaderStub.jsx`: a visually complete but functionally inert page — layout, input field for a URL, disabled "Ingest" button, and a "Coming soon" banner.
- Add it to routing and navigation behind the `VITE_ENABLE_LINK_UPLOADER` flag (hidden from nav when `false`).
- No backend calls implemented for this step.

### Step 10 — Documentation update
- Update `README.md`: replace the old single-service architecture diagram with the new two-service (frontend + backend) diagram, update the Usage section with two separate run commands, update Known Limitations (remove "hardcoded LAN IPs" and "missing /delete, /assistant" now that they're handled or explicitly stubbed).

---

## 4. Landing Page & Navigation Blueprint

**Layout (`Landing.jsx`):**
- Hero section: project name, one-line value proposition, primary CTA ("Get Started" → `/signup`, secondary "Log In" → `/login`).
- Feature summary: 3-column grid — Chat, Document Upload, (grayed-out) Web Link Ingestion — each linking to its route once authenticated, or to signup if not.
- Global assistant widget mounted here (and on all `/app/*` routes) per Step 7.

**Auth forms (all placeholder — no real backend calls yet, wire to `console.log`/local state stub and TODO comment marking the future POST target):**
- `LoginForm.jsx` — email, password, submit → future `POST /api/v1/auth/login`.
- `SignUpForm.jsx` — email, password, confirm password, submit → future `POST /api/v1/auth/signup`.
- `ForgotPasswordForm.jsx` — email, submit → future `POST /api/v1/auth/reset`.
- `OAuthButtons.jsx` — "Continue with Google", "Continue with GitHub" — buttons only, `onClick` stub that logs intent, no OAuth flow implemented.

**Session context (`SessionContext.jsx`):**
```js
{
  user_id: null,        // string | null — set on successful login (future)
  authToken: null,       // string | null
  isAuthenticated: false,
  login: (payload) => {},   // stub, sets state, no real request yet
  logout: () => {},
}
```
Provide this via a `SessionProvider` wrapping the whole app in `App.jsx`. All workspace pages should read `isAuthenticated` and redirect to `/login` if false — but since real auth doesn't exist yet, default `isAuthenticated` to `true` behind a dev flag (`VITE_SKIP_AUTH=true` in `.env.example`) so the tool workspaces remain usable during this transitional phase. State this default explicitly in your Step 8 report.

**Routing matrix:**

| Route | Component | Auth-gated? |
|---|---|---|
| `/` | `Landing.jsx` | No |
| `/login` | `LoginForm.jsx` (within landing layout) | No |
| `/signup` | `SignUpForm.jsx` | No |
| `/app/chat` | `ChatWorkspace.jsx` | Yes (soft-gated per above) |
| `/app/upload` | `UploadWorkspace.jsx` | Yes (soft-gated per above) |
| `/app/links` | `LinkUploaderStub.jsx` | Yes, and behind `VITE_ENABLE_LINK_UPLOADER` |

---

## 5. Integration Spec — UI Action → Endpoint Mapping

| UI Action | Frontend call | Backend endpoint | Status |
|---|---|---|---|
| Send chat message | `api/chat.js` | `POST {VITE_API_BASE_URL}/api/v1/chat` | Live (renamed from `/send_prompt` in Step 5) |
| Upload document | `api/upload.js` | `POST {VITE_API_BASE_URL}/api/v1/upload` | Live (renamed from `/File_Upload` in Step 5) |
| Delete uploaded file | — | `DELETE {VITE_API_BASE_URL}/api/v1/documents/{id}` | **Not implemented** — do not build frontend call until backend exists |
| Ask virtual assistant | `api/assistant.js` | `POST {VITE_API_BASE_URL}/api/v1/assistant` | **Not implemented** — frontend built with graceful-degradation only (Step 7) |
| Login | `SessionContext.login()` | `POST {VITE_API_BASE_URL}/api/v1/auth/login` | **Not implemented** — placeholder only |
| Sign up | `SessionContext` (future) | `POST {VITE_API_BASE_URL}/api/v1/auth/signup` | **Not implemented** — placeholder only |
| Ingest web link | — | `POST {VITE_API_BASE_URL}/api/v1/links` | **Not implemented** — stub UI only, Step 9 |

---

## 6. Explicit Non-Goals (do not implement under this guide)

- Real authentication (password hashing, token issuance, session persistence, OAuth provider integration).
- Backend streaming for `/api/v1/chat`.
- Backend implementation of `/api/v1/assistant` or `/api/v1/links`.
- Any change to chunking, embedding, retrieval, or reranking logic.
- Docker/deployment changes (separate guide).
