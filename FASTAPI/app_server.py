import logging
logging.basicConfig(level=logging.INFO)
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load app-level config (FRONTEND_ORIGIN, Embedding_KEY, reranker_KEY) from the
# utilities .env. FRONTEND_ORIGIN may be a comma-separated list of allowed origins.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "utilities", ".env"))

FRONTEND_ORIGIN = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
    if o.strip()
]

from routes.fileupload import router as uploadfile_route
from routes.chatbot import router as chat_route
from routes.auth import router as auth_route

app = FastAPI()

# --- CORS settings ---
# Restricted to the frontend origin(s) via FRONTEND_ORIGIN (Guide 1 Step 5).
# Set FRONTEND_ORIGIN in FASTAPI/utilities/.env (comma-separated for multiple).
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: Jinja2 template serving and the /static mount were removed in Guide 1
# Step 4. This process now exposes API routes only; the standalone React+Vite
# frontend (frontend/) serves all UI and static assets.

app.include_router(chat_route, prefix="")
app.include_router(uploadfile_route, prefix="")
app.include_router(auth_route, prefix="")
