# Production Dockerfile for BimaSakshi Backend (Render Web Service)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/root

WORKDIR /app

# Install FFmpeg (required by gnani_service.py to convert browser WebM/Opus -> 16kHz PCM WAV)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-warm ChromaDB default ONNX embedding model (all-MiniLM-L6-v2) into container cache
# so Render startup does not depend on downloading ~79MB during cold boot / health check.
RUN python -c "from chromadb.utils import embedding_functions; fn = embedding_functions.DefaultEmbeddingFunction(); fn(['Star Health Premier warmup'])"

# Copy backend source and tracked policy corpus (data/policy_clauses.md)
COPY . .

EXPOSE 8000

# Listen on 0.0.0.0 and Render-injected PORT (defaults to 8000 locally)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

