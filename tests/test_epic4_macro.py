from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from bd_stockevaluator.core.data_pipeline import SQLiteDataStore
from bd_stockevaluator.analysis.epic4_macro import (
    ForecastAlignmentEngine,
    MacroDataPoint,
    MacroSeries,
    MacroSnapshotBuilder,
    RecessionSignalCalculator,
    SentimentTracker,
)


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_macro_snapshot_builder_persists_series_and_builds_dashboard(tmp_path):
    store = SQLiteDataStore(tmp_path / "macro.db")
    builder = MacroSnapshotBuilder(store)

    gdp_series = MacroSeries(
        series_id="gdp_growth",
        frequency="quarterly",
        provider="fred",
        points=[
            MacroDataPoint(_dt(2024, 3, 31), 2.5),
            MacroDataPoint(_dt(2024, 6, 30), 2.1),
        ],
    )
    cpi_series = MacroSeries(
        series_id="cpi",
        frequency="monthly",
        provider="fred",
        points=[
            MacroDataPoint(_dt(2024, 5, 31), 3.2),
            MacroDataPoint(_dt(2024, 6, 30), 3.0),
            MacroDataPoint(_dt(2024, 7, 31), 2.9),
        ],
    )
    unemployment_series = MacroSeries(
        series_id="unemployment_rate",
        frequency="monthly",
        provider="fred",
        points=[
            MacroDataPoint(_dt(2024, 5, 31), 3.6),
            MacroDataPoint(_dt(2024, 6, 30), 3.7),
            MacroDataPoint(_dt(2024, 7, 31), 3.9),
        ],
    )
    fed_funds_series = MacroSeries(
        series_id="fed_funds_rate",
        frequency="daily",
        provider="fred",
        points=[
            MacroDataPoint(_dt(2024, 7, 15), 5.25),
            MacroDataPoint(_dt(2024, 7, 16), 5.33),
        ],
    )
    yield_curve_series = MacroSeries(
        series_id="yield_curve_spread",
        frequency="daily",
        provider="fred",
        points=[
            MacroDataPoint(_dt(2024, 7, 15), -0.35),
            MacroDataPoint(_dt(2024, 7, 16), -0.28),
        ],
    )

    as_of = _dt(2024, 7, 31)
    builder.ingest_series(gdp_series, as_of=as_of)
    builder.ingest_series(cpi_series, as_of=as_of)
    builder.ingest_series(unemployment_series, as_of=as_of)
    builder.ingest_series(fed_funds_series, as_of=as_of)
    builder.ingest_series(yield_curve_series, as_of=as_of)

    snapshot = builder.build_snapshot(as_of=as_of)

    assert snapshot["as_of"] == as_of.isoformat().replace("+00:00", "Z")
    dashboard = snapshot["dashboard"]

    assert dashboard["gdp_growth"]["latest"]["value"] == pytest.approx(2.1)
    assert dashboard["gdp_growth"]["trend"] == "cooling"

    assert dashboard["cpi"]["latest"]["value"] == pytest.approx(2.9)
    assert dashboard["cpi"]["trend"] == "cooling"

    assert dashboard["unemployment_rate"]["trend"] == "rising"
    assert dashboard["fed_funds_rate"]["trend"] == "rising"
    assert dashboard["yield_curve_spread"]["latest"]["value"] == pytest.approx(-0.28)

    stored_series = store.load_macro_series("cpi")
    assert len(stored_series) == 3
    assert stored_series[-1]["value"] == pytest.approx(2.9)
    stored_snapshot = store.load_macro_snapshot()
    assert stored_snapshot["as_of"] == snapshot["as_of"]


def test_recession_signals_detect_sahm_yield_curve_and_buffett_flags():
    dates = [_dt(2023, 8, 31) + timedelta(days=30 * idx) for idx in range(15)]
    unemployment_points = [
        MacroDataPoint(dt, value)
        for dt, value in zip(
            dates,
            [
                3.2,
                3.3,
                3.4,
                3.3,
                3.2,
                3.1,
                3.0,
                3.1,
                3.5,
                4.0,
                4.2,
                4.4,
                4.5,
                4.6,
                4.7,
            ],
        )
    ]
    yield_curve_points = [
        MacroDataPoint(_dt(2024, 7, day), spread)
        for day, spread in enumerate([-0.2, -0.3, -0.25, -0.15, -0.1], start=10)
    ]
    buffett_points = [
        MacroDataPoint(_dt(2024, quarter, 30), ratio)
        for quarter, ratio in ((3, 1.45), (6, 1.52))
    ]

    calculator = RecessionSignalCalculator()
    signals = calculator.evaluate(
        {
            "unemployment_rate": unemployment_points,
            "yield_curve_spread": yield_curve_points,
            "buffett_indicator": buffett_points,
        }
    )

    sahm = signals["sahm_rule"]
    assert sahm["triggered"] is True
    assert sahm["gap"] >= 0.5

    curve = signals["yield_curve_inversion"]
    assert curve["inverted"] is True
    assert curve["latest"] == pytest.approx(-0.1)

    buffett = signals["buffett_indicator"]
    assert buffett["stretched"] is True
    assert buffett["latest"] == pytest.approx(1.52)


def test_sentiment_tracker_combines_global_valuations_and_flows():
    valuation_points = [
        MacroDataPoint(_dt(2024, 5, 31), 75.0),
        MacroDataPoint(_dt(2024, 6, 30), 82.0),
        MacroDataPoint(_dt(2024, 7, 31), 85.0),
    ]
    flow_points = [
        MacroDataPoint(_dt(2024, 7, day), value)
        for day, value in (
            (1, -1.2),
            (8, -0.8),
            (15, -0.5),
            (22, -0.3),
        )
    ]

    tracker = SentimentTracker()
    sentiment = tracker.summarise(
        {
            "global_valuation_percentile": valuation_points,
            "institutional_flows": flow_points,
        }
    )

    assert sentiment["valuation_state"] == "stretched"
    assert sentiment["flow_trend"] == "outflows"
    assert sentiment["regime"] == "risk_off"


def test_forecast_alignment_engine_flags_rate_sensitive_and_macro_links():
    macro_snapshot = {
        "dashboard": {
            "fed_funds_rate": {
                "latest": {"value": 5.33, "date": _dt(2024, 7, 16)},
                "trend": "rising",
            },
            "gdp_growth": {
                "latest": {"value": 1.2, "date": _dt(2024, 6, 30)},
                "trend": "cooling",
            },
        }
    }
    fundamentals_trends = {
        "ticker": "ACME",
        "revenue_growth": {"trend": -0.08},
        "eps_growth": {"trend": -0.05},
        "fcf_growth": {"trend": 0.01},
    }

    engine = ForecastAlignmentEngine()
    alignment = engine.align(macro_snapshot, fundamentals_trends)

    assert any("rising rates" in insight.lower() for insight in alignment["insights"])
    assert alignment["risk_bias"] == "macro_headwinds"
