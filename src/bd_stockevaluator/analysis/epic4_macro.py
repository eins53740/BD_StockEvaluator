from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, MutableMapping, Optional, Sequence

from ..core.data_pipeline import SQLiteDataStore, _to_iso


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class MacroDataPoint:
    date: datetime
    value: float


@dataclass(frozen=True)
class MacroSeries:
    series_id: str
    frequency: str
    provider: Optional[str]
    points: Sequence[MacroDataPoint]


class MacroSnapshotBuilder:
    """Persist macro series and produce dashboard-friendly summaries."""

    def __init__(self, store: SQLiteDataStore) -> None:
        self.store = store
        self._series_meta: Dict[str, Dict[str, Optional[str]]] = {}

    def ingest_series(
        self, series: MacroSeries, *, as_of: Optional[datetime] = None
    ) -> None:
        if not series.points:
            return
        ingested_at = _ensure_aware(as_of or datetime.now(timezone.utc))
        payload = [
            {"date": point.date, "value": point.value}
            for point in sorted(series.points, key=lambda p: p.date)
        ]
        self.store.save_macro_series(
            series.series_id,
            payload,
            frequency=series.frequency,
            provider=series.provider,
            ingested_at=ingested_at,
        )
        self._series_meta[series.series_id] = {
            "frequency": series.frequency,
            "provider": series.provider,
        }

    def build_snapshot(self, *, as_of: Optional[datetime] = None) -> Dict[str, Dict]:
        snapshot_time = _ensure_aware(as_of or datetime.now(timezone.utc))
        dashboard: Dict[str, Dict[str, object]] = {}

        for series_id, meta in self._series_meta.items():
            records = self.store.load_macro_series(series_id)
            if not records:
                continue
            latest = records[-1]
            previous = records[-2] if len(records) > 1 else None
            change = (
                latest["value"] - previous["value"]
                if previous
                and latest["value"] is not None
                and previous["value"] is not None
                else 0.0
            )
            trend = _describe_trend(series_id, change)
            dashboard[series_id] = {
                "latest": {
                    "value": latest["value"],
                    "date": latest["date"],
                    "provider": latest.get("provider") or meta.get("provider"),
                },
                "previous": previous,
                "change": change,
                "trend": trend,
                "frequency": meta.get("frequency"),
            }

        snapshot = {
            "as_of": _to_iso(snapshot_time),
            "dashboard": dashboard,
        }
        self.store.save_macro_snapshot(snapshot_time, snapshot)
        return snapshot


def _describe_trend(series_id: str, delta: float) -> str:
    threshold = 0.01
    if abs(delta) <= threshold:
        return "stable"
    cooling_series = {"gdp_growth", "cpi", "core_cpi", "ppi", "inflation_expectations"}
    if series_id in cooling_series:
        return "heating" if delta > 0 else "cooling"
    if series_id in {"yield_curve_spread"}:
        return "steepening" if delta > 0 else "flattening"
    return "rising" if delta > 0 else "falling"


class RecessionSignalCalculator:
    """Derive recession alert signals from macro time series."""

    def evaluate(
        self, series_map: MutableMapping[str, Sequence[MacroDataPoint]]
    ) -> Dict[str, Dict[str, object]]:
        sahm = self._sahm_rule(series_map.get("unemployment_rate", ()))
        curve = self._yield_curve(series_map.get("yield_curve_spread", ()))
        buffett = self._buffett_indicator(series_map.get("buffett_indicator", ()))
        return {
            "sahm_rule": sahm,
            "yield_curve_inversion": curve,
            "buffett_indicator": buffett,
        }

    @staticmethod
    def _sahm_rule(points: Sequence[MacroDataPoint]) -> Dict[str, object]:
        if len(points) < 3:
            return {
                "triggered": False,
                "gap": 0.0,
                "latest_average": None,
                "min_average": None,
            }
        sorted_points = sorted(points, key=lambda p: p.date)
        trailing_avgs: List[float] = []
        for idx in range(2, len(sorted_points)):
            window = sorted_points[idx - 2 : idx + 1]
            trailing_avgs.append(sum(point.value for point in window) / 3)
        latest_avg = trailing_avgs[-1]
        recent_window = (
            trailing_avgs[-12:] if len(trailing_avgs) >= 12 else trailing_avgs
        )
        min_avg = min(recent_window) if recent_window else latest_avg
        gap = latest_avg - min_avg
        return {
            "triggered": gap >= 0.5,
            "gap": round(gap, 3),
            "latest_average": round(latest_avg, 3),
            "min_average": round(min_avg, 3),
        }

    @staticmethod
    def _yield_curve(points: Sequence[MacroDataPoint]) -> Dict[str, object]:
        if not points:
            return {"inverted": False, "latest": None, "negative_streak": 0}
        sorted_points = sorted(points, key=lambda p: p.date)
        latest_value = sorted_points[-1].value
        streak = 0
        for point in reversed(sorted_points):
            if point.value < 0:
                streak += 1
            else:
                break
        return {
            "inverted": latest_value < 0,
            "latest": round(latest_value, 3),
            "negative_streak": streak,
        }

    @staticmethod
    def _buffett_indicator(points: Sequence[MacroDataPoint]) -> Dict[str, object]:
        if not points:
            return {"stretched": False, "latest": None}
        latest = sorted(points, key=lambda p: p.date)[-1].value
        return {
            "stretched": latest >= 1.35,
            "latest": round(latest, 3),
        }


