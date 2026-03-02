# src/bd_stockevaluator/__main__.py
"""
Launches the unified FastAPI application (Flask UI + API on port 8000).

Usage:
    python -m bd_stockevaluator
"""
import os


def main():
    import uvicorn

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    uvicorn.run(
        "bd_stockevaluator.api.main:app",
        host=host,
        port=port,
        reload=debug,
    )


if __name__ == "__main__":
    main()
