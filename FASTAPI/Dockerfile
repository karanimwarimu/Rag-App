# Build context for this Dockerfile is the FASTAPI/ directory, e.g.:
#   docker build -f FASTAPI/Dockerfile -t rag-backend FASTAPI
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System libraries for PDF parsing (Poppler) and OCR (Tesseract).
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source. Secrets (.env) are excluded via .dockerignore and
# must be supplied as environment variables by the host (e.g. Render).
COPY . .

EXPOSE 5000

# Render injects PORT; fall back to 5000 for local runs.
CMD ["sh", "-c", "uvicorn app_server:app --host 0.0.0.0 --port ${PORT:-5000}"]
