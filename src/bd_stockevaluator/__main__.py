# src/bd_stockevaluator/__main__.py
"""
Enables running the Flask application as a module.
`python -m bd_stockevaluator`
"""
import os

from .app import app


def main():
    """
    Main entry point to run the Flask web application.
    For production, use gunicorn/uvicorn instead of app.run().
    """
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)


if __name__ == "__main__":
    main()
