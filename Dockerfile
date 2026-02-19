# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

ARG GITHUB_TOKEN
ARG FULL_REQUIREMENTS=0

COPY requirements.txt ./
COPY requirements.docker.txt ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/* && \
    python -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel

RUN if [ "$FULL_REQUIREMENTS" = "1" ]; then \
        if [ -n "$GITHUB_TOKEN" ]; then \
            sed -i "s|https://github.com/|https://${GITHUB_TOKEN}@github.com/|g" requirements.txt; \
        fi; \
        sed -i "s|file:///C:/Users/bfsd/Documents/GitHub/BD_StockEvaluator|file:///app|g" requirements.txt || true; \
        grep -vEi "(-e\s+git\+|bd_python_ai|bd-python-ai|pydantic==|gradio|google-genai|openbb(-|_)|kivy|kivy-deps|kivy-examples|kivy-garden|pyqt5|pyqt5-qt5|pyqt5_sip|pyqt5-qt|ta-lib|metatrader5|pywin32|pywin32-ctypes|pypiwin32|tensorflow(-intel)?)" requirements.txt > /tmp/requirements.filtered.txt || true; \
        grep -vEi "(file::///|file:///|bd_stockevaluator|bd-stockevaluator)" /tmp/requirements.filtered.txt > /tmp/requirements.filtered.no_local.txt || true; \
        pip install --no-cache-dir -r /tmp/requirements.filtered.no_local.txt; \
    else \
        pip install --no-cache-dir -r requirements.docker.txt; \
    fi

COPY . .

RUN pip install --no-deps .


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DOCKER_RUNTIME=mock

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src/bd_stockevaluator/static /app/static
COPY --from=builder /app/src/bd_stockevaluator/templates /app/templates
COPY --from=builder /app/config ./config
COPY --from=builder /app/gunicorn.conf.py ./gunicorn.conf.py

# Ensure runtime directories exist and are writable by the non-root user.
RUN groupadd --system appuser && \
    useradd --system --gid appuser --create-home --home-dir /home/appuser appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app /home/appuser /opt/venv

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "bd_stockevaluator.api.main:app"]
