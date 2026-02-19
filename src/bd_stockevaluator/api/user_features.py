"""
User-scoped feature endpoints: Watchlist, Portfolio, Screener, Sentiment, Patterns.

Uses anonymous client ID (X-Client-ID header) for per-user scoping without auth.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field

import yfinance as yf

from ..core import StockAnalysisService

_TICKER_RE = re.compile(r"^[A-Z0-9.\-^]{1,12}$")
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
_ALLOWED_HOLDING_COLUMNS = {"quantity", "buy_price", "buy_date", "currency"}

router = APIRouter()

# Database path (same directory as the data pipeline DB).
_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "user_features.db"
_analysis_service = StockAnalysisService()


def _get_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_user_schema(conn)
    return conn


def _ensure_user_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            channels TEXT NOT NULL DEFAULT '["email"]',
            rules TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            UNIQUE(client_id, ticker)
        );

        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            quantity REAL NOT NULL,
            buy_price REAL NOT NULL,
            buy_date TEXT,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_watchlist_client ON watchlist(client_id);
        CREATE INDEX IF NOT EXISTS idx_portfolio_client ON portfolio_holdings(client_id);
        """
    )


def _get_client_id(x_client_id: Optional[str] = Header(None)) -> str:
    """Extract or generate a client ID for anonymous user scoping."""
    if x_client_id and len(x_client_id) >= 8:
        return x_client_id
    raise HTTPException(
        status_code=400,
        detail="X-Client-ID header is required. Generate a UUID on the client and send it with each request.",
    )


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class WatchlistRule(BaseModel):
    path: str = Field(..., description="Dot-path into analysis payload, e.g. 'risk_assessment.overall_risk_score'")
    operator: str = Field(..., description="Comparison operator: >=, >, <=, <, ==, !=")
    value: float
    message: str = ""


class WatchlistAddRequest(BaseModel):
    ticker: str
    channels: List[str] = ["email"]
    rules: List[WatchlistRule] = []


class WatchlistEntry(BaseModel):
    id: int
    ticker: str
    channels: List[str]
    rules: List[WatchlistRule]
    created_at: str


class PortfolioAddRequest(BaseModel):
    ticker: str
    quantity: float
    buy_price: float = Field(..., gt=0)
    buy_date: Optional[str] = None
    currency: str = "USD"


class PortfolioUpdateRequest(BaseModel):
    quantity: Optional[float] = None
    buy_price: Optional[float] = None
    buy_date: Optional[str] = None
    currency: Optional[str] = None


class PortfolioHolding(BaseModel):
    id: int
    ticker: str
    quantity: float
    buy_price: float
    buy_date: Optional[str]
    currency: str
    created_at: str


class ScreenRequest(BaseModel):
    query: str = Field(..., description="Natural language screening query, e.g. 'tech stocks with ROE > 20%'")


class SentimentResult(BaseModel):
    ticker: str
    overall_score: float
    label: str
    headlines: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Watchlist Endpoints (E13)
# ---------------------------------------------------------------------------

