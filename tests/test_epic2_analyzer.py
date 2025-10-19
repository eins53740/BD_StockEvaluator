from __future__ import annotations

import pytest

from bd_stockevaluator.analysis import Epic2Analyzer


def build_sample_history():
    history = []
    for idx, year in enumerate(range(2013, 2024)):
        growth_years = year - 2013
        history.append(
            {
                "period": f"FY{year}",
                "eps": round(2.0 * (1.12**growth_years), 2),
                "revenue": 20000 * (1.07**growth_years),
                "free_cash_flow": 1200 * (1.085**growth_years),
                "pe": 24 - 0.4 * growth_years,
                "fcf_yield": 0.03 + 0.002 * growth_years,
                "profit_margins": 0.12 + 0.003 * growth_years,
                "roe": 0.16 + 0.004 * growth_years,
                "debt_to_equity": 0.72 - 0.015 * growth_years,
            }
        )
    return history


def test_epic2_analyzer_builds_expected_outputs():
    history = build_sample_history()
    latest = history[-1]

    stock_info = {
        "ticker": "ACME",
        "sector": "Technology",
        "regularMarketPrice": 150.0,
        "eps": latest["eps"],
        "trailingPE": 18.0,
        "pegRatio": 1.3,
        "priceToBook": 3.8,
        "evToEbit": 12.0,
        "fcfYield": 0.055,
        "dividendYield": 0.018,
        "payoutRatio": 0.35,
        "profitMargins": latest["profit_margins"],
        "operatingMargins": 0.21,
        "returnOnEquity": latest["roe"],
        "returnOnAssets": 0.11,
        "debtToEquity": 0.48,
        "historicalMetrics": history,
    }

    analyzer = Epic2Analyzer(stock_info, sector="Technology")
    results = analyzer.analyze()

    valuation = results["valuation"]
    assert valuation["overall_score"] is not None
    assert valuation["overall_score"] > 60
    assert "fcf_yield" in valuation["metrics"]
    assert valuation["metrics"]["fcf_yield"]["sector_score"] is not None

    profitability = results["profitability"]
    assert profitability["overall_score"] is not None
    assert profitability["stability_label"] in {"Excellent", "Solid"}
    assert profitability["metrics"]["roe"]["score"] > 70

    growth = results["growth"]
    revenue_growth = growth["metrics"]["revenue"]["cagr_5y"]
    assert revenue_growth == pytest.approx(0.07, rel=0.1)

    intrinsic = results["intrinsic_values"]["models"]
    assert "dcf" in intrinsic
    assert intrinsic["dcf"]["value"] > 0
    assert "ben_graham" in intrinsic
    assert (
        intrinsic["ben_graham"]["margin_of_safety_price"]
        < intrinsic["ben_graham"]["value"]
    )
    if "ddm" in intrinsic:
        assert intrinsic["ddm"]["value"] > stock_info["regularMarketPrice"] * 0.5

    context = results["historical_context"]["pe"]
    assert context["delta_pct"] is not None
    assert context["favourable"] is True
