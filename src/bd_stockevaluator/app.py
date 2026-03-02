# D:/GitHub/BD_Python_AI/BD_Finance/FlowchartStocks/stock-evaluator/app.py
# 20251507 BDLRA
#
import html
import os
import re
import threading
import atexit
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, render_template, request, url_for

try:
    # Preferred path when executed as part of the installed package.
    from .core import StockAnalysisService, get_stock_data, refresh_macro_snapshot
    from .core.service import SCHEDULER_HOOKS
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys
    from pathlib import Path

    package_root = Path(__file__).resolve().parent
    src_root = package_root.parent
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from bd_stockevaluator.core import (
        StockAnalysisService,
        get_stock_data,
        refresh_macro_snapshot,
    )
    from bd_stockevaluator.core.service import SCHEDULER_HOOKS

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = PACKAGE_ROOT / "templates"
STATIC_DIR = PACKAGE_ROOT / "static"
load_dotenv(PROJECT_ROOT / ".env", override=False)

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
_flask_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
if _flask_debug:
    app.secret_key = os.environ.get("SECRET_KEY", "a-default-secret-key-for-dev-only")
else:
    _secret = os.environ.get("SECRET_KEY", "")
    if not _secret:
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production. "
            "Set FLASK_DEBUG=1 to use a default key for development."
        )
    app.secret_key = _secret

# Reusable service shared with future API backends and the Android client.
analysis_service = StockAnalysisService()
_refresh_thread = None
_refresh_stop_event = threading.Event()

# Common ticker list for autocomplete (loaded once).
_POPULAR_TICKERS = [
    {"ticker": "AAPL", "name": "Apple Inc."},
    {"ticker": "MSFT", "name": "Microsoft Corporation"},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "AMZN", "name": "Amazon.com Inc."},
    {"ticker": "NVDA", "name": "NVIDIA Corporation"},
    {"ticker": "META", "name": "Meta Platforms Inc."},
    {"ticker": "TSLA", "name": "Tesla Inc."},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway Inc."},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co."},
    {"ticker": "V", "name": "Visa Inc."},
    {"ticker": "JNJ", "name": "Johnson & Johnson"},
    {"ticker": "WMT", "name": "Walmart Inc."},
    {"ticker": "PG", "name": "Procter & Gamble Co."},
    {"ticker": "MA", "name": "Mastercard Inc."},
    {"ticker": "UNH", "name": "UnitedHealth Group Inc."},
    {"ticker": "HD", "name": "The Home Depot Inc."},
    {"ticker": "DIS", "name": "The Walt Disney Co."},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc."},
    {"ticker": "NFLX", "name": "Netflix Inc."},
    {"ticker": "ADBE", "name": "Adobe Inc."},
    {"ticker": "CRM", "name": "Salesforce Inc."},
    {"ticker": "AMD", "name": "Advanced Micro Devices Inc."},
    {"ticker": "INTC", "name": "Intel Corporation"},
    {"ticker": "CSCO", "name": "Cisco Systems Inc."},
    {"ticker": "PEP", "name": "PepsiCo Inc."},
    {"ticker": "KO", "name": "The Coca-Cola Co."},
    {"ticker": "COST", "name": "Costco Wholesale Corp."},
    {"ticker": "AVGO", "name": "Broadcom Inc."},
    {"ticker": "T", "name": "AT&T Inc."},
    {"ticker": "VZ", "name": "Verizon Communications Inc."},
    {"ticker": "NKE", "name": "Nike Inc."},
    {"ticker": "MRK", "name": "Merck & Co. Inc."},
    {"ticker": "PFE", "name": "Pfizer Inc."},
    {"ticker": "ABBV", "name": "AbbVie Inc."},
    {"ticker": "XOM", "name": "Exxon Mobil Corp."},
    {"ticker": "CVX", "name": "Chevron Corp."},
    {"ticker": "BA", "name": "The Boeing Co."},
    {"ticker": "CAT", "name": "Caterpillar Inc."},
    {"ticker": "GS", "name": "Goldman Sachs Group Inc."},
    {"ticker": "IBM", "name": "International Business Machines"},
    {"ticker": "QCOM", "name": "Qualcomm Inc."},
    {"ticker": "TXN", "name": "Texas Instruments Inc."},
    {"ticker": "LOW", "name": "Lowe's Companies Inc."},
    {"ticker": "SBUX", "name": "Starbucks Corp."},
    {"ticker": "INTU", "name": "Intuit Inc."},
    {"ticker": "AMAT", "name": "Applied Materials Inc."},
    {"ticker": "GE", "name": "GE Aerospace"},
    {"ticker": "ISRG", "name": "Intuitive Surgical Inc."},
    {"ticker": "NOW", "name": "ServiceNow Inc."},
    {"ticker": "BKNG", "name": "Booking Holdings Inc."},
]