class SentimentTracker:
    """Combine valuation and flow metrics into a sentiment regime."""

    def summarise(
        self, series_map: MutableMapping[str, Sequence[MacroDataPoint]]
    ) -> Dict[str, object]:
        valuation_state = "neutral"
        valuation_latest = None
        valuations = series_map.get("global_valuation_percentile", ())
        if valuations:
            valuations_sorted = sorted(valuations, key=lambda p: p.date)
            valuation_latest = valuations_sorted[-1].value
            if valuation_latest >= 80:
                valuation_state = "stretched"
            elif valuation_latest <= 40:
                valuation_state = "discounted"

        flow_trend = "mixed"
        flows = series_map.get("institutional_flows", ())
        flow_latest = None
        if flows:
            flows_sorted = sorted(flows, key=lambda p: p.date)
            flow_latest = flows_sorted[-1].value
            tail = flows_sorted[-4:] if len(flows_sorted) >= 4 else flows_sorted
            tail_avg = sum(point.value for point in tail) / len(tail)
            if tail_avg <= -0.25 or flow_latest <= -0.25:
                flow_trend = "outflows"
            elif tail_avg >= 0.25 or flow_latest >= 0.25:
                flow_trend = "inflows"

        regime = "neutral"
        if valuation_state == "stretched" and flow_trend == "outflows":
            regime = "risk_off"
        elif valuation_state == "discounted" and flow_trend == "inflows":
            regime = "risk_on"

        return {
            "valuation_state": valuation_state,
            "flow_trend": flow_trend,
            "regime": regime,
            "valuation_latest": valuation_latest,
            "flow_latest": flow_latest,
        }


class ForecastAlignmentEngine:
    """Assess how macro momentum aligns with company fundamentals."""

    def align(
        self,
        macro_snapshot: MutableMapping[str, Dict[str, Dict[str, object]]],
        fundamentals_trends: MutableMapping[str, MutableMapping[str, float]],
    ) -> Dict[str, object]:
        insights: List[str] = []
        risk_bias = "balanced"

        dashboard = macro_snapshot.get("dashboard", {})
        revenue_trend = fundamentals_trends.get("revenue_growth", {}).get("trend")
        eps_trend = fundamentals_trends.get("eps_growth", {}).get("trend")
        fcf_trend = fundamentals_trends.get("fcf_growth", {}).get("trend")

        fed = dashboard.get("fed_funds_rate")
        if fed and fed.get("trend") == "rising":
            if revenue_trend is not None and revenue_trend < 0:
                insights.append(
                    "Rising rates coincide with revenue contraction — monitor financing costs."
                )
                risk_bias = "macro_headwinds"
            else:
                insights.append(
                    "Rising rates have not derailed top-line momentum so far."
                )

        gdp = dashboard.get("gdp_growth")
        if gdp and gdp.get("trend") == "cooling":
            if revenue_trend is not None and revenue_trend < 0:
                insights.append(
                    "Cooling GDP growth lines up with weakening company revenues."
                )
                risk_bias = "macro_headwinds"
            elif revenue_trend is not None and revenue_trend > 0:
                insights.append("Company is outgrowing a cooling macro backdrop.")

        cpi = dashboard.get("cpi")
        if (
            cpi
            and cpi.get("trend") == "cooling"
            and fcf_trend is not None
            and fcf_trend > 0
        ):
            insights.append(
                "Disinflation plus improving free cash flow support margin resilience."
            )
            if risk_bias != "macro_headwinds":
                risk_bias = "macro_tailwinds"

        eps_note_added = False
        if eps_trend is not None:
            fed_trend = fed.get("trend") if fed else None
            if (
                fed_trend == "rising"
                and eps_trend < 0
                and "macro_headwinds" != risk_bias
            ):
                insights.append("Earnings under pressure amid tighter monetary policy.")
                risk_bias = "macro_headwinds"
                eps_note_added = True
        if (
            fcf_trend is not None
            and fcf_trend < 0
            and risk_bias == "balanced"
            and not eps_note_added
        ):
            insights.append("Free cash flow softening despite neutral macro reads.")

        if not insights:
            insights.append(
                "Macro alignment appears balanced with no clear headwinds or tailwinds."
            )

        return {
            "insights": insights,
            "risk_bias": risk_bias,
        }


__all__ = [
    "MacroDataPoint",
    "MacroSeries",
    "MacroSnapshotBuilder",
    "RecessionSignalCalculator",
    "SentimentTracker",
    "ForecastAlignmentEngine",
]
