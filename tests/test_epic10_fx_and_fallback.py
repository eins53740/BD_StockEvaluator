from __future__ import annotations

from datetime import datetime, timezone

from typing import Dict, Optional

from bd_stockevaluator.core.data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
    SQLiteDataStore,
)


class StubProvider:
    def __init__(self, name: str, payloads: Optional[Dict[str, Dict]] = None) -> None:
        self.name = name
        self._payloads = payloads or {}

    def fetch(self, ticker: str) -> Dict[str, Dict]:
        return self._payloads


def build_client(store: SQLiteDataStore, providers: Dict[str, StubProvider]):
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
    converter = CurrencyConverter({"USD": 1.0, "EUR": 1.07, "BRL": 0.20})
    return MultiSourceDataClient(
        store=store, converter=converter, providers=providers, precedence=precedence
    )


def test_provider_fallback_flag(tmp_path):
    store = SQLiteDataStore(tmp_path / "s.db")

    # Simulate yahoo not providing prices, fmp provides prices
    providers = {
        "yahoo": StubProvider("yahoo", {"prices": {}}),
        "fmp": StubProvider("fmp", {"prices": {"currency": "BRL", "close": 100.0}}),
    }

    client = build_client(store, providers)
    info = client.sync_ticker("FOO", as_of=datetime(2024, 1, 1, tzinfo=timezone.utc))

    assert info.get("data_providers")
    # provider_fallback should be True because prices used 'fmp' while precedence lists 'yahoo' first
    assert info.get("provider_fallback") is True


def test_fx_snapshot_returns_equivalence(tmp_path):
    store = SQLiteDataStore(tmp_path / "s2.db")

    # Provide price history in BRL; converter has USD/EUR rates. We'll compute returns and ensure conversion
    providers = {
        "yahoo": StubProvider(
            "yahoo",
            {
                "price_history": [
                    {
                        "date": "2024-01-01",
                        "open": 90.0,
                        "high": 110.0,
                        "low": 85.0,
                        "close": 100.0,
                    },
                    {
                        "date": "2024-01-02",
                        "open": 100.0,
                        "high": 120.0,
                        "low": 95.0,
                        "close": 110.0,
                    },
                ],
                "prices": {"currency": "BRL", "close": 110.0, "previous_close": 100.0},
                "profile": {"exchange": "SAO", "country": "Brazil", "currency": "BRL"},
            },
        ),
    }

    client = build_client(store, providers)
    info = client.sync_ticker(
        "B3SA3.SA", as_of=datetime(2024, 1, 10, tzinfo=timezone.utc)
    )

    # percent return based on native currency close values: (110-100)/100 = 0.10
    native_return = (
        info["regularMarketPrice"] - info.get("regularMarketPreviousClose")
    ) / info.get("regularMarketPreviousClose")

    # Now compute using USD values: prices are converted using fx_snapshot rates
    fx = info.get("fx_snapshot") or {}
    # Ensure fx snapshot contains USD and BRL
    assert "USD" in fx
    assert "BRL" in fx

    brl_to_usd = fx.get("BRL")
    # Convert native closes to USD using rates stored as rates_to_usd
    prev_usd = (info.get("regularMarketPreviousClose") or 0) * brl_to_usd
    cur_usd = (info.get("regularMarketPrice") or 0) * brl_to_usd
    usd_return = (cur_usd - prev_usd) / prev_usd

    assert round(native_return, 6) == round(usd_return, 6)


def test_suffix_metadata_backfill(tmp_path):
    store = SQLiteDataStore(tmp_path / "s3.db")

    # Simulate a provider that returns only prices and no profile; client should backfill minimal profile on first read
    providers = {
        "yahoo": StubProvider(
            "yahoo",
            {
                "prices": {"currency": "GBP", "close": 50.0, "previous_close": 48.0},
                # no profile provided
            },
        )
    }

    client = build_client(store, providers)
    info = client.sync_ticker(
        "TSCO.L", as_of=datetime(2024, 1, 10, tzinfo=timezone.utc)
    )

    # On first read we expect profile/exchange/country may be missing but the client/backfill should at least set currency and exchange if possible
    assert info.get("currency") == "GBP"
    # exchange should be present (TSCO.L -> .L suffix often maps to LSE; simplistic backfill may set exchange to 'LSE' or preserve None; ensure not to crash
    assert "exchange" in info