def _background_worker(tickers, interval_minutes):
    interval_seconds = max(60, int(interval_minutes) * 60)
    app.logger.info(
        "Starting background refresh for %s (interval %s minutes)",
        tickers,
        interval_minutes,
    )
    # Initial warm-up pass
    try:
        refresh_macro_snapshot()
    except Exception as exc:
        app.logger.warning("Initial macro refresh failed: %s", exc)
    for ticker in tickers:
        try:
            SCHEDULER_HOOKS.client.sync_ticker(ticker, categories=None)
        except Exception as exc:
            app.logger.warning("Initial refresh failed for %s: %s", ticker, exc)
    while not _refresh_stop_event.wait(interval_seconds):
        try:
            refresh_macro_snapshot()
        except Exception as exc:
            app.logger.debug("Macro refresh skipped: %s", exc)
        for ticker in tickers:
            if _refresh_stop_event.is_set():
                break
            try:
                SCHEDULER_HOOKS.client.sync_ticker(ticker, categories=None)
                app.logger.debug("Refreshed %s via background scheduler", ticker)
            except Exception as exc:
                app.logger.warning("Scheduled refresh failed for %s: %s", ticker, exc)


def start_background_refresh():
    global _refresh_thread
    if _refresh_thread and _refresh_thread.is_alive():
        return
    enabled = os.environ.get("ENABLE_BACKGROUND_REFRESH", "false").lower() == "true"
    if not enabled:
        return
    raw_tickers = os.environ.get("REFRESH_TICKERS", "")
    tickers = [
        symbol.strip().upper() for symbol in raw_tickers.split(",") if symbol.strip()
    ]
    if not tickers:
        app.logger.warning(
            "ENABLE_BACKGROUND_REFRESH is true but REFRESH_TICKERS is empty. Skipping scheduler bootstrap."
        )
        return
    interval = int(os.environ.get("REFRESH_INTERVAL_MINUTES", "180") or "180")
    _refresh_thread = threading.Thread(
        target=_background_worker,
        args=(tickers, interval),
        name="bd-finance-refresh",
        daemon=True,
    )
    _refresh_thread.start()


def stop_background_refresh():
    _refresh_stop_event.set()
    if _refresh_thread and _refresh_thread.is_alive():
        _refresh_thread.join(timeout=2)


# NOTE: With multiple gunicorn workers, each worker spawns its own refresh
# thread. Currently safe because ENABLE_BACKGROUND_REFRESH defaults to false.
# If enabled with >1 worker, replace with a proper task queue (e.g. Celery).
start_background_refresh()
atexit.register(stop_background_refresh)


def _prepare_chart_url(analysis):
    """Resolve the technical chart PNG path to a URL for the template."""
    chart = analysis.get("technical_analysis", {}).get("chart", {})
    chart_png = chart.get("png")
    if chart_png:
        chart["png_url"] = url_for(
            "static",
            filename=str(chart_png).replace("\\", "/"),
        )


@app.route("/", methods=["GET", "POST"])
def index():
    current_year = datetime.now().year

    if request.method == "POST":
        ticker_symbol = request.form.get("ticker", "").upper().strip()
        if not ticker_symbol:
            flash("Please enter a stock ticker.", "error")
            return render_template("index.html", current_year=current_year)
        if not _TICKER_RE.fullmatch(ticker_symbol):
            flash("Invalid ticker symbol format.", "error")
            return render_template("index.html", current_year=current_year)

        try:
            analysis = analysis_service.analyze(ticker_symbol)
            _prepare_chart_url(analysis)
            return render_template("index.html", current_year=current_year, **analysis)
        except Exception as exc:
            if hasattr(get_stock_data, "cache"):
                get_stock_data.cache.clear()
            flash(str(exc), "error")
            return render_template(
                "index.html", current_year=current_year, ticker=ticker_symbol
            )

    return render_template("index.html", current_year=current_year)


@app.route("/evaluate", methods=["POST"])
def evaluate_htmx():
    """HTMX endpoint: returns the results partial HTML fragment."""
    ticker_symbol = request.form.get("ticker", "").upper().strip()
    if not ticker_symbol:
        return '<div class="flash-error" role="alert">Please enter a stock ticker.</div>'
    if not _TICKER_RE.fullmatch(ticker_symbol):
        return '<div class="flash-error" role="alert">Invalid ticker symbol format.</div>'

    try:
        analysis = analysis_service.analyze(ticker_symbol)
        _prepare_chart_url(analysis)
        return render_template("partials/_results.html", **analysis)
    except Exception as exc:
        if hasattr(get_stock_data, "cache"):
            get_stock_data.cache.clear()
        return f'<div class="flash-error" role="alert">{html.escape(str(exc))}</div>'


@app.route("/api/search")
def search_tickers():
    """Autocomplete endpoint: returns JSON list of matching tickers."""
    query = request.args.get("q", "").upper().strip()
    if not query:
        return jsonify([])

    matches = [
        t
        for t in _POPULAR_TICKERS
        if query in t["ticker"] or query in t["name"].upper()
    ]
    return jsonify(matches[:8])


_TICKER_RE = re.compile(r"^[A-Z0-9.\-^]{1,12}$")

if __name__ == "__main__":
    # Deprecated: use `uvicorn bd_stockevaluator.api.main:app` instead.
    # This standalone mode is kept for quick local debugging only.
    app.run(host="0.0.0.0", port=8000, debug=_flask_debug)
