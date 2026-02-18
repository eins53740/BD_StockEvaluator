"""Tests for the user-features API router (E13, E14, E19, E21, E22)."""

from __future__ import annotations

import io
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from bd_stockevaluator.api.main import app

CLIENT_ID = "test-client-uuid-00001"
HEADERS = {"X-Client-ID": CLIENT_ID}


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Redirect the user features DB to a temp dir for every test."""
    db_path = tmp_path / "user_features.db"
    monkeypatch.setattr(
        "bd_stockevaluator.api.user_features._DB_PATH",
        db_path,
    )
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Auth / header validation
# ---------------------------------------------------------------------------

class TestAnonymousAuth:
    def test_missing_client_id_returns_400(self, client):
        resp = client.get("/user/watchlist")
        assert resp.status_code == 400
        assert "X-Client-ID" in resp.json()["detail"]

    def test_short_client_id_returns_400(self, client):
        resp = client.get("/user/watchlist", headers={"X-Client-ID": "abc"})
        assert resp.status_code == 400

    def test_valid_client_id_accepted(self, client):
        resp = client.get("/user/watchlist", headers=HEADERS)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Watchlist Endpoints (E13)
# ---------------------------------------------------------------------------

class TestWatchlist:
    def test_add_ticker(self, client):
        resp = client.post(
            "/user/watchlist",
            json={"ticker": "AAPL", "channels": ["email"]},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["channels"] == ["email"]

    def test_add_duplicate_returns_409(self, client):
        client.post("/user/watchlist", json={"ticker": "MSFT"}, headers=HEADERS)
        resp = client.post("/user/watchlist", json={"ticker": "MSFT"}, headers=HEADERS)
        assert resp.status_code == 409

    def test_list_watchlist(self, client):
        client.post("/user/watchlist", json={"ticker": "GOOGL"}, headers=HEADERS)
        client.post("/user/watchlist", json={"ticker": "NVDA"}, headers=HEADERS)
        resp = client.get("/user/watchlist", headers=HEADERS)
        assert resp.status_code == 200
        tickers = [e["ticker"] for e in resp.json()]
        assert "GOOGL" in tickers
        assert "NVDA" in tickers

    def test_remove_ticker(self, client):
        client.post("/user/watchlist", json={"ticker": "TSLA"}, headers=HEADERS)
        resp = client.delete("/user/watchlist/TSLA", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"

    def test_remove_nonexistent_returns_404(self, client):
        resp = client.delete("/user/watchlist/ZZZZ", headers=HEADERS)
        assert resp.status_code == 404

    def test_watchlist_scoping(self, client):
        """Different client IDs see different watchlists."""
        client.post("/user/watchlist", json={"ticker": "AAPL"}, headers=HEADERS)
        other = {"X-Client-ID": "other-client-uuid-0002"}
        resp = client.get("/user/watchlist", headers=other)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_add_with_rules(self, client):
        rule = {
            "path": "risk_assessment.overall_risk_score",
            "operator": ">=",
            "value": 70,
            "message": "High risk alert",
        }
        resp = client.post(
            "/user/watchlist",
            json={"ticker": "META", "channels": ["push"], "rules": [rule]},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rules"]) == 1
        assert data["rules"][0]["path"] == "risk_assessment.overall_risk_score"


# ---------------------------------------------------------------------------
# Portfolio Endpoints (E14)
# ---------------------------------------------------------------------------

class TestPortfolio:
    def test_add_holding(self, client):
        resp = client.post(
            "/user/portfolio",
            json={"ticker": "AAPL", "quantity": 10, "buy_price": 150.0},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["quantity"] == 10
        assert data["buy_price"] == 150.0

    def test_list_holdings(self, client):
        client.post(
            "/user/portfolio",
            json={"ticker": "MSFT", "quantity": 5, "buy_price": 300.0},
            headers=HEADERS,
        )
        resp = client.get("/user/portfolio", headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["ticker"] == "MSFT"

    def test_update_holding(self, client):
        add_resp = client.post(
            "/user/portfolio",
            json={"ticker": "GOOG", "quantity": 3, "buy_price": 2800.0},
            headers=HEADERS,
        )
        holding_id = add_resp.json()["id"]
        resp = client.put(
            f"/user/portfolio/{holding_id}",
            json={"quantity": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 5

    def test_update_nonexistent_returns_404(self, client):
        resp = client.put(
            "/user/portfolio/9999",
            json={"quantity": 1},
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_update_no_fields_returns_400(self, client):
        add_resp = client.post(
            "/user/portfolio",
            json={"ticker": "NVDA", "quantity": 2, "buy_price": 800.0},
            headers=HEADERS,
        )
        holding_id = add_resp.json()["id"]
        resp = client.put(
            f"/user/portfolio/{holding_id}",
            json={},
            headers=HEADERS,
        )
        assert resp.status_code == 400

    def test_delete_holding(self, client):
        add_resp = client.post(
            "/user/portfolio",
            json={"ticker": "AMZN", "quantity": 1, "buy_price": 180.0},
            headers=HEADERS,
        )
        holding_id = add_resp.json()["id"]
        resp = client.delete(f"/user/portfolio/{holding_id}", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/user/portfolio/9999", headers=HEADERS)
        assert resp.status_code == 404

    def test_import_csv(self, client):
        csv_content = "ticker,quantity,buy_price,buy_date\nAAPL,10,150.0,2024-01-15\nMSFT,5,300.0,\n"
        resp = client.post(
            "/user/portfolio/import",
            files={"file": ("portfolio.csv", csv_content, "text/csv")},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

        # Verify holdings were created
        list_resp = client.get("/user/portfolio", headers=HEADERS)
        assert len(list_resp.json()) == 2

    def test_import_non_csv_returns_400(self, client):
        resp = client.post(
            "/user/portfolio/import",
            files={"file": ("data.json", "{}", "application/json")},
            headers=HEADERS,
        )
        assert resp.status_code == 400

    def test_portfolio_performance_empty(self, client):
        resp = client.get("/user/portfolio/performance", headers=HEADERS)
        assert resp.status_code == 200
        assert "error" in resp.json()

    @patch("bd_stockevaluator.api.user_features.yf")
    def test_portfolio_performance_with_holdings(self, yf_mock, client):
        # Add a holding first
        client.post(
            "/user/portfolio",
            json={"ticker": "AAPL", "quantity": 10, "buy_price": 150.0},
            headers=HEADERS,
        )

        # Mock yfinance
        mock_ticker = MagicMock()
        mock_ticker.info = {"currentPrice": 180.0}
        yf_mock.Ticker.return_value = mock_ticker

        resp = client.get("/user/portfolio/performance", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cost"] == 1500.0
        assert data["total_value"] == 1800.0
        assert data["total_gain"] == 300.0
        assert len(data["holdings"]) == 1

    def test_portfolio_scoping(self, client):
        """Different client IDs see different portfolios."""
        client.post(
            "/user/portfolio",
            json={"ticker": "AAPL", "quantity": 10, "buy_price": 150.0},
            headers=HEADERS,
        )
        other = {"X-Client-ID": "other-client-uuid-0002"}
        resp = client.get("/user/portfolio", headers=other)
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# ---------------------------------------------------------------------------
# Pattern Recognition Endpoint (E22)
# ---------------------------------------------------------------------------

class TestPatterns:
    @patch("bd_stockevaluator.analysis.epic3.Epic3TechnicalAnalyzer")
    def test_patterns_success(self, mock_analyzer_cls, client):
        import pandas as pd

        mock_instance = MagicMock()
        mock_analyzer_cls.from_ticker.return_value = mock_instance
        mock_instance.detect_price_patterns.return_value = {"double_bottom": True}
        mock_instance.compute_indicator_suite.return_value = {"rsi": 55}
        mock_instance.generate_signal.return_value = {"action": "HOLD", "score": 5}

        # Provide a small dataframe for candlestick detection
        df = pd.DataFrame({
            "Open": [100, 101, 102],
            "High": [105, 106, 107],
            "Low": [98, 99, 100],
            "Close": [103, 104, 105],
        })
        mock_instance._df = df

        resp = client.get("/user/patterns/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "patterns" in data
        assert "candlestick_patterns" in data
        assert "indicators" in data

    def test_patterns_empty_ticker_returns_400(self, client):
        resp = client.get("/user/patterns/%20")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Natural Language Screener Endpoint (E19)
# ---------------------------------------------------------------------------

class TestScreener:
    def test_screener_no_api_key_returns_503(self, client, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        resp = client.post(
            "/user/screen",
            json={"query": "tech stocks with ROE > 20%"},
        )
        assert resp.status_code == 503

    @patch("bd_stockevaluator.api.user_features._build_stock_universe")
    @patch("bd_stockevaluator.analysis.epic8_ai_layer.NaturalLanguageScreener")
    def test_screener_success(self, mock_screener_cls, mock_universe, client, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        mock_universe.return_value = [
            {"ticker": "AAPL", "sector": "Technology", "roe": 0.25},
            {"ticker": "MSFT", "sector": "Technology", "roe": 0.30},
        ]
        mock_instance = MagicMock()
        mock_screener_cls.return_value = mock_instance
        mock_instance.screen.return_value = [
            {"ticker": "MSFT", "score": 0.9},
        ]

        resp = client.post(
            "/user/screen",
            json={"query": "tech stocks with ROE > 20%"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "tech stocks with ROE > 20%"
        assert len(data["results"]) == 1

    @patch("bd_stockevaluator.api.user_features._build_stock_universe")
    def test_screener_empty_universe(self, mock_universe, client, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        mock_universe.return_value = []

        resp = client.post(
            "/user/screen",
            json={"query": "dividend stocks"},
        )
        assert resp.status_code == 200
        assert "No cached stock data" in resp.json()["message"]


# ---------------------------------------------------------------------------
# Sentiment Analysis Endpoint (E21)
# ---------------------------------------------------------------------------

class TestSentiment:
    @patch("bd_stockevaluator.api.user_features.yf")
    def test_sentiment_no_news(self, yf_mock, client):
        mock_ticker = MagicMock()
        mock_ticker.news = []
        yf_mock.Ticker.return_value = mock_ticker

        resp = client.get("/user/sentiment/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["label"] == "Neutral"
        assert data["overall_score"] == 0.5

    @patch("bd_stockevaluator.api.user_features.yf")
    def test_sentiment_with_news_no_api_key(self, yf_mock, client, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        mock_ticker = MagicMock()
        mock_ticker.news = [
            {"title": "Apple beats earnings", "publisher": "Reuters", "link": "https://example.com"},
            {"title": "iPhone sales surge", "publisher": "Bloomberg", "link": "https://example.com"},
        ]
        yf_mock.Ticker.return_value = mock_ticker

        resp = client.get("/user/sentiment/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert len(data["headlines"]) == 2
        # Without API key, default score is 0.5 => Neutral
        assert data["label"] == "Neutral"

    def test_sentiment_empty_ticker_returns_400(self, client):
        resp = client.get("/user/sentiment/%20")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Flask App - HTMX and Search Endpoints (E4)
# ---------------------------------------------------------------------------

class TestFlaskEndpoints:
    @pytest.fixture
    def flask_client(self):
        from bd_stockevaluator.app import app as flask_app
        flask_app.config["TESTING"] = True
        return flask_app.test_client()

    def test_search_empty_query(self, flask_client):
        resp = flask_client.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json == []

    def test_search_returns_matches(self, flask_client):
        resp = flask_client.get("/api/search?q=AAPL")
        assert resp.status_code == 200
        data = resp.json
        assert any(t["ticker"] == "AAPL" for t in data)

    def test_search_case_insensitive_name(self, flask_client):
        resp = flask_client.get("/api/search?q=APPLE")
        assert resp.status_code == 200
        data = resp.json
        assert any(t["ticker"] == "AAPL" for t in data)

    def test_search_limits_results(self, flask_client):
        resp = flask_client.get("/api/search?q=A")
        assert resp.status_code == 200
        assert len(resp.json) <= 8

    @patch("bd_stockevaluator.app.analysis_service")
    def test_evaluate_htmx_endpoint(self, mock_service, flask_client):
        mock_service.analyze.return_value = {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "result": "BUY",
            "path": [],
            "active_links": [],
            "flowchart_definition": "graph TD;",
            "opinion_report": "<p>Test</p>",
            "risk_assessment": {},
            "trend_analysis": {},
            "comparative_analysis": {},
            "dividend_analysis": {},
            "valuation_scorecard": {},
            "profitability_snapshot": {},
            "growth_trends": {},
            "intrinsic_value_models": {},
            "historical_context": {},
            "technical_analysis": {},
            "macro_context": {},
            "metrics": {},
        }
        resp = flask_client.post("/evaluate", data={"ticker": "MSFT"})
        assert resp.status_code == 200

    def test_evaluate_htmx_empty_ticker(self, flask_client):
        resp = flask_client.post("/evaluate", data={"ticker": ""})
        assert resp.status_code == 200
        assert b"Please enter a stock ticker" in resp.data
