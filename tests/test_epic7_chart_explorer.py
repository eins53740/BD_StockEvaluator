from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


from bd_stockevaluator.ux.chart_explorer import (
    ChartExplorerPayload,
    collect_chart_explorer_payload,
)


class DummyService:
    def __init__(self) -> None:
        self.analyze_calls: List[str] = []

    def analyze(self, ticker: str, include_opinion: bool = False) -> Dict[str, Any]:
        self.analyze_calls.append(ticker)
        return {
            "ticker": ticker,
            "company_name": "Acme Corp",
            "technical_analysis": {
                "chart": {
                    "json": "C:/tmp/static/charts/acme.json",
                }
            },
            "fundamentals_history": [
                {
                    "period": "FY2023",
                    "pe": 22.0,
                    "peg": 1.8,
                    "fcf_yield": 0.045,
                    "as_of": "2023-12-31",
                },
                {
                    "period": "FY2022",
                    "pe": 24.0,
                    "peg": 1.9,
                    "fcf_yield": 0.04,
                    "as_of": "2022-12-31",
                },
            ],
            "price_history": [
                {
                    "date": "2024-01-01",
                    "close": 150.0,
                    "open": 149.0,
                    "high": 151.0,
                    "low": 148.5,
                    "volume": 1_200_000,
                },
                {
                    "date": "2024-01-02",
                    "close": 152.0,
                    "open": 150.0,
                    "high": 153.0,
                    "low": 149.5,
                    "volume": 1_150_000,
                },
            ],
        }


def test_collect_chart_explorer_payload_loads_history(
    tmp_path: Path, monkeypatch
) -> None:
    json_path = tmp_path / "static" / "charts" / "acme.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    chart_payload = {"data": [{"y": [1, 2, 3]}], "layout": {"title": "Chart"}}
    json_path.write_text(json.dumps(chart_payload), encoding="utf-8")

    service = DummyService()

    payload = collect_chart_explorer_payload(
        "ACME", service=service, chart_json_root=json_path.parent.parent
    )

    assert isinstance(payload, ChartExplorerPayload)
    assert payload.ticker == "ACME"
    assert payload.company_name == "Acme Corp"
    assert payload.fundamentals_history[0]["period"] == "FY2023"
    assert payload.price_history[-1]["close"] == 152.0
    assert payload.technical_figure_json["layout"]["title"] == "Chart"
