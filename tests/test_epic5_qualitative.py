from __future__ import annotations

from datetime import datetime

import pytest

from bd_stockevaluator.analysis.epic5_qualitative import (
    ManagementQualityAnalyzer,
    MoatAssessmentInput,
    MoatScorecardBuilder,
    OwnershipTrendAnalyzer,
)


def test_moat_scorecard_combines_manual_and_ai_scores():
    builder = MoatScorecardBuilder(default_manual_weight=0.6)
    assessment = MoatAssessmentInput(
        manual_scores={
            "switching_costs": 4.5,
            "network_effects": 4.0,
            "intangibles": 3.6,
            "cost_advantage": 4.2,
            "efficient_scale": 3.8,
        },
        ai_summaries={
            "switching_costs": {"score": 0.92, "summary": "High switching costs across enterprise clients."},
            "network_effects": {"score": 0.85, "summary": "Expanding partner ecosystem with strong retention."},
            "intangibles": {"score": 0.80, "summary": "Brand strength improving, patents renewed."},
            "cost_advantage": {"score": 0.88, "summary": "Scale-driven procurement advantages maintained."},
            "efficient_scale": {"score": 0.78, "summary": "Regional dominance discourages new entrants."},
        },
        qualitative_notes={"cost_advantage": ["Management emphasises margin resilience."]},
    )

    scorecard = builder.build(assessment)

    assert scorecard.overall_score == pytest.approx(81.9, abs=0.2)
    assert scorecard.moat_rating == "Wide Moat"
    assert scorecard.dimensions["switching_costs"]["combined_score"] == pytest.approx(90.0, abs=0.1)
    assert (
        scorecard.dimensions["switching_costs"]["summary"]
        == "High switching costs across enterprise clients."
    )
    assert "Management emphasises margin resilience." in scorecard.dimensions["cost_advantage"]["notes"]


def test_moat_scorecard_handles_missing_inputs():
    builder = MoatScorecardBuilder(default_manual_weight=0.5)
    assessment = MoatAssessmentInput(
        manual_scores={
            "switching_costs": None,
            "network_effects": 2.6,
            "intangibles": 3.0,
            "cost_advantage": None,
            "efficient_scale": 2.4,
        },
        ai_summaries={
            "switching_costs": {"score": 0.68, "summary": "Contract terms provide moderate stickiness."},
            "network_effects": {"score": 0.70, "summary": "User community plateauing."},
            "intangibles": {"score": 0.65, "summary": "Brand awareness flat year over year."},
            "cost_advantage": {"score": 0.55, "summary": "Logistics costs rising due to fuel expenses."},
            "efficient_scale": {"score": 0.60, "summary": "Regional competitors gaining share."},
        },
        qualitative_notes={},
    )

    scorecard = builder.build(assessment)

    assert scorecard.overall_score == pytest.approx(64.0, abs=0.2)
    assert scorecard.moat_rating == "Narrow Moat"
    assert scorecard.dimensions["switching_costs"]["combined_score"] == pytest.approx(68.0, abs=0.1)
    assert scorecard.dimensions["cost_advantage"]["combined_score"] == pytest.approx(55.0, abs=0.1)


def test_ownership_trend_analyzer_flags_trends():
    analyzer = OwnershipTrendAnalyzer()
    history = [
        {"date": datetime(2024, 4, 30), "institutional": 64.0, "insider": 2.1},
        {"date": datetime(2024, 5, 31), "institutional": 65.5, "insider": 2.2},
        {"date": datetime(2024, 6, 30), "institutional": 66.8, "insider": 2.25},
        {"date": datetime(2024, 7, 31), "institutional": 68.1, "insider": 2.3},
    ]

    summary = analyzer.summarise(history)

    assert summary["institutional"]["trend"] == "increasing"
    assert summary["institutional"]["change_percentage"] == pytest.approx(6.4, abs=0.1)
    assert summary["insider"]["trend"] == "increasing"
    assert summary["alerts"] == []


def test_management_quality_analyzer_scores_high_quality():
    analyzer = ManagementQualityAnalyzer()
    metrics = {
        "roic_trend": [0.12, 0.15, 0.18],
        "capital_allocation": {
            "share_buybacks": True,
            "dividend_growth": True,
            "capex_focus": "growth",
        },
        "governance_flags": [],
        "tenure_years": 9,
        "insider_alignment": 0.04,
        "glassdoor_rating": 4.3,
    }
    qualitative = [
        "Management prioritised reinvestment while keeping leverage modest.",
        "Shareholder letters highlight disciplined capital allocation.",
    ]

    result = analyzer.evaluate(metrics, qualitative)

    assert result["score"] == pytest.approx(84.0, abs=0.5)
    assert result["rating"] == "High"
    assert any("capital allocation" in highlight.lower() for highlight in result["highlights"])


def test_management_quality_analyzer_detects_red_flags():
    analyzer = ManagementQualityAnalyzer()
    metrics = {
        "roic_trend": [0.18, 0.15, 0.11],
        "capital_allocation": {
            "share_buybacks": False,
            "dividend_growth": False,
            "capex_focus": "maintenance",
        },
        "governance_flags": ["accounting_restated", "executive_turnover"],
        "tenure_years": 2,
        "insider_alignment": 0.005,
        "glassdoor_rating": 2.9,
    }
    qualitative = ["Recent departures in finance leadership raise oversight concerns."]

    result = analyzer.evaluate(metrics, qualitative)

    assert result["score"] == pytest.approx(42.0, abs=0.5)
    assert result["rating"] == "Low"
    assert any("restated" in warning.lower() for warning in result["warnings"])
