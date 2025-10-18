from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import MagicMock

import pytest

from bd_stockevaluator.core.data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
    SchedulerHooks,
    SQLiteDataStore,
)


class StubProvider:
    """Deterministic provider used in tests to simulate external data sources."""

    def __init__(self, name: str, payloads: Optional[Dict[str, Dict]] = None) -> None:
        self.name = name
        self._payloads = payloads or {}
        self.fetch_invocations: list[str] = []

    def fetch(self, ticker: str) -> Dict[str, Dict]:
        self.fetch_invocations.append(ticker)
        return copy.deepcopy(self._payloads)


def build_client(store: SQLiteDataStore, providers: Dict[str, StubProvider]) -> MultiSourceDataClient:
    precedence = {
        "prices": ["fmp", "yahoo", "alpha"],
        "fundamentals": ["fmp", "finnhub", "alpha", "yahoo"],
        "dividends": ["yahoo", "fmp"],
        "profile": ["fmp", "yahoo"],
        "exchange_rates": ["fmp", "alpha", "yahoo"],
        "history": ["fmp", "finnhub"],
        "price_history": ["fmp", "yahoo"],
        "price_history": ["fmp", "yahoo"],
    }

    converter = CurrencyConverter({"USD": 1.0, "GBP": 1.25, "EUR": 1.08})
    return MultiSourceDataClient(
        store=store,
        converter=converter,
        providers=providers,
        precedence=precedence,
    )


def test_multi_source_syncs_and_persists(tmp_path):
    store = SQLiteDataStore(tmp_path / "stocks.db")

    providers = {
        "yahoo": StubProvider(
            "yahoo",
            {
                "prices": {
                    "currency": "USD",
                    "close": 150.0,
                    "previous_close": 148.0,
                    "open": 149.5,
                },
                "dividends": {
                    "forward_yield": 0.015,
                    "payout_ratio": 0.34,
                },
                "profile": {
                    "name": "Acme Corp",
                    "sector": "Industrials",
                    "industry": "Aerospace",
                },
            },
        ),
        "fmp": StubProvider(
            "fmp",
            {
                "fundamentals": {
                    "currency": "GBP",
                    "eps": 5.5,
                    "pe": 22.0,
                    "peg": 1.6,
                    "ev_to_ebit": 12.0,
                    "pb": 3.2,
                    "fcf_yield": 0.045,
                    "revenue_growth": 0.12,
                    "profit_margins": 0.18,
                    "roe": 0.22,
                    "debt_to_equity": 0.4,
                    "quick_ratio": 1.8,
                },
                "profile": {
                    "name": "Acme Aviation PLC",
                    "exchange": "LSE",
                    "sector": "Industrials",
                    "industry": "Aerospace & Defense",
                },
                "exchange_rates": {
                    "USD": 1.0,
                    "GBP": 1.25,
                    "EUR": 1.08,
                },
                "history": [
                    {
                        "period": "FY2023",
                        "currency": "GBP",
                        "eps": 5.0,
                        "pe": 21.0,
                        "peg": 1.7,
                        "ev_to_ebit": 11.5,
                        "pb": 3.0,
                        "fcf_yield": 0.043,
                    }
                ],
                "prices": {
                    "currency": "USD",
                    "close": 150.0,
                    "previous_close": 150.5,
                    "open": 150.5,
                },
                "price_history": [
                    {
                        "date": "2024-01-08",
                        "open": 146.0,
                        "high": 152.0,
                        "low": 145.5,
                        "close": 150.5,
                        "volume": 1250000,
                    },
                    {
                        "date": "2024-01-09",
                        "open": 150.5,
                        "high": 151.0,
                        "low": 148.5,
                        "close": 150.0,
                        "volume": 980000,
                    },
                ],
            },
        ),
        "alpha": StubProvider(
            "alpha",
            {
                "prices": {
                    "currency": "USD",
                    "close": 151.0,
                }
            },
        ),
        "finnhub": StubProvider("finnhub", {}),
    }

    client = build_client(store, providers)
    as_of = datetime(2024, 1, 10, 12, tzinfo=timezone.utc)

    info = client.sync_ticker("ACME", as_of=as_of)
    assert info["ticker"] == "ACME"
    assert info["regularMarketPrice"] == pytest.approx(150.0)
    assert info["regularMarketPriceEUR"] == pytest.approx(138.8889, rel=1e-4)
    assert info["trailingPE"] == pytest.approx(22.0)
    assert info["returnOnEquity"] == pytest.approx(0.22)
    assert info["profitMargins"] == pytest.approx(0.18)
    assert info["dividendYield"] == pytest.approx(0.015)
    assert info["data_providers"]["fundamentals"] == "fmp"
    assert info["data_providers"]["prices"] == "fmp"
    assert info["data_providers"]["history"] == "fmp"
    assert info["data_providers"]["price_history"] == "fmp"

    price_history = info.get("priceHistory")
    assert price_history
    assert price_history[-1]["close"] == pytest.approx(150.0)

    historical = info.get("historicalMetrics")
    assert historical
    assert historical[0]["period"] == "FY2023"

    snapshot = store.load_latest_snapshot("ACME")
    assert snapshot["provider"] == "fmp"
    assert snapshot["currency"] == "GBP"
    assert snapshot["eps"] == pytest.approx(5.5)
    assert snapshot["eps_usd"] == pytest.approx(6.875)
    assert snapshot["eps_eur"] == pytest.approx(6.3657, rel=1e-4)
    assert snapshot["fcf_yield"] == pytest.approx(0.045)

    history = store.load_history("ACME")
    assert history
    assert history[0]["period"] == "FY2023"
    assert history[0]["provider"] == "fmp"

    price = store.load_latest_price("ACME")
    assert price["provider"] == "fmp"
    assert price["currency"] == "USD"
    assert price["close"] == pytest.approx(150.0)
    assert price["close_eur"] == pytest.approx(138.8889, rel=1e-4)

    meta = store.load_provider_meta("fmp", "fundamentals")
    assert meta["last_success"] is not None
    alpha_meta = store.load_provider_meta("alpha", "fundamentals")
    assert alpha_meta["provider"] == "alpha"


