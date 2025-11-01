# syntax=docker/dockerfile:1.7
# Multi-stage production-ready Dockerfile for BD_StockEvaluator
# Epic 11 - F11.1: Containerisation with best practices

# ============================================================================
# Stage 1: Builder - Install dependencies and prepare wheels
# ============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for better layer caching
COPY pyproject.toml README.md MANIFEST.in ./
COPY src/ ./src/

# Install dependencies and build wheel
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /wheels . && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r <(python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))")

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.12-slim AS runtime

# Metadata
LABEL maintainer="Bruno Dias (BD)" \
      description="Stock Evaluator API - FastAPI backend for comprehensive stock analysis" \
      version="0.1.0"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    PORT=8000

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy wheels from builder and install
COPY --from=builder --chown=appuser:appuser /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser .env.example ./.env

# Create data directory for SQLite and caching
RUN mkdir -p /app/data /app/data/macro && \
    chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE ${PORT}

# Health check - probe the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health').read()" || exit 1

# Start FastAPI application
CMD ["sh", "-c", "uvicorn src.bd_stockevaluator.api.main:app --host 0.0.0.0 --port ${PORT}"]
