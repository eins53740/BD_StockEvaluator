"""
Helpers to prepare data and layout specifications for the desktop overview.

The functions in this module turn the detailed analysis payloads from
``StockAnalysisService`` into lightweight structures that the Streamlit UI
can render without duplicating business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..core.macro import MacroContextService
from ..core.service import StockAnalysisService


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_dict(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return dict(payload)
    try:
        return dict(payload.items())  # type: ignore[arg-type]
    except AttributeError:
        return dict(payload)  # type: ignore[arg-type]


def _extract_fundamentals(analysis: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "valuation": _as_dict(analysis.get("valuation_scorecard")),
        "profitability": _as_dict(analysis.get("profitability_snapshot")),
        "growth": _as_dict(analysis.get("growth_trends")),
        "intrinsic_values": _as_dict(analysis.get("intrinsic_value_models")),
    }


@dataclass(frozen=True)
class DashboardTickerOverview:
    ticker: str
    company_name: str
    verdict: Optional[str]
    fundamentals: Dict[str, Any] = field(default_factory=dict)
    technicals: Dict[str, Any] = field(default_factory=dict)
    macro: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DashboardSnapshot:
    tickers: List[DashboardTickerOverview]
    macro_snapshot: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tickers": [ticker.to_dict() for ticker in self.tickers],
            "macro_snapshot": dict(self.macro_snapshot),
            "generated_at": self.generated_at,
        }


def collect_dashboard_snapshot(
    tickers: Sequence[str],
    service: StockAnalysisService,
    *,
    macro_service: Optional[MacroContextService] = None,
    include_opinion: bool = False,
) -> DashboardSnapshot:
    seen: set[str] = set()
    entries: List[DashboardTickerOverview] = []

    for raw in tickers:
        ticker = str(raw or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        try:
            analysis = service.analyze(ticker, include_opinion=include_opinion)
        except Exception:
            continue

        entries.append(
            DashboardTickerOverview(
                ticker=analysis.get("ticker") or ticker,
                company_name=analysis.get("company_name")
                or analysis.get("ticker")
                or ticker,
                verdict=analysis.get("result"),
                fundamentals=_extract_fundamentals(analysis),
                technicals=_as_dict(analysis.get("technical_analysis")),
                macro=_as_dict(analysis.get("macro_context")),
                metrics=_as_dict(analysis.get("metrics")),
                generated_at=analysis.get("generated_at") or _now_iso(),
            )
        )

    macro_snapshot: Dict[str, Any] = {}
    if macro_service is not None:
        try:
            raw_snapshot = macro_service.get_snapshot()
            if raw_snapshot:
                macro_snapshot = dict(raw_snapshot)
        except AttributeError:
            try:
                raw_context = macro_service.get_context()  # type: ignore[arg-type]
                if raw_context:
                    macro_snapshot = dict(raw_context)
            except TypeError:
                macro_snapshot = {}
            except Exception:
                macro_snapshot = {}
        except Exception:
            macro_snapshot = {}

    return DashboardSnapshot(
        tickers=entries,
        macro_snapshot=macro_snapshot,
        generated_at=_now_iso(),
    )


def build_dashboard_layout_spec(snapshot: DashboardSnapshot) -> Dict[str, Any]:
    sections: List[Dict[str, Any]] = []
    for ticker in snapshot.tickers:
        sections.append(
            {
                "ticker": ticker.ticker,
                "company_name": ticker.company_name,
                "verdict": ticker.verdict,
                "metrics": dict(ticker.metrics),
                "tabs": [
                    {
                        "id": "fundamentals",
                        "label": "Fundamentals",
                        "payload": dict(ticker.fundamentals),
                    },
                    {
                        "id": "technicals",
                        "label": "Technicals",
                        "payload": dict(ticker.technicals),
                    },
                    {
                        "id": "macro",
                        "label": "Macro Context",
                        "payload": dict(ticker.macro),
                    },
                ],
            }
        )

    return {
        "title": "BD Finance Desktop Overview",
        "generated_at": snapshot.generated_at,
        "macro": dict(snapshot.macro_snapshot),
        "sections": sections,
    }


__all__ = [
    "DashboardSnapshot",
    "DashboardTickerOverview",
    "build_dashboard_layout_spec",
    "collect_dashboard_snapshot",
]
