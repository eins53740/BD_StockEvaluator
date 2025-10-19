from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

import bd_stockevaluator.core.service as core_service
from bd_stockevaluator.api.main import app
from bd_stockevaluator.core.service import StockAnalysisService


def _analysis_stub() -> Dict[str, Any]:
    return {
        "ticker": "ACME",
        "company_name": "Acme Corp",
        "generated_at": "2024-01-03T00:00:00Z",
        "technical_analysis": {
            "chart": {"json": "charts/acme.json", "png": "charts/acme.png"}
        },
        "fundamentals_history": [{"period": "FY2023", "pe": 22.0}],
        "price_history": [{"date": "2024-01-01", "close": 150.0}],
        "data_providers": {"fundamentals": "fmp"},
    }


def test_build_sync_payload_aggregates_store(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StockAnalysisService()

    monkeypatch.setattr(
        service,
        "analyze",
        lambda ticker, include_opinion=False: _analysis_stub(),
    )
    monkeypatch.setattr(
        core_service.SQLiteDataStore,
        "load_latest_snapshot",
        lambda self, ticker: {"provider": "fmp", "currency": "USD"},
    )
    monkeypatch.setattr(
        core_service.SQLiteDataStore,
        "load_history",
        lambda self, ticker: [{"period": "FY2022", "pe": 24.0}],
    )
    monkeypatch.setattr(
        core_service,
        "MACRO_SERVICE",
        SimpleNamespace(get_snapshot=lambda: {"headline": "Steady expansion"}),
    )

    payload = service.build_sync_payload("ACME")

    assert payload["ticker"] == "ACME"
    assert payload["version"] == "2024-01-03T00:00:00Z"
    assert payload["fundamentals"]["snapshot"]["provider"] == "fmp"
    assert payload["fundamentals"]["history"][0]["period"] == "FY2022"
    assert payload["price_history"][0]["close"] == 150.0
    assert payload["macro_snapshot"]["headline"] == "Steady expansion"


def test_sync_endpoint_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)

    sample_payload = {
        "ticker": "ACME",
        "version": "2024-01-03T00:00:00Z",
        "data_providers": {"fundamentals": "fmp"},
        "fundamentals": {
            "snapshot": {"provider": "fmp"},
            "history": [{"period": "FY2023"}],
        },
        "price_history": [{"date": "2024-01-01", "close": 150.0}],
        "technical_chart": {"json": "charts/acme.json"},
        "macro_snapshot": {"headline": "Steady expansion"},
    }

    monkeypatch.setattr(
        "bd_stockevaluator.api.main.analysis_service.build_sync_payload",
        lambda ticker: sample_payload,
    )

    response = client.get("/sync/ACME")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "ACME"
    assert body["fundamentals"]["snapshot"]["provider"] == "fmp"