def _validate_ticker(raw: str) -> str:
    """Validate and normalize a ticker symbol."""
    ticker = raw.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required.")
    if not _TICKER_RE.fullmatch(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol format.")
    return ticker


@router.post("/watchlist", response_model=WatchlistEntry)
def add_to_watchlist(req: WatchlistAddRequest, client_id: str = Depends(_get_client_id)):
    ticker = _validate_ticker(req.ticker)
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required.")
    now = datetime.now(timezone.utc).isoformat()
    db = _get_db()
    try:
        db.execute(
            "INSERT INTO watchlist (client_id, ticker, channels, rules, created_at) VALUES (?, ?, ?, ?, ?)",
            (client_id, ticker, json.dumps(req.channels), json.dumps([r.model_dump() for r in req.rules]), now),
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM watchlist WHERE client_id = ? AND ticker = ?", (client_id, ticker)
        ).fetchone()
        return WatchlistEntry(
            id=row["id"], ticker=row["ticker"],
            channels=json.loads(row["channels"]),
            rules=[WatchlistRule(**r) for r in json.loads(row["rules"])],
            created_at=row["created_at"],
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"{ticker} is already in your watchlist.")
    finally:
        db.close()


@router.get("/watchlist", response_model=List[WatchlistEntry])
def list_watchlist(client_id: str = Depends(_get_client_id)):
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT * FROM watchlist WHERE client_id = ? ORDER BY created_at DESC", (client_id,)
        ).fetchall()
        return [
            WatchlistEntry(
                id=r["id"], ticker=r["ticker"],
                channels=json.loads(r["channels"]),
                rules=[WatchlistRule(**rule) for rule in json.loads(r["rules"])],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        db.close()


@router.delete("/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, client_id: str = Depends(_get_client_id)):
    db = _get_db()
    try:
        result = db.execute(
            "DELETE FROM watchlist WHERE client_id = ? AND ticker = ?", (client_id, ticker.upper())
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"{ticker.upper()} not found in watchlist.")
        return {"status": "removed", "ticker": ticker.upper()}
    finally:
        db.close()


@router.post("/watchlist/evaluate")
def evaluate_watchlist(client_id: str = Depends(_get_client_id)):
    """Run analysis on all watchlist tickers and evaluate alert rules."""
    db = _get_db()
    try:
        rows = db.execute("SELECT * FROM watchlist WHERE client_id = ?", (client_id,)).fetchall()
    finally:
        db.close()

    if not rows:
        return {"alerts": [], "message": "Watchlist is empty."}

    from ..core.watchlist import WatchlistAlertEngine

    watchlist_entries = []
    tickers = set()
    for r in rows:
        entry = {
            "ticker": r["ticker"],
            "channels": json.loads(r["channels"]),
            "rules": json.loads(r["rules"]),
        }
        watchlist_entries.append(entry)
        tickers.add(r["ticker"])

    # Run analysis for each ticker
    analysis_results = {}
    for ticker in tickers:
        try:
            analysis_results[ticker] = _analysis_service.analyze(ticker, include_opinion=False)
        except Exception:
            continue

    engine = WatchlistAlertEngine()
    alerts = engine.evaluate(watchlist_entries, analysis_results)

    return {
        "alerts": [
            {
                "ticker": a.ticker,
                "triggered_rules": list(a.triggered_rules),
                "channels": list(a.channels),
            }
            for a in alerts
        ],
        "tickers_analyzed": len(analysis_results),
    }


# ---------------------------------------------------------------------------
# Portfolio Endpoints (E14)
# ---------------------------------------------------------------------------

@router.post("/portfolio", response_model=PortfolioHolding)
def add_holding(req: PortfolioAddRequest, client_id: str = Depends(_get_client_id)):
    ticker = _validate_ticker(req.ticker)
    if not ticker or req.quantity <= 0:
        raise HTTPException(status_code=400, detail="Valid ticker and positive quantity required.")
    now = datetime.now(timezone.utc).isoformat()
    db = _get_db()
    try:
        db.execute(
            "INSERT INTO portfolio_holdings (client_id, ticker, quantity, buy_price, buy_date, currency, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (client_id, ticker, req.quantity, req.buy_price, req.buy_date, req.currency, now, now),
        )
        db.commit()
        row_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return PortfolioHolding(
            id=row_id, ticker=ticker, quantity=req.quantity,
            buy_price=req.buy_price, buy_date=req.buy_date,
            currency=req.currency, created_at=now,
        )
    finally:
        db.close()


@router.get("/portfolio", response_model=List[PortfolioHolding])
def list_holdings(client_id: str = Depends(_get_client_id)):
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT * FROM portfolio_holdings WHERE client_id = ? ORDER BY created_at DESC", (client_id,)
        ).fetchall()
        return [
            PortfolioHolding(
                id=r["id"], ticker=r["ticker"], quantity=r["quantity"],
                buy_price=r["buy_price"], buy_date=r["buy_date"],
                currency=r["currency"], created_at=r["created_at"],
            )
            for r in rows
        ]
    finally:
        db.close()


@router.put("/portfolio/{holding_id}", response_model=PortfolioHolding)
def update_holding(holding_id: int, req: PortfolioUpdateRequest, client_id: str = Depends(_get_client_id)):
    db = _get_db()
    try:
        existing = db.execute(
            "SELECT * FROM portfolio_holdings WHERE id = ? AND client_id = ?", (holding_id, client_id)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Holding not found.")

        updates = {}
        if req.quantity is not None:
            updates["quantity"] = req.quantity
        if req.buy_price is not None:
            updates["buy_price"] = req.buy_price
        if req.buy_date is not None:
            updates["buy_date"] = req.buy_date
        if req.currency is not None:
            updates["currency"] = req.currency

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update.")

        # Allowlist column names to prevent SQL injection via dynamic SET clause
        invalid_cols = set(updates.keys()) - _ALLOWED_HOLDING_COLUMNS
        if invalid_cols:
            raise HTTPException(status_code=400, detail=f"Invalid fields: {invalid_cols}")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [holding_id, client_id]
        db.execute(f"UPDATE portfolio_holdings SET {set_clause} WHERE id = ? AND client_id = ?", values)
        db.commit()

        row = db.execute("SELECT * FROM portfolio_holdings WHERE id = ?", (holding_id,)).fetchone()
        return PortfolioHolding(
            id=row["id"], ticker=row["ticker"], quantity=row["quantity"],
            buy_price=row["buy_price"], buy_date=row["buy_date"],
            currency=row["currency"], created_at=row["created_at"],
        )
    finally:
        db.close()


@router.delete("/portfolio/{holding_id}")
def remove_holding(holding_id: int, client_id: str = Depends(_get_client_id)):
    db = _get_db()
    try:
        result = db.execute(
            "DELETE FROM portfolio_holdings WHERE id = ? AND client_id = ?", (holding_id, client_id)
        )
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Holding not found.")
        return {"status": "removed", "id": holding_id}
    finally:
        db.close()


@router.post("/portfolio/import")
def import_portfolio_csv(
    file: UploadFile = File(...),
    client_id: str = Depends(_get_client_id),
):
    """Import holdings from a CSV file. Expected columns: ticker, quantity, buy_price, buy_date (optional), currency (optional)."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw_bytes = file.file.read()
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    content = raw_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    now = datetime.now(timezone.utc).isoformat()
    db = _get_db()
    imported = 0
    try:
        for row in reader:
            ticker = (row.get("ticker") or "").upper().strip()
            quantity = float(row.get("quantity") or 0)
            buy_price = float(row.get("buy_price") or row.get("avg_cost") or 0)
            buy_date = row.get("buy_date") or row.get("date") or None
            currency = row.get("currency", "USD").upper().strip()

            if not ticker or quantity <= 0:
                continue

            db.execute(
                "INSERT INTO portfolio_holdings (client_id, ticker, quantity, buy_price, buy_date, currency, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (client_id, ticker, quantity, buy_price, buy_date, currency, now, now),
            )
            imported += 1
        db.commit()
    finally:
        db.close()

    return {"status": "imported", "count": imported}


@router.get("/portfolio/performance")
def portfolio_performance(client_id: str = Depends(_get_client_id)):
    """Compute portfolio snapshot with live prices and performance metrics."""
    db = _get_db()
    try:
        rows = db.execute(
            "SELECT * FROM portfolio_holdings WHERE client_id = ?", (client_id,)
        ).fetchall()
    finally:
        db.close()

    if not rows:
        return {"error": "No holdings found. Add stocks to your portfolio first."}

    holdings = []
    total_cost = 0.0
    total_value = 0.0

    for r in rows:
        ticker = r["ticker"]
        qty = r["quantity"]
        cost = r["buy_price"] * qty
        total_cost += cost
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or r["buy_price"]
        except Exception:
            price = r["buy_price"]

        value = price * qty
        total_value += value
        gain = value - cost
        holdings.append({
            "ticker": ticker,
            "quantity": qty,
            "buy_price": r["buy_price"],
            "current_price": round(price, 2),
            "cost_basis": round(cost, 2),
            "market_value": round(value, 2),
            "gain": round(gain, 2),
            "gain_pct": round((gain / cost) * 100, 2) if cost else 0,
        })

    total_gain = total_value - total_cost
    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_pct": round((total_gain / total_cost) * 100, 2) if total_cost else 0,
        "holdings": holdings,
    }


# ---------------------------------------------------------------------------
# Pattern Recognition Endpoint (E22)
# ---------------------------------------------------------------------------

@router.get("/patterns/{ticker}")
def get_patterns(ticker: str):
    """Return technical patterns including candlestick and chart patterns."""
    ticker = _validate_ticker(ticker)

    try:
        from ..analysis.epic3 import Epic3TechnicalAnalyzer

        analyzer = Epic3TechnicalAnalyzer.from_ticker(ticker, period="1y")
        patterns = analyzer.detect_price_patterns()
        indicators = analyzer.compute_indicator_suite()
        signal = analyzer.generate_signal(verdict="N/A")

        # Add candlestick patterns
        candlestick_patterns = _detect_candlestick_patterns(analyzer)

        return {
            "ticker": ticker,
            "patterns": patterns,
            "candlestick_patterns": candlestick_patterns,
            "indicators": indicators,
            "signal": signal,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _detect_candlestick_patterns(analyzer) -> List[Dict[str, Any]]:
    """Detect common candlestick patterns from OHLC data."""
    df = analyzer._df
    if df is None or len(df) < 3:
        return []

    patterns_found = []
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values  # noqa: E741
    c = df["Close"].values

    for i in range(2, len(df)):
        body = abs(c[i] - o[i])
        full_range = h[i] - l[i]
        if full_range == 0:
            continue

        body_ratio = body / full_range
        upper_shadow = h[i] - max(o[i], c[i])
        lower_shadow = min(o[i], c[i]) - l[i]
        is_bullish = c[i] > o[i]
        prev_body = abs(c[i - 1] - o[i - 1])

        # Doji: very small body relative to range
        if body_ratio < 0.1:
            patterns_found.append({"index": i, "pattern": "Doji", "signal": "neutral"})

        # Hammer: small body at top, long lower shadow (bullish reversal)
        elif body_ratio < 0.35 and lower_shadow > 2 * body and upper_shadow < body:
            patterns_found.append({"index": i, "pattern": "Hammer", "signal": "bullish"})

        # Shooting Star: small body at bottom, long upper shadow (bearish reversal)
        elif body_ratio < 0.35 and upper_shadow > 2 * body and lower_shadow < body:
            patterns_found.append({"index": i, "pattern": "Shooting Star", "signal": "bearish"})

        # Bullish Engulfing
        if (
            i >= 1
            and c[i - 1] < o[i - 1]  # prev was bearish
            and is_bullish  # current is bullish
            and o[i] <= c[i - 1]  # opens at or below prev close
            and c[i] >= o[i - 1]  # closes at or above prev open
            and body > prev_body
        ):
            patterns_found.append({"index": i, "pattern": "Bullish Engulfing", "signal": "bullish"})

        # Bearish Engulfing
        if (
            i >= 1
            and c[i - 1] > o[i - 1]  # prev was bullish
            and not is_bullish  # current is bearish
            and o[i] >= c[i - 1]  # opens at or above prev close
            and c[i] <= o[i - 1]  # closes at or below prev open
            and body > prev_body
        ):
            patterns_found.append({"index": i, "pattern": "Bearish Engulfing", "signal": "bearish"})

    # Return only the most recent patterns (last 20 trading days)
    recent = [p for p in patterns_found if p["index"] >= len(df) - 20]
    return recent[-10:]  # cap at 10 most recent


# ---------------------------------------------------------------------------
# Natural Language Screener Endpoint (E19)
# ---------------------------------------------------------------------------

@router.post("/screen")
def screen_stocks(req: ScreenRequest):
    """Screen stocks using natural language query."""
    import os

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured. Screener requires an LLM API key.")

    try:
        from ..analysis.epic8_ai_layer import NaturalLanguageScreener

        screener = NaturalLanguageScreener(api_key)

        # Build stock universe from cached fundamentals
        stock_universe = _build_stock_universe()
        if not stock_universe:
            return {"query": req.query, "results": [], "message": "No cached stock data available. Evaluate some tickers first."}

        results = screener.screen(req.query, stock_universe)
        return {"query": req.query, "results": results[:20], "total_universe": len(stock_universe)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _build_stock_universe() -> List[Dict[str, Any]]:
    """Build a list of stock dicts from cached fundamentals in the data pipeline DB."""
    db_path = Path(__file__).resolve().parents[3] / "data" / "stocks.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT ticker, raw_json FROM fundamentals_snapshot").fetchall()
        stocks = []
        for r in rows:
            try:
                data = json.loads(r["raw_json"])
                stock = {
                    "ticker": r["ticker"],
                    "company_name": data.get("longName") or data.get("shortName") or r["ticker"],
                    "sector": data.get("sector", ""),
                    "industry": data.get("industry", ""),
                    "market_cap": data.get("marketCap", 0),
                    "pe": data.get("trailingPE"),
                    "roe": data.get("returnOnEquity"),
                    "debt_to_equity": data.get("debtToEquity"),
                    "revenue_growth": data.get("revenueGrowth"),
                    "profit_margin": data.get("profitMargins"),
                    "dividend_yield": data.get("dividendYield"),
                    "current_price": data.get("currentPrice") or data.get("regularMarketPrice"),
                }
                stocks.append(stock)
            except (json.JSONDecodeError, KeyError):
                continue
        return stocks
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Sentiment Analysis Endpoint (E21)
# ---------------------------------------------------------------------------

@router.get("/sentiment/{ticker}", response_model=SentimentResult)
def get_sentiment(ticker: str):
    """Fetch recent news headlines and score their sentiment."""
    ticker = _validate_ticker(ticker)

    try:
        stock = yf.Ticker(ticker)
        news = stock.news or []
    except Exception:
        news = []

    if not news:
        return SentimentResult(
            ticker=ticker, overall_score=0.5, label="Neutral",
            headlines=[{"title": "No recent news available", "score": 0.5}],
        )

    # Score each headline
    import os

    api_key = os.environ.get("GROQ_API_KEY", "")
    scored_headlines = []

    for article in news[:10]:
        title = article.get("title") or article.get("content", {}).get("title", "")
        if not title:
            continue
        score = 0.5  # default neutral
        if api_key:
            try:
                from ..analysis.epic8_ai_layer import PredictiveModel

                model = PredictiveModel(api_key)
                score = model.get_sentiment_score(title)
            except Exception:
                pass
        scored_headlines.append({
            "title": title,
            "score": round(score, 3),
            "publisher": article.get("publisher") or article.get("content", {}).get("provider", {}).get("displayName", ""),
            "link": article.get("link") or article.get("content", {}).get("clickThroughUrl", {}).get("url", ""),
        })

    if scored_headlines:
        avg_score = sum(h["score"] for h in scored_headlines) / len(scored_headlines)
    else:
        avg_score = 0.5

    if avg_score >= 0.65:
        label = "Bullish"
    elif avg_score <= 0.35:
        label = "Bearish"
    else:
        label = "Neutral"

    return SentimentResult(
        ticker=ticker,
        overall_score=round(avg_score, 3),
        label=label,
        headlines=scored_headlines,
    )
