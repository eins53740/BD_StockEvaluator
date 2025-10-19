"""
Automated portfolio reporting utilities for Epic 6.

The goal is to transform portfolio snapshots and analytics into artefacts that
can be distributed via email or stored as PDFs.  The implementation favours
deterministic behaviour and filesystem-side effects that are easy to assert in
tests without reaching external services.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

from bd_stockevaluator.core.portfolio import PortfolioSnapshot
from bd_stockevaluator.core.portfolio_performance import (
    compute_performance_metrics,
)
from bd_stockevaluator.core.watchlist import WatchlistAlert


@dataclass(frozen=True)
class PortfolioDigest:
    """Composite artefact combining rendered content and metadata."""

    snapshot: PortfolioSnapshot
    metrics: Mapping[str, float]
    alerts: Sequence[str]
    watchlist_alerts: Sequence[WatchlistAlert]
    macro_context: Mapping[str, Any]
    html: str
    email_subject: str
    email_body: str
    pdf_path: Path


def _default_series(
    snapshot: PortfolioSnapshot,
) -> pd.Series:
    historical_value = snapshot.total_cost or snapshot.total_value
    start_date = snapshot.as_of - dt.timedelta(days=365)
    return pd.Series(
        [historical_value, snapshot.total_value],
        index=pd.to_datetime([start_date, snapshot.as_of]),
    )


def _render_html(
    snapshot: PortfolioSnapshot,
    metrics: Mapping[str, float],
    alerts: Sequence[str],
    macro_context: Mapping[str, Any],
) -> str:
    sector_rows = "\n".join(
        f"<tr><td>{sector}</td><td>{weight:.2%}</td></tr>"
        for sector, weight in sorted(snapshot.sector_exposure.items())
    )
    alerts_html = (
        "<ul>" + "".join(f"<li>{alert}</li>" for alert in alerts) + "</ul>"
        if alerts
        else "<p>No active alerts.</p>"
    )
    macro_headline = macro_context.get("headline", "Macro summary unavailable.")
    macro_details = macro_context.get("indicators", {})
    macro_rows = "\n".join(
        f"<li>{name}: {value}</li>" for name, value in macro_details.items()
    )

    return (
        "<section>"
        "<h1>BD Portfolio Automation</h1>"
        f"<p>Date: {snapshot.as_of:%Y-%m-%d}</p>"
        f"<p>Total Value: {snapshot.total_value:,.2f} {snapshot.base_currency}</p>"
        f"<p>Total Gain: {snapshot.total_gain:,.2f} {snapshot.base_currency}</p>"
        "<h2>Performance</h2>"
        f"<p>CAGR: {metrics['cagr']:.2%} vs Benchmark {metrics['benchmark_cagr']:.2%}</p>"
        f"<p>Alpha: {metrics['alpha']:.2%} | Beta: {metrics['beta']:.2f}</p>"
        f"<p>Beta-adjusted Return: {metrics['beta_adjusted_return']:.2%}</p>"
        "<h2>Sector Exposure</h2>"
        "<table><thead><tr><th>Sector</th><th>Weight</th></tr></thead>"
        f"<tbody>{sector_rows}</tbody></table>"
        "<h2>Alerts</h2>"
        f"{alerts_html}"
        "<h2>Macro Context</h2>"
        f"<p>{macro_headline}</p>"
        f"<ul>{macro_rows}</ul>"
        "</section>"
    )


def _render_email_body(
    snapshot: PortfolioSnapshot,
    metrics: Mapping[str, float],
    alerts: Sequence[str],
) -> str:
    lines = [
        f"BD Portfolio Automation - {snapshot.as_of:%Y-%m-%d}",
        f"Total Value: {snapshot.total_value:,.2f} {snapshot.base_currency}",
        f"CAGR: {metrics['cagr']:.2%}",
        f"Alpha vs Benchmark: {metrics['alpha']:.2%}",
    ]
    lines.append("Top Holdings:")
    for position in sorted(
        snapshot.positions, key=lambda pos: pos.weight, reverse=True
    )[:5]:
        lines.append(
            f"  - {position.ticker}: {position.current_value:,.2f} "
            f"{snapshot.base_currency} ({position.weight:.2%})"
        )
    if alerts:
        lines.append("Alerts:")
        lines.extend(f"  - {alert}" for alert in alerts)
    else:
        lines.append("Alerts: none triggered.")
    return "\n".join(lines)


def _write_pdf(path: Path, html: str) -> None:
    """
    Persist rendered content using a minimal PDF placeholder.

    Real deployments can substitute this helper with a true HTML-to-PDF
    conversion. For the automated tests we simply store the HTML payload as
    UTF-8 text under a ``.pdf`` extension.
    """

    path.write_text(html, encoding="utf-8")


def generate_portfolio_report(
    snapshot: PortfolioSnapshot,
    *,
    portfolio_series: Optional[pd.Series] = None,
    benchmark_series: Optional[pd.Series] = None,
    alerts: Optional[Iterable[Any]] = None,
    macro_context: Optional[Mapping[str, Any]] = None,
    output_dir: Optional[Path] = None,
) -> PortfolioDigest:
    """
    Build the automated portfolio report artefacts for a given snapshot.
    """

    display_alerts, structured_alerts = _normalise_alerts(alerts)
    macro_context = macro_context or {}

    effective_portfolio_series = (
        portfolio_series if portfolio_series is not None else _default_series(snapshot)
    )
    if benchmark_series is None:
        benchmark_series = effective_portfolio_series * 0.95

    metrics = compute_performance_metrics(effective_portfolio_series, benchmark_series)

    html = _render_html(snapshot, metrics, display_alerts, macro_context)
    email_subject = f"BD Portfolio Digest - {snapshot.as_of:%Y-%m-%d}"
    email_body = _render_email_body(snapshot, metrics, display_alerts)

    target_dir = Path(output_dir or "Portfolio")
    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = target_dir / f"portfolio_report_{snapshot.as_of:%Y%m%d}.pdf"
    _write_pdf(pdf_path, html)

    return PortfolioDigest(
        snapshot=snapshot,
        metrics=metrics,
        alerts=display_alerts,
        watchlist_alerts=structured_alerts,
        macro_context=macro_context,
        html=html,
        email_subject=email_subject,
        email_body=email_body,
        pdf_path=pdf_path,
    )


def _normalise_alerts(
    alerts: Optional[Iterable[Any]],
) -> Tuple[List[str], List[WatchlistAlert]]:
    display: List[str] = []
    structured: List[WatchlistAlert] = []
    for alert in alerts or []:
        if isinstance(alert, WatchlistAlert):
            structured.append(alert)
            summary = ", ".join(alert.triggered_rules) or "Conditions met"
            display.append(f"{alert.ticker}: {summary}")
        else:
            display.append(str(alert))
    return display, structured


__all__ = ["PortfolioDigest", "generate_portfolio_report"]