def test_sync_ticker_falls_back_to_next_provider(tmp_path):
    store = SQLiteDataStore(tmp_path / "fallback.db")

    providers = {
        "yahoo": StubProvider(
            "yahoo",
            {
                "prices": {
                    "currency": "USD",
                    "close": 90.0,
                },
                "dividends": {
                    "forward_yield": 0.02,
                    "payout_ratio": 0.4,
                },
            },
        ),
        "fmp": StubProvider(
            "fmp",
            {
                "fundamentals": None,
                "exchange_rates": {
                    "USD": 1.0,
                    "EUR": 1.08,
                },
            },
        ),
        "finnhub": StubProvider(
            "finnhub",
            {
                "fundamentals": {
                    "currency": "USD",
                    "eps": 3.0,
                    "pe": 18.0,
                    "peg": 1.4,
                    "ev_to_ebit": 9.5,
                    "pb": 2.1,
                    "fcf_yield": 0.055,
                    "revenue_growth": 0.08,
                    "profit_margins": 0.16,
                    "roe": 0.19,
                    "debt_to_equity": 0.6,
                    "quick_ratio": 1.4,
                }
            },
        ),
        "alpha": StubProvider("alpha", {}),
    }

    client = build_client(store, providers)
    as_of = datetime(2024, 6, 1, tzinfo=timezone.utc)
    info = client.sync_ticker("ACME", as_of=as_of)

    assert info["trailingPE"] == pytest.approx(18.0)
    assert info["data_providers"]["fundamentals"] == "finnhub"

    snapshot = store.load_latest_snapshot("ACME")
    assert snapshot["provider"] == "finnhub"
    assert snapshot["eps"] == pytest.approx(3.0)

    meta_failure = store.load_provider_meta("fmp", "fundamentals")
    assert meta_failure["last_failure"] is not None
    meta_success = store.load_provider_meta("finnhub", "fundamentals")
    assert meta_success["last_success"] is not None


def test_scheduler_builds_jobs_and_invokes_client():
    client = MagicMock()
    client.category_order = ("prices", "fundamentals", "dividends", "profile")
    hooks = SchedulerHooks(
        client=client,
        desktop_cron_expression="0 */6 * * *",
        android_interval_minutes=360,
        android_flex_minutes=30,
    )

    jobs = hooks.build_jobs(["ACME"])
    assert len(jobs) == 2

    android_jobs = [job for job in jobs if job["platform"] == "android"]
    desktop_jobs = [job for job in jobs if job["platform"] == "desktop"]

    assert android_jobs
    android_job = android_jobs[0]
    assert android_job["work_manager"]["ticker"] == "ACME"
    assert android_job["work_manager"]["interval_minutes"] == 360
    assert android_job["work_manager"]["categories"] == list(client.category_order)

    assert desktop_jobs
    desktop_job = desktop_jobs[0]
    assert desktop_job["cron"]["expression"] == "0 */6 * * *"
    assert desktop_job["categories"] == list(client.category_order)
    desktop_job["callable"]()
    client.sync_ticker.assert_called_once_with("ACME", categories=None)
