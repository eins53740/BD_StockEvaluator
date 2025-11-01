"""Application entrypoint for ``python -m app``.

The Docker image starts the API by executing this module, which in turn
launches Uvicorn pointing at the FastAPI application defined in
``bd_stockevaluator.api.main``.
"""

from __future__ import annotations

import os

import uvicorn


def _int_from_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> None:
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = _int_from_env("APP_PORT", 8000)
    workers = _int_from_env("APP_WORKERS", 1)

    uvicorn.run(
        "bd_stockevaluator.api.main:app",
        host=host,
        port=port,
        reload=False,
        factory=False,
        workers=workers,
    )


if __name__ == "__main__":  # pragma: no cover - invoked via python -m app
    main()
