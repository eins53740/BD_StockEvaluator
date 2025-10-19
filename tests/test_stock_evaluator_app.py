from __future__ import annotations

import importlib
from unittest.mock import MagicMock

import pytest

from bd_stockevaluator import app as stock_app
from bd_stockevaluator.core import service as core_service


@pytest.fixture
def stock_app_module():
    module = importlib.reload(stock_app)
    module.app.config.update(TESTING=True)
    return module


def test_stock_app_root_get(stock_app_module):
    client = stock_app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Stock Evaluator" in response.data


def test_stock_app_post_flow(stock_app_module, monkeypatch):
    module = stock_app_module

    def fake_get_stock_data(ticker: str) -> dict:
        assert ticker == "FAKE"
        return {
            "longName": "Fake Corp",
            "revenueGrowth": 0.2,
            "trailingPE": 20.0,
            "returnOnEquity": 0.25,
            "profitMargins": 0.18,
            "debtToEquity": 0.4,
            "quickRatio": 1.8,
            "sector": "Technology",
            "industry": "Software",
            "beta": 1.0,
            "averageVolume": 1_000_000,
            "marketCap": 5_000_000_000,
            "currentPrice": 150.0,
            "currentRatio": 2.0,
            "dividendYield": 0.02,
            "payoutRatio": 0.4,
        }

    class DummyEvaluator:
        def __init__(self, info: dict) -> None:
            self.info = info
            self.metrics = {
                "rev_growth": info["revenueGrowth"],
                "pe": info["trailingPE"],
                "roe": info["returnOnEquity"],
                "margin": info["profitMargins"],
                "de": info["debtToEquity"],
                "qr": info["quickRatio"],
            }
            self.thresholds = {
                "rev_growth": 0.1,
                "pe": 25,
                "peg": 2.0,
                "roe": 0.15,
                "margin": 0.1,
                "de": 1.0,
                "qr": 1.5,
            }
            self.path = [
                ("Revenue Growth (TTM)", 0.2, 0.1, "PASS"),
                ("P/E Ratio", 20.0, "< 25", "PASS"),
                ("PEG Ratio", 1.0, "< 2.0", "PASS"),
                ("Return on Equity", 0.25, 0.15, "PASS"),
                ("Net Profit Margin", 0.18, 0.1, "PASS"),
                ("Debt to Equity", 0.4, 1.0, "PASS"),
                ("Quick Ratio", 1.8, 1.5, "PASS"),
            ]
            self.active_links = {
                "A->B",
                "B->C",
                "C->E",
                "E->G",
                "G->H",
                "H->I",
                "I->J",
            }

        def evaluate(self):
            return "BUY", list(self.path), self.active_links

    class DummyFeatures:
        def __init__(self, ticker: str, info: dict) -> None:
            self.ticker = ticker
            self.info = info

        def get_risk_assessment(self):
            return {"overall_risk_score": 25, "risk_level": "Low", "risk_factors": {}}

        def get_trend_analysis(self):
            return {"trends": {}, "momentum_score": 5, "trend_consistency": "Stable"}

        def get_comparative_analysis(self):
            return {"valuation_vs_peers": "Favorable"}

        def get_dividend_analysis(self):
            return {"current_yield": 0.02}

    def fake_generate_stock_opinion(api_key, company_name, ticker, metrics):
        return "<p>Opinion Ready</p>"

    class DummyEpic2:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def analyze(self):
            return {
                "valuation": {
                    "overall_score": 80,
                    "metrics": {
                        "fcf_yield": {"sector_score": 0.8, "score": 0.9, "value": 0.055}
                    },
                },
                "profitability": {
                    "overall_score": 70,
                    "metrics": {"roe": {"score": 75, "value": 0.25}},
                },
                "growth": {
                    "overall_score": 65,
                    "metrics": {"revenue": {"trend": "up", "value": 0.12}},
                },
                "intrinsic_values": {"price": 150, "models": {"dcf": {"value": 160}}},
                "historical_context": {"pe": {"delta_pct": -0.1, "favourable": True}},
            }

    class DummyEpic3:
        def __init__(self, *args, **kwargs) -> None:
            pass

        @classmethod
        def from_ticker(cls, *args, **kwargs):
            return cls()

        def compute_indicator_suite(self):
            return {}

        def detect_price_patterns(self):
            return {}

        def generate_signal(self, verdict: str):
            return {"action": verdict, "score": 5.0}

        def compute_performance_metrics(self):
            return {}

        def export_charts(self, ticker: str, static_dir):
            chart_dir = static_dir / "charts"
            chart_dir.mkdir(parents=True, exist_ok=True)
            return {
                "png": chart_dir / f"{ticker.upper()}.png",
                "json": chart_dir / f"{ticker.upper()}.json",
            }

    class DummyMacroService:
        def get_context(self, **kwargs):
            return {"alignment": {"risk_bias": "balanced"}}

    monkeypatch.setattr(core_service, "get_stock_data", fake_get_stock_data)
    monkeypatch.setattr(core_service, "StockEvaluator", DummyEvaluator)
    monkeypatch.setattr(core_service, "StockAnalysisFeatures", DummyFeatures)
    monkeypatch.setattr(
        core_service, "generate_stock_opinion", fake_generate_stock_opinion
    )
    monkeypatch.setattr(core_service, "Epic2Analyzer", DummyEpic2)
    monkeypatch.setattr(core_service, "Epic3TechnicalAnalyzer", DummyEpic3)
    monkeypatch.setattr(core_service, "MACRO_SERVICE", DummyMacroService())

    analysis_payload = {
        "ticker": "FAKE",
        "company_name": "Fake Corp",
        "result": "BUY",
        "path": [],
        "active_links": [],
        "flowchart_definition": "graph TD;",
        "opinion_report": "<p>Opinion Ready</p>",
        "risk_assessment": {
            "overall_risk_score": 25,
            "risk_level": "Low",
            "risk_factors": {},
        },
        "trend_analysis": {},
        "comparative_analysis": {},
        "dividend_analysis": {},
        "valuation_scorecard": {"overall_score": 80, "metrics": {}},
        "profitability_snapshot": {"overall_score": 70, "metrics": {}},
        "growth_trends": {"overall_score": 65, "metrics": {}},
        "intrinsic_value_models": {"price": 150, "models": {}},
        "historical_context": {},
        "technical_analysis": {"error": "skipped"},
        "macro_context": {},
        "metrics": {},
    }
    module.analysis_service = MagicMock()
    module.analysis_service.analyze.return_value = analysis_payload
    client = module.app.test_client()
    response = client.post("/", data={"ticker": "FAKE"})
    assert response.status_code == 200
    assert b"Opinion Ready" in response.data
