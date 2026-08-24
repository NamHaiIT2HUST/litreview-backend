# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
# NOTE: langchain-huggingface and sentence-transformers used to be stripped from the
# runtime image here to keep builds fast, which silently broke EMBEDDING_PROVIDER=local
# (see src/services/vector_store.py) -- it fell back to a non-semantic hash embedding
# with no error. They are real runtime dependencies now and must ship in production.
RUN grep -Ev '^(ruff|pytest|pytest-asyncio)($|[<>=])' requirements.txt > requirements-runtime.txt \
    && pip install --no-cache-dir --retries 10 --timeout 120 --prefix=/install -r requirements-runtime.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY . .

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
