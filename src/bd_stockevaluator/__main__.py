# src/bd_stockevaluator/__main__.py
"""
Enables running the Flask application as a module.
`python -m bd_stockevaluator`
"""
from .app import app


def main():
    """
    Main entry point to run the Flask web application.
    It respects the debug flag and other settings from environment variables.
    """
    # In app.py, app.run is called with debug=True.
    # We will do the same here for consistency when running as a module.
    # For a production deployment, a proper WSGI server like gunicorn or uvicorn
    # should be used instead of app.run().
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
