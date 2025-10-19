from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


from bd_stockevaluator.reports.per_ticker import (
    TickerReport,
    compose_ticker_report,
    export_report_pdf,
    render_report_html,
)


def _analysis_payload() -> dict:
    return {
        "ticker": "ACME",
        "company_name": "Acme Incorporated",
        "result": "BUY",
        "flowchart_definition": "graph TD; A-->B; B-->C;",
        "valuation_scorecard": {"score": 7.2, "rating": "attractive"},
        "profitability_snapshot": {"roe": 0.18, "margin_stability": "strong"},
        "growth_trends": {"revenue_cagr": 0.12, "fcf_cagr": 0.10},
        "intrinsic_value_models": {
            "dcf": {"value": 155.00, "upside": 0.28},
            "graham": {"value": 142.00, "upside": 0.18},
        },
        "technical_analysis": {
            "signal": {"label": "Bullish", "score": 8},
            "momentum": {"score": 6},
            "chart": {
                "png": "c:/tmp/static/charts/acme.png",
                "json": "c:/tmp/static/charts/acme.json",
            },
        },
        "macro_context": {
            "snapshot": {"headline": "Soft landing"},
            "alignment": {"rates": "supportive"},
        },
        "qualitative_moat": {"overall": 4.1},
        "metrics": {"price": 120.55, "market_cap": 50_000_000_000},
        "generated_at": "2024-01-03T00:00:00Z",
    }


def test_compose_ticker_report_collects_sections() -> None:
    service = MagicMock()
    service.analyze.return_value = _analysis_payload()

    report = compose_ticker_report("acme", service=service)

    assert isinstance(report, TickerReport)
    assert report.ticker == "ACME"
    assert report.company_name == "Acme Incorporated"
    assert report.verdict == "BUY"
    assert report.fundamentals["valuation"]["rating"] == "attractive"
    assert report.fundamentals["growth"]["fcf_cagr"] == 0.10
    assert report.intrinsic_values["dcf"]["value"] == 155.00
    assert report.chart_png.endswith("static/charts/acme.png")
    assert report.flowchart_definition == "graph TD; A-->B; B-->C;"
    assert service.analyze.call_args[0][0] == "ACME"


def test_render_report_html_matches_fixture(tmp_path: Path) -> None:
    service = MagicMock()
    service.analyze.return_value = _analysis_payload()
    report = compose_ticker_report("ACME", service=service)

    html = render_report_html(report)
    expected = Path("tests/test_epic7_per_ticker_report_expected.html").read_text(
        encoding="utf-8"
    )

    assert html.strip() == expected.strip()


def test_export_report_pdf_uses_pdfkit_fallback(monkeypatch, tmp_path: Path) -> None:
    pdf_calls: dict[str, int] = {"count": 0}

    class BrokenWeasy:
        def __init__(self, string: str) -> None:
            raise RuntimeError("weasyprint failure")

        def write_pdf(self, path: str) -> None:  # pragma: no cover - never reached
            raise RuntimeError("weasyprint failure")

    def fake_from_string(html: str, path: str) -> None:
        pdf_calls["count"] += 1
        Path(path).write_text("pdfkit-output", encoding="utf-8")

    monkeypatch.setattr(
        "bd_stockevaluator.reports.per_ticker._WEASY_HTML", BrokenWeasy, raising=False
    )
    monkeypatch.setattr(
        "bd_stockevaluator.reports.per_ticker._PDFKIT",
        SimpleNamespace(from_string=fake_from_string),
        raising=False,
    )

    output_path = tmp_path / "report.pdf"
    result_path = export_report_pdf("<p>Hello</p>", output_path)

    assert result_path == output_path
    assert pdf_calls["count"] == 1
    assert output_path.read_text(encoding="utf-8") == "pdfkit-output"
