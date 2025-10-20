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
# When installing the full requirements, filter out desktop/GUI-only packages (Kivy, PyQt, etc.)
RUN if [ "$FULL_REQUIREMENTS" = "1" ]; then \
            # Inject GITHUB_TOKEN into any github.com URLs in requirements.txt if provided
            if [ -n "$GITHUB_TOKEN" ]; then \
                sed -i "s|https://github.com/|https://${GITHUB_TOKEN}@github.com/|g" requirements.txt; \
            fi && \
            # Replace Windows local path with container path for editable/local install
            sed -i "s|file:///C:/Users/bfsd/Documents/GitHub/BD_StockEvaluator|file:///app|g" requirements.txt || true && \
            # Create a filtered requirements file that removes GUI/desktop-only and
            # platform-specific packages that commonly fail to install in a slim linux
            # container (Kivy and its deps, PyQt5, MetaTrader5, pywin32, tensorflow, etc.),
            # and skip editable git installs (private repos) that may not resolve cleanly
            # in CI images. Match patterns anywhere on the line (case-insensitive).
            # Also exclude version pins that conflict (e.g. pydantic pin) and heavy GUI/AI helpers
            # like gradio and google-genai which may have transitive constraints.
            grep -vEi "(-e\s+git\+|bd_python_ai|bd-python-ai|pydantic==|gradio|google-genai|openbb(-|_)|kivy|kivy-deps|kivy-examples|kivy-garden|pyqt5|pyqt5-qt5|pyqt5_sip|pyqt5-qt|ta-lib|metatrader5|pywin32|pywin32-ctypes|pypiwin32|tensorflow(-intel)?)" requirements.txt > /tmp/requirements.filtered.txt || true && \
            # Remove any local editable/project lines (file:///app or bd_stockevaluator) so
            # pip doesn't try to resolve the project's own install_requires (which can
            # bring in platform-specific packages). We'll install the local project
            # separately with --no-deps below.
            grep -vEi "(file::///|file:///|bd_stockevaluator|bd-stockevaluator)" /tmp/requirements.filtered.txt > /tmp/requirements.filtered.no_local.txt || true && \
            pip install --upgrade pip && \
            pip install --no-cache-dir -r /tmp/requirements.filtered.no_local.txt && \
            # Finally install the project code itself without its install-time deps
            # to avoid pulling platform-specific packages into the container.
            pip install --no-deps /app; \
        else \
            pip install --upgrade pip && \
            pip install --no-cache-dir -r requirements.docker.txt; \
        fi

EXPOSE 8000

CMD ["uvicorn", "bd_stockevaluator.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
