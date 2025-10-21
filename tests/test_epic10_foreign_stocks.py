from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Dict, Optional

import pytest

from bd_stockevaluator.core.data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
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


def build_client(
    store: SQLiteDataStore, providers: Dict[str, StubProvider]
) -> MultiSourceDataClient:
    precedence = {
        "prices": ["yahoo", "fmp"],
        "fundamentals": ["yahoo", "fmp"],
        "dividends": ["yahoo", "fmp"],
        "profile": ["yahoo", "fmp"],
        "exchange_rates": ["fmp", "alpha", "yahoo"],
        "history": ["fmp", "finnhub"],
        "price_history": ["fmp", "yahoo"],
        "ownership": ["fmp", "yahoo"],
    }

    converter = CurrencyConverter({"USD": 1.0, "GBP": 1.25, "EUR": 1.08, "BRL": 0.20})
    return MultiSourceDataClient(
        store=store,
        converter=converter,
        providers=providers,
        precedence=precedence,
    )


def test_foreign_stock_sync_and_persist(tmp_path):
    store = SQLiteDataStore(tmp_path / "stocks.db")

    providers = {
        "yahoo": StubProvider(
            "yahoo",
            {
                "prices": {
                    "currency": "BRL",
                    "close": 50.0,
                    "previous_close": 48.0,
                    "open": 49.5,
                },
                "profile": {
                    "name": "B3 SA",
                    "sector": "Financial Services",
                    "industry": "Financial Exchanges",
                    "exchange": "SAO",
                    "country": "Brazil",
                },
            },
        ),
        "fmp": StubProvider("fmp", {}),
    }

    client = build_client(store, providers)
    as_of = datetime(2024, 1, 10, 12, tzinfo=timezone.utc)

    info = client.sync_ticker("B3SA3.SA", as_of=as_of)
    assert info["ticker"] == "B3SA3.SA"
    assert info["currency"] == "BRL"
    assert info["exchange"] == "SAO"
    assert info["country"] == "Brazil"
    assert info["regularMarketPrice"] == pytest.approx(50.0)
    assert info["regularMarketPriceUSD"] == pytest.approx(10.0)
    assert info["regularMarketPriceEUR"] == pytest.approx(9.259, rel=1e-4)

    snapshot = store.load_latest_snapshot("B3SA3.SA")
    assert snapshot["currency"] == "BRL"
    assert snapshot["exchange"] == "SAO"
    assert snapshot["country"] == "Brazil"
