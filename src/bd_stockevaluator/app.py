# D:/GitHub/BD_Python_AI/BD_Finance/FlowchartStocks/stock-evaluator/app.py
# 20251507 BDLRA
#
import os
import threading
import atexit
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, render_template, request, url_for

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
load_dotenv(PROJECT_ROOT / ".env", override=False)

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "templates"),
    static_folder=str(PROJECT_ROOT / "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "a-default-secret-key-for-dev-only")

# Reusable service shared with future API backends and the Android client.
analysis_service = StockAnalysisService()
_refresh_thread = None
_refresh_stop_event = threading.Event()


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


start_background_refresh()
atexit.register(stop_background_refresh)


@app.route("/", methods=["GET", "POST"])
def index():
    current_year = datetime.now().year

    if request.method == "POST":
        ticker_symbol = request.form.get("ticker", "").upper().strip()
        if not ticker_symbol:
            flash("Please enter a stock ticker.", "error")
            return render_template("index.html", current_year=current_year)

        try:
            analysis = analysis_service.analyze(ticker_symbol)
            chart = analysis.get("technical_analysis", {}).get("chart", {})
            chart_png = chart.get("png")
            if chart_png:
                chart["png_url"] = url_for(
                    "static",
                    filename=str(chart_png).replace("\\", "/"),
                )
            return render_template("index.html", current_year=current_year, **analysis)
        except Exception as exc:
            # Clear cache to avoid stale errors, then show message to the user.
            if hasattr(get_stock_data, "cache"):
                get_stock_data.cache.clear()
            flash(str(exc), "error")
            return render_template(
                "index.html", current_year=current_year, ticker=ticker_symbol
            )

    return render_template("index.html", current_year=current_year)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
