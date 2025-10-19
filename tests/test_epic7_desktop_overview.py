from __future__ import annotations

from unittest.mock import MagicMock

from bd_stockevaluator.ux.dashboard import (
    DashboardSnapshot,
    DashboardTickerOverview,
    build_dashboard_layout_spec,
    collect_dashboard_snapshot,
)


def _analysis_payload(ticker: str, verdict: str = "BUY") -> dict:
    upper = ticker.upper()
    return {
        "ticker": upper,
        "company_name": f"{upper} Incorporated",
        "result": verdict,
        "valuation_scorecard": {"score": 7.2, "rating": "attractive"},
        "profitability_snapshot": {"roe": 0.18, "margin_stability": "strong"},
        "growth_trends": {"revenue_cagr": 0.12},
        "intrinsic_value_models": {"dcf": {"value": 155.0}},
        "technical_analysis": {"momentum": {"score": 6}, "trend": {"score": 4}},
        "macro_context": {"alignment": {"rates_vs_growth": "supportive"}},
        "metrics": {"price": 120.55},
        "generated_at": "2024-01-03T00:00:00Z",
    }


def test_collect_dashboard_snapshot_merges_sections() -> None:
    service = MagicMock()
    service.analyze.side_effect = [
        _analysis_payload("acme"),
        _analysis_payload("zeus", verdict="HOLD"),
    ]

    macro_service = MagicMock()
    macro_service.get_snapshot.return_value = {"headline": "Soft landing likely"}

    snapshot = collect_dashboard_snapshot(
        ["acme", "  ", "ZEUS", "acme"], service, macro_service=macro_service
    )

    assert [call.args[0] for call in service.analyze.call_args_list] == [
        "ACME",
        "ZEUS",
    ]
    assert [ticker.ticker for ticker in snapshot.tickers] == ["ACME", "ZEUS"]
    assert snapshot.tickers[0].fundamentals["valuation"]["rating"] == "attractive"
    assert snapshot.tickers[1].technicals["momentum"]["score"] == 6
    assert snapshot.macro_snapshot == {"headline": "Soft landing likely"}
    assert snapshot.tickers[0].macro["alignment"]["rates_vs_growth"] == "supportive"


def test_build_dashboard_layout_spec_is_stable_snapshot() -> None:
    snapshot = DashboardSnapshot(
        tickers=[
            DashboardTickerOverview(
                ticker="ACME",
                company_name="Acme Corp",
                verdict="BUY",
                fundamentals={
                    "valuation": {"score": 7.2},
                    "profitability": {"roe": 0.18},
                    "growth": {"revenue_cagr": 0.12},
                    "intrinsic_values": {"dcf": {"value": 155}},
                },
                technicals={"momentum": {"score": 6}},
                macro={"alignment": {"summary": "supportive"}},
                metrics={"price": 120.55},
                generated_at="2024-01-03T00:00:00Z",
            )
        ],
        macro_snapshot={"headline": "Soft landing likely"},
        generated_at="2024-02-01T12:00:00Z",
    )

    spec = build_dashboard_layout_spec(snapshot)

    assert spec == {
        "title": "BD Finance Desktop Overview",
        "generated_at": "2024-02-01T12:00:00Z",
        "macro": {"headline": "Soft landing likely"},
        "sections": [
            {
                "ticker": "ACME",
                "company_name": "Acme Corp",
                "verdict": "BUY",
                "metrics": {"price": 120.55},
                "tabs": [
                    {
                        "id": "fundamentals",
                        "label": "Fundamentals",
                        "payload": {
                            "valuation": {"score": 7.2},
                            "profitability": {"roe": 0.18},
                            "growth": {"revenue_cagr": 0.12},
                            "intrinsic_values": {"dcf": {"value": 155}},
                        },
                    },
                    {
                        "id": "technicals",
                        "label": "Technicals",
                        "payload": {"momentum": {"score": 6}},
                    },
                    {
                        "id": "macro",
                        "label": "Macro Context",
                        "payload": {"alignment": {"summary": "supportive"}},
                    },
                ],
            }
        ],
    }
