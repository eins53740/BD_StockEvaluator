from __future__ import annotations

from bd_stockevaluator.core.watchlist import WatchlistAlertEngine


def test_watchlist_alert_engine_triggers_on_thresholds():
    engine = WatchlistAlertEngine()
    watchlist = [
        {
            "ticker": "AAPL",
            "channels": ["email", "push"],
            "rules": [
                {
                    "path": "fundamentals.valuation.overall_score",
                    "operator": ">=",
                    "value": 80,
                    "message": "Valuation score above target",
                },
                {
                    "path": "technicals.signal.score",
                    "operator": ">=",
                    "value": 7,
                    "message": "Technical signal in buy zone",
                },
            ],
        }
    ]
    analysis = {
        "AAPL": {
            "fundamentals": {"valuation": {"overall_score": 85}},
            "technicals": {"signal": {"score": 7.6}},
        }
    }

    alerts = engine.evaluate(watchlist, analysis)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.ticker == "AAPL"
    assert alert.channels == ["email", "push"]
    assert alert.triggered_rules == [
        "Valuation score above target",
        "Technical signal in buy zone",
    ]
    assert alert.payload["values"]["fundamentals.valuation.overall_score"] == 85
    assert alert.payload["values"]["technicals.signal.score"] == 7.6


def test_watchlist_alert_engine_ignores_when_below_threshold():
    engine = WatchlistAlertEngine()
    watchlist = [
        {
            "ticker": "MSFT",
            "channels": ["email"],
            "rules": [
                {
                    "path": "fundamentals.growth.cagr_5",
                    "operator": ">=",
                    "value": 0.15,
                    "message": "Growth accelerating",
                }
            ],
        }
    ]
    analysis = {
        "MSFT": {
            "fundamentals": {"growth": {"cagr_5": 0.12}},
            "technicals": {"signal": {"score": 5.5}},
        }
    }

    alerts = engine.evaluate(watchlist, analysis)

    assert alerts == []
