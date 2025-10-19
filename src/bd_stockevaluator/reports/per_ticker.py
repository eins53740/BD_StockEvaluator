"""
Per-ticker printable report utilities for Epic 7.

These helpers generate a compact one-page summary that blends fundamentals,
technicals, macro alignment, and the legacy Mermaid flow definition.  The
module is intentionally decoupled from Streamlit or Flask so that reports can
be rendered from CLI tools or scheduled jobs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from bd_stockevaluator.core.service import StockAnalysisService

try:  # Optional dependency
    from weasyprint import HTML as _WEASY_HTML  # type: ignore
except Exception:  # pragma: no cover - fallback path tested separately
    _WEASY_HTML = None

try:  # Optional dependency
    import pdfkit as _PDFKIT  # type: ignore
except Exception:  # pragma: no cover - fallback path tested separately
    _PDFKIT = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise_chart_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        full = Path(path)
        parts = [part for part in full.parts if part]  # normalise empty segments
        if "static" in parts:
            idx = parts.index("static")
            return "/".join(parts[idx:])
        return "/".join(parts)
    except Exception:
        return path.replace("\\", "/")


def _dict_or_empty(data: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {}
    if isinstance(data, dict):
        return dict(data)
    return dict(data.items())  # type: ignore[arg-type]


def _ordered_metrics(metrics: Mapping[str, Any]) -> Sequence[tuple[str, Any]]:
    order = {"price": 0}
    return sorted(metrics.items(), key=lambda kv: (order.get(kv[0], 1), kv[0]))


def _format_intrinsic_summary(
    models: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for model, payload in models.items():
        if not isinstance(payload, Mapping):
            continue
        value = payload.get("value")
        upside = payload.get("upside")
        summary[model] = {
            "value": float(value) if value is not None else None,
            "upside": float(upside) if upside is not None else None,
        }
    return summary


def _json_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True)
class TickerReport:
    ticker: str
    company_name: str
    verdict: Optional[str]
    generated_at: str
    fundamentals: Dict[str, Dict[str, Any]]
    intrinsic_values: Dict[str, Dict[str, Any]]
    technicals: Dict[str, Any]
    macro: Dict[str, Any]
    metrics: Dict[str, Any]
    flowchart_definition: str
    chart_png: Optional[str] = None
    chart_json: Optional[str] = None
    qualitative: Dict[str, Any] = field(default_factory=dict)


def compose_ticker_report(
    ticker: str,
    *,
    service: Optional[StockAnalysisService] = None,
    include_opinion: bool = False,
) -> TickerReport:
    resolved_service = service or StockAnalysisService()
    target = ticker.strip().upper()

    analysis = resolved_service.analyze(target, include_opinion=include_opinion)

    fundamentals = {
        "valuation": _dict_or_empty(analysis.get("valuation_scorecard")),
        "profitability": _dict_or_empty(analysis.get("profitability_snapshot")),
        "growth": _dict_or_empty(analysis.get("growth_trends")),
    }
    intrinsic_values = _format_intrinsic_summary(
        _dict_or_empty(analysis.get("intrinsic_value_models"))
    )
    technicals = _dict_or_empty(analysis.get("technical_analysis"))
    macro = _dict_or_empty(analysis.get("macro_context"))
    qualitative = _dict_or_empty(analysis.get("qualitative_moat"))
    metrics = _dict_or_empty(analysis.get("metrics"))
    chart_payload = _dict_or_empty(technicals.get("chart")) if technicals else {}

    generated_at = str(analysis.get("generated_at") or _now_iso())

    return TickerReport(
        ticker=analysis.get("ticker", target),
        company_name=analysis.get("company_name", target),
        verdict=analysis.get("result"),
        generated_at=generated_at,
        fundamentals=fundamentals,
        intrinsic_values=intrinsic_values,
        technicals=technicals,
        macro=macro,
        metrics=metrics,
        flowchart_definition=str(analysis.get("flowchart_definition") or ""),
        chart_png=_normalise_chart_path(chart_payload.get("png")),
        chart_json=_normalise_chart_path(chart_payload.get("json")),
        qualitative=qualitative,
    )


def render_report_html(report: TickerReport) -> str:
    metrics_rows = "\n            ".join(
        f"<div><dt>{key}</dt><dd>{value}</dd></div>"
        for key, value in _ordered_metrics(report.metrics)
    )

    fundamentals_html = "\n        ".join(
        f"""<article>
            <h3>{section.capitalize()}</h3>
            <pre>{_json_dumps(payload)}</pre>
        </article>"""
        for section, payload in (
            ("valuation", report.fundamentals.get("valuation", {})),
            ("profitability", report.fundamentals.get("profitability", {})),
            ("growth", report.fundamentals.get("growth", {})),
        )
    )

    intrinsic_entries = [
        f"<li>{model}: value {values['value']:.2f}"
        + (
            f" (upside {values['upside'] * 100:.1f}%)"
            if values.get("upside") is not None
            else ""
        )
        + "</li>"
        for model, values in sorted(report.intrinsic_values.items())
        if values.get("value") is not None
    ]
    if intrinsic_entries:
        intrinsic_list = "            " + "\n            ".join(intrinsic_entries)
    else:
        intrinsic_list = "            <li>No intrinsic models available.</li>"
    macro_payload = _json_dumps(report.macro) if report.macro else "{}"

    chart_img = (
        f'<img src="{report.chart_png}" alt="Technical chart for {report.ticker}" />'
        if report.chart_png
        else "<p>No technical chart available.</p>"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>BD Finance Ticker Report - {report.ticker}</title>
</head>
<body>
    <header>
        <h1>{report.company_name} ({report.ticker})</h1>
        <p class="verdict">Verdict: <strong>{report.verdict or "Unknown"}</strong></p>
        <p class="generated-at">Generated: {report.generated_at}</p>
    </header>
    <section id="key-metrics">
        <h2>Key Metrics</h2>
        <dl>
            {metrics_rows}
        </dl>
    </section>
    <section id="fundamentals">
        <h2>Fundamentals</h2>
        {fundamentals_html}
    </section>
    <section id="intrinsic-values">
        <h2>Intrinsic Value Summary</h2>
        <ul>
{intrinsic_list}
        </ul>
    </section>
    <section id="technicals">
        <h2>Technicals</h2>
        <p>Signal: {report.technicals.get('signal', {}).get('label', 'n/a')} (score {report.technicals.get('signal', {}).get('score', 'n/a')})</p>
        {chart_img}
    </section>
    <section id="macro">
        <h2>Macro Context</h2>
        <pre>{macro_payload}</pre>
    </section>
    <section id="flow">
        <h2>Mermaid Flow</h2>
        <pre class="mermaid">{report.flowchart_definition}</pre>
    </section>
</body>
</html>"""
    return html


def export_report_pdf(html: str, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if _WEASY_HTML is not None:
        try:
            _WEASY_HTML(string=html).write_pdf(str(output_path))
            return output_path
        except Exception:
            pass

    if _PDFKIT is not None:
        try:
            _PDFKIT.from_string(html, str(output_path))
            return output_path
        except Exception:
            pass

    output_path.write_text(html, encoding="utf-8")
    return output_path


def pdf_generation_available() -> bool:
    return _WEASY_HTML is not None or _PDFKIT is not None


__all__ = [
    "TickerReport",
    "compose_ticker_report",
    "render_report_html",
    "export_report_pdf",
    "pdf_generation_available",
]
