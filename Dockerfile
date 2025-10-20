# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH="/app"

WORKDIR /app

COPY requirements.txt .
COPY requirements.docker.txt .

# Install system packages needed for pip to fetch git packages and build wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
        pkg-config \
        make && \
    rm -rf /var/lib/apt/lists/*

# Copy project files before installing so editable/local installs in requirements.txt can reference /app
COPY . .

ARG GITHUB_TOKEN
ARG FULL_REQUIREMENTS=0
# By default, install a minimal runtime set (faster). Set FULL_REQUIREMENTS=1 to install the full requirements.txt.
RUN if [ "$FULL_REQUIREMENTS" = "1" ]; then \
            if [ -n "$GITHUB_TOKEN" ]; then \
                sed -i "s|https://github.com/eins53740/BD_StockEvaluator.git|https://${GITHUB_TOKEN}@github.com/eins53740/BD_StockEvaluator.git|g" requirements.txt; \
            fi && \
            sed -i "s|file:///C:/Users/bfsd/Documents/GitHub/BD_StockEvaluator|file:///app|g" requirements.txt || true && \
            pip install --upgrade pip && \
            pip install --no-cache-dir -r requirements.txt; \
        else \
            pip install --upgrade pip && \
            pip install --no-cache-dir -r requirements.docker.txt; \
        fi

EXPOSE 8000

CMD ["uvicorn", "bd_stockevaluator.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
