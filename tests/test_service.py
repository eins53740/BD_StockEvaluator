import pytest
from unittest.mock import MagicMock, patch

from bd_stockevaluator.core.service import STATIC_DIR, StockAnalysisService


@patch("bd_stockevaluator.core.service._build_qualitative_components")
@patch("bd_stockevaluator.core.service.MACRO_SERVICE")
@patch("bd_stockevaluator.core.service.generate_stock_opinion")
@patch("bd_stockevaluator.core.service.StockAnalysisFeatures")
@patch("bd_stockevaluator.core.service.StockEvaluator")
@patch("bd_stockevaluator.core.service.Epic2Analyzer")
@patch("bd_stockevaluator.core.service.Epic3TechnicalAnalyzer")
@patch("bd_stockevaluator.core.service.get_stock_data")
def test_analyze_full_flow(
    get_stock_data_mock,
    epic3_cls_mock,
    epic2_cls_mock,
    evaluator_cls_mock,
    features_cls_mock,
    opinion_mock,
    macro_service_mock,
    qualitative_mock,
):
    get_stock_data_mock.return_value = {
        "longName": "Acme Corp",
        "ticker": "ACME",
        "priceHistory": [
            {
                "date": "2024-01-08",
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 154.0,
                "volume": 1_200_000,
            },
            {
                "date": "2024-01-09",
                "open": 154.0,
                "high": 156.0,
                "low": 153.0,
                "close": 155.0,
                "volume": 1_100_000,
            },
        ],
    }

    evaluator_instance = MagicMock()
    evaluator_instance.metrics = {"rev_growth": 0.12}
    evaluator_instance.evaluate.return_value = (
        "BUY",
        [("Revenue Growth (TTM)", 0.12, 0.1, "PASS")],
        {("A", "B"), ("B", "C")},
    )
    evaluator_cls_mock.return_value = evaluator_instance

    features_instance = MagicMock()
    features_instance.get_risk_assessment.return_value = {"overall_risk_score": 25}
    features_instance.get_trend_analysis.return_value = {"trends": {}}
    features_instance.get_comparative_analysis.return_value = {
        "valuation_vs_peers": "Fairly Valued"
    }
    features_instance.get_dividend_analysis.return_value = {"current_yield": 0.02}
    features_cls_mock.return_value = features_instance

    epic2_instance = MagicMock()
    epic2_instance.analyze.return_value = {
        "valuation": {"overall_score": 82, "metrics": {"pe": {"score": 78}}},
        "profitability": {"overall_score": 75, "metrics": {}},
        "growth": {"overall_score": 68, "metrics": {}},
        "intrinsic_values": {"price": 150, "models": {"dcf": {"value": 160}}},
        "historical_context": {"pe": {"delta_pct": -0.1, "favourable": True}},
    }
    epic2_cls_mock.return_value = epic2_instance

    technical_instance = MagicMock()
    technical_instance.compute_indicator_suite.return_value = {
        "macd": {"line": 0.5, "signal": 0.3, "histogram": 0.2},
        "rsi": {"value": 62.0},
        "adx": {"adx": 28.0, "plus_di": 32.0, "minus_di": 18.0},
        "bollinger": {"price_position": "upper", "upper": 160.0, "lower": 145.0},
        "sma": {"sma20": 152.0, "sma50": 148.0, "sma200": 130.0, "last_close": 155.0},
    }
    technical_instance.detect_price_patterns.return_value = {
        "support_levels": [140.0, 135.0],
        "resistance_levels": [165.0],
        "fibonacci": {"0.382": 142.0, "0.618": 150.0},
        "trendline": {"slope": 0.45, "intercept": 120.0},
    }
    technical_instance.generate_signal.return_value = {
        "score": 7.8,
        "action": "Buy",
        "components": {"trend": 4.2, "momentum": 3.6},
        "notes": ["MACD histogram positive."],
        "hysteresis_state": {"bucket": "buy", "thresholds": {"buy": 7.0, "sell": 3.0}},
    }
    technical_instance.compute_performance_metrics.return_value = {
        "max_drawdown": -0.12,
        "sharpe_ratio": 1.4,
        "calmar_ratio": 0.9,
        "volatility": 0.22,
    }
    chart_dir = STATIC_DIR / "charts"
    chart_paths = {
        "png": chart_dir / "ACME.png",
        "json": chart_dir / "ACME.json",
    }
    technical_instance.export_charts.return_value = chart_paths
    epic3_cls_mock.return_value = technical_instance
    epic3_cls_mock.from_ticker.return_value = technical_instance

    opinion_mock.return_value = "<p>Good stock</p>"
    macro_service_mock.get_context.return_value = {
        "snapshot": {"dashboard": {}},
        "recession_signals": {"sahm_rule": {"triggered": False}},
        "sentiment": {"regime": "neutral"},
        "alignment": {"insights": ["Balanced"], "risk_bias": "balanced"},
    }
    qualitative_mock.return_value = {
        "moat": {
            "overall_score": 81.2,
            "moat_rating": "Wide Moat",
            "dimensions": {
                "switching_costs": {
                    "manual_score": 90.0,
                    "ai_score": 88.0,
                    "combined_score": 89.0,
                    "summary": "High retention across enterprise clients.",
                    "notes": [],
                }
            },
        },
        "ownership": {
            "institutional": {
                "trend": "increasing",
                "change_percentage": 6.4,
                "latest": 68.1,
            },
            "insider": {
                "trend": "stable",
                "change_percentage": 0.2,
                "latest": 2.3,
            },
            "alerts": [],
        },
        "management": {
            "score": 84.1,
            "rating": "High",
            "highlights": ["Management prioritised reinvestment."],
            "warnings": [],
        },
    }

    service = StockAnalysisService(opinion_api_key="dummy")
    result = service.analyze("acme")

    assert result["ticker"] == "ACME"
    assert result["result"] == "BUY"
    assert result["active_links"] == [["A", "B"], ["B", "C"]]
    assert result["opinion_report"] == "<p>Good stock</p>"
    assert result["risk_assessment"]["overall_risk_score"] == 25
    assert result["metrics"] == {"rev_growth": 0.12}
    assert result["valuation_scorecard"]["overall_score"] == 82
    assert result["intrinsic_value_models"]["models"]["dcf"]["value"] == 160
    assert result["historical_context"]["pe"]["favourable"] is True
    assert result["technical_analysis"]["signal"]["action"] == "Buy"
    assert result["technical_analysis"]["chart"]["png"].endswith("charts/ACME.png")
    assert result["macro_context"]["alignment"]["risk_bias"] == "balanced"
    assert result["qualitative_moat"]["moat_rating"] == "Wide Moat"
    assert result["qualitative_moat"]["overall_score"] == pytest.approx(81.2)
    assert result["ownership_trends"]["institutional"]["trend"] == "increasing"
    assert result["management_quality"]["rating"] == "High"

    evaluator_cls_mock.assert_called_once()
    features_cls_mock.assert_called_once_with(
        "acme", get_stock_data_mock.return_value, None
    )
    opinion_mock.assert_called_once()
    epic2_cls_mock.assert_called_once_with(
        get_stock_data_mock.return_value, None, sector=None
    )


