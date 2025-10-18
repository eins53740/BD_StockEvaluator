from __future__ import annotations

import math
from pathlib import Path
from typing import List

import pytest

from bd_stockevaluator.analysis.epic3 import Epic3TechnicalAnalyzer


def build_price_history(days: int = 120) -> List[dict]:
    base_price = 100.0
    history: List[dict] = []
    for idx in range(days):
        # Introduce an accelerated uptrend with manageable oscillation for signal strength.
        trend = 0.55 * idx
        seasonal = 2.5 * math.sin(idx / 12.0)
        close = base_price + trend + seasonal
        open_price = close - 0.6 + 0.5 * math.sin(idx / 6.0)
        high = max(close, open_price) + 1.4
        low = min(close, open_price) - 1.2
        volume = 150_000 + 700 * idx + (2500 * (idx % 5))

        history.append(
            {
                "date": f"2024-01-{(idx % 30) + 1:02d}",
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            }
        )
    return history


def test_indicator_suite_detects_momentum():
    history = build_price_history()
    analyzer = Epic3TechnicalAnalyzer(history)

    indicators = analyzer.compute_indicator_suite()

    assert {"macd", "rsi", "adx", "bollinger", "sma"} <= indicators.keys()

    macd = indicators["macd"]
    assert macd["line"] is not None
    assert macd["signal"] is not None
    assert macd["histogram"] is not None
    assert macd["histogram"] > 0  # uptrend should yield positive momentum

    rsi = indicators["rsi"]["value"]
    assert 50 < rsi < 90

    adx = indicators["adx"]["adx"]
    assert adx and adx > 5
    assert indicators["adx"]["plus_di"] > indicators["adx"]["minus_di"]

    bands = indicators["bollinger"]
    assert bands["upper"] > bands["lower"]
    assert bands["price_position"] in {"upper", "middle", "lower"}

    sma = indicators["sma"]
    assert sma["sma20"] > sma["sma50"]
    if sma["sma200"] is not None:
        assert sma["sma50"] > sma["sma200"]


def test_pattern_detection_identifies_support_and_trend():
    history = build_price_history()
    analyzer = Epic3TechnicalAnalyzer(history)

    patterns = analyzer.detect_price_patterns()

    supports = patterns["support_levels"]
    resistances = patterns["resistance_levels"]
    assert supports and resistances
    assert any(level < history[-1]["close"] - 10 for level in supports)
    assert max(resistances) >= history[-1]["close"] - 2

    fibs = patterns["fibonacci"]
    assert {"0.382", "0.5", "0.618"} <= fibs.keys()

    trendline = patterns["trendline"]
    assert trendline["slope"] > 0
    assert trendline["endpoints"]["start"]["price"] < trendline["endpoints"]["end"]["price"]


def test_signal_generator_combines_components_into_buy_action():
    history = build_price_history()
    analyzer = Epic3TechnicalAnalyzer(history)

    signal = analyzer.generate_signal(verdict="BUY")

    assert signal["action"] == "Buy"
    assert signal["score"] >= 7
    assert signal["components"]["trend"] >= signal["components"]["momentum"]
    assert signal["hysteresis_state"]["bucket"] in {"buy", "hold", "sell"}


def test_performance_metrics_cover_drawdown_and_ratios():
    history = build_price_history()
    analyzer = Epic3TechnicalAnalyzer(history)

    performance = analyzer.compute_performance_metrics(risk_free_rate=0.02)

    assert performance["max_drawdown"] < 0
    assert performance["sharpe_ratio"] > 0.5
    assert performance["calmar_ratio"] > 0
    assert performance["volatility"] > 0


def test_chart_export_writes_png_and_json(tmp_path: Path):
    history = build_price_history()
    analyzer = Epic3TechnicalAnalyzer(history)

    output = analyzer.export_charts("ACME", tmp_path)

    png_path = tmp_path / "charts" / "ACME.png"
    json_path = tmp_path / "charts" / "ACME.json"
    assert output["png"] == png_path
    assert output["json"] == json_path
    assert png_path.exists()
    assert json_path.exists()
    assert png_path.stat().st_size > 0
    assert json_path.stat().st_size > 0