@patch("bd_stockevaluator.core.service._build_qualitative_components")
@patch("bd_stockevaluator.core.service.MACRO_SERVICE")
@patch("bd_stockevaluator.core.service.generate_stock_opinion")
@patch("bd_stockevaluator.core.service.StockAnalysisFeatures")
@patch("bd_stockevaluator.core.service.StockEvaluator")
@patch("bd_stockevaluator.core.service.Epic2Analyzer")
@patch("bd_stockevaluator.core.service.Epic3TechnicalAnalyzer")
@patch("bd_stockevaluator.core.service.get_stock_data")
def test_analyze_without_opinion(
    get_stock_data_mock,
    epic3_cls_mock,
    epic2_cls_mock,
    evaluator_cls_mock,
    features_cls_mock,
    opinion_mock,
    macro_service_mock,
    qualitative_mock,
):
    get_stock_data_mock.return_value = {
        "longName": "Beta Inc",
        "ticker": "BETA",
        "priceHistory": [
            {
                "date": "2024-01-08",
                "open": 80.0,
                "high": 81.0,
                "low": 79.5,
                "close": 80.5,
                "volume": 800_000,
            },
            {
                "date": "2024-01-09",
                "open": 80.5,
                "high": 80.8,
                "low": 79.8,
                "close": 80.1,
                "volume": 750_000,
            },
        ],
    }

    evaluator_instance = MagicMock()
    evaluator_instance.metrics = {}
    evaluator_instance.evaluate.return_value = ("Do Not Buy", [], set())
    evaluator_cls_mock.return_value = evaluator_instance

    features_instance = MagicMock()
    features_instance.get_risk_assessment.return_value = {}
    features_instance.get_trend_analysis.return_value = {}
    features_instance.get_comparative_analysis.return_value = {}
    features_instance.get_dividend_analysis.return_value = {}
    features_cls_mock.return_value = features_instance

    epic2_instance = MagicMock()
    epic2_instance.analyze.return_value = {
        "valuation": {},
        "profitability": {},
        "growth": {},
        "intrinsic_values": {"price": None, "models": {}},
        "historical_context": {},
    }
    epic2_cls_mock.return_value = epic2_instance

    technical_instance = MagicMock()
    technical_instance.compute_indicator_suite.return_value = {
        "macd": {"line": None, "signal": None, "histogram": None},
        "rsi": {"value": 50.0},
        "adx": {"adx": None, "plus_di": None, "minus_di": None},
        "bollinger": {"price_position": "middle", "upper": None, "lower": None},
        "sma": {"sma20": None, "sma50": None, "sma200": None, "last_close": None},
    }
    technical_instance.detect_price_patterns.return_value = {
        "support_levels": [],
        "resistance_levels": [],
        "fibonacci": {"0.382": 0.0, "0.618": 0.0},
        "trendline": {"slope": 0.0, "intercept": 0.0},
    }
    technical_instance.generate_signal.return_value = {
        "score": 3.0,
        "action": "Hold",
        "components": {"trend": 1.5, "momentum": 1.5},
        "notes": [],
        "hysteresis_state": {"bucket": "hold", "thresholds": {"buy": 7.0, "sell": 3.0}},
    }
    technical_instance.compute_performance_metrics.return_value = {
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "calmar_ratio": 0.0,
        "volatility": 0.0,
    }
    chart_dir = STATIC_DIR / "charts"
    technical_instance.export_charts.return_value = {
        "png": chart_dir / "BETA.png",
        "json": chart_dir / "BETA.json",
    }
    epic3_cls_mock.return_value = technical_instance
    epic3_cls_mock.from_ticker.return_value = technical_instance
    macro_service_mock.get_context.return_value = {
        "snapshot": {"dashboard": {}},
        "recession_signals": {},
        "sentiment": {"regime": "neutral"},
        "alignment": {"insights": [], "risk_bias": "balanced"},
    }
    qualitative_mock.return_value = {
        "moat": {
            "overall_score": 62.0,
            "moat_rating": "Narrow Moat",
            "dimensions": {},
        },
        "ownership": {
            "institutional": {
                "trend": "stable",
                "change_percentage": 0.4,
                "latest": 54.2,
            },
            "insider": {
                "trend": "stable",
                "change_percentage": 0.1,
                "latest": 1.1,
            },
            "alerts": [],
        },
        "management": {
            "score": 58.0,
            "rating": "Moderate",
            "highlights": [],
            "warnings": [],
        },
    }

    service = StockAnalysisService()
    result = service.analyze("beta", include_opinion=False)

    assert result["opinion_report"] is None
    opinion_mock.assert_not_called()
    assert result["qualitative_moat"]["moat_rating"] == "Narrow Moat"
    assert result["ownership_trends"]["insider"]["latest"] == pytest.approx(1.1)
    assert result["management_quality"]["rating"] == "Moderate"


@patch(
    "bd_stockevaluator.core.service.get_stock_data",
    side_effect=ValueError("Ticker not found"),
)
@patch("bd_stockevaluator.core.service._build_qualitative_components")
@patch("bd_stockevaluator.core.service.MACRO_SERVICE")
def test_analyze_raises_when_data_missing(
    macro_service_mock, _qualitative_mock, get_stock_data_mock
):
    service = StockAnalysisService()
    with pytest.raises(ValueError):
        service.analyze("missing")
