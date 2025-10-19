from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, MutableMapping, Optional, Sequence

try:
    from fredapi import Fred  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Fred = None

import pandas as pd  # type: ignore

from ..analysis.epic4_macro import (
    ForecastAlignmentEngine,
    MacroDataPoint,
    MacroSeries,
    MacroSnapshotBuilder,
    RecessionSignalCalculator,
    SentimentTracker,
)
from .data_pipeline import SQLiteDataStore
from .keys import get_api_key


def _ensure_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class MacroSeriesConfig:
    series: Optional[str]
    frequency: str
    transform: Optional[str] = None
    provider: str = "fred"
    limit: int = 120
    fallback: Optional[str] = None


FRED_SERIES: Dict[str, MacroSeriesConfig] = {
    "gdp_growth": MacroSeriesConfig(
        series="A191RL1Q225SBEA", frequency="quarterly", transform=None, limit=40
    ),
    "cpi": MacroSeriesConfig(
        series="CPIAUCSL", frequency="monthly", transform="yoy_pct", limit=120
    ),
    "unemployment_rate": MacroSeriesConfig(
        series="UNRATE", frequency="monthly", transform=None, limit=120
    ),
    "fed_funds_rate": MacroSeriesConfig(
        series="FEDFUNDS", frequency="daily", transform=None, limit=365
    ),
    "yield_curve_spread": MacroSeriesConfig(
        series="T10Y2Y", frequency="daily", transform=None, limit=365
    ),
    "global_valuation_percentile": MacroSeriesConfig(
        series=None,
        frequency="monthly",
        provider="csv",
        fallback="global_valuation_percentile.csv",
    ),
    "institutional_flows": MacroSeriesConfig(
        series=None,
        frequency="weekly",
        provider="csv",
        fallback="institutional_flows.csv",
    ),
    "buffett_indicator": MacroSeriesConfig(
        series=None,
        frequency="quarterly",
        provider="csv",
        fallback="buffett_indicator.csv",
    ),
}


class MacroContextService:
    """Coordinate macro data ingestion and analytics for the evaluator."""

    def __init__(
        self,
        store: SQLiteDataStore,
        data_dir: Path,
        *,
        fred_api_key: Optional[str] = None,
    ) -> None:
        self.store = store
        self.data_dir = data_dir
        self.builder = MacroSnapshotBuilder(store)
        self.recession = RecessionSignalCalculator()
        self.sentiment = SentimentTracker()
        self.alignment = ForecastAlignmentEngine()

        resolved_key = fred_api_key or get_api_key("FRED_API_KEY")
        self._fred = None
        if resolved_key and Fred is not None:
            try:
                self._fred = Fred(api_key=resolved_key)
            except Exception:
                self._fred = None

    # ------------------------------------------------------------------ #
    # Refresh & Snapshot access

    def refresh(
        self,
        *,
        as_of: Optional[datetime] = None,
        overrides: Optional[MutableMapping[str, Sequence[MacroDataPoint]]] = None,
    ) -> Dict[str, Dict]:
        timestamp = _ensure_aware(as_of or datetime.now(timezone.utc))
        overrides = overrides or {}

        for series_id, config in FRED_SERIES.items():
            override_points = overrides.get(series_id)
            if override_points:
                points = list(override_points)
                provider = "override"
            else:
                points = self._collect_series(series_id, config)
                provider = config.provider
            if not points:
                continue
            macro_series = MacroSeries(
                series_id=series_id,
                frequency=config.frequency,
                provider=provider,
                points=points,
            )
            self.builder.ingest_series(macro_series, as_of=timestamp)
        return self.builder.build_snapshot(as_of=timestamp)

    def get_snapshot(self) -> Dict[str, Dict]:
        snapshot = self.store.load_macro_snapshot()
        if snapshot:
            return snapshot
        return {}

    def get_context(
        self,
        *,
        fundamentals_trends: MutableMapping[str, MutableMapping[str, Optional[float]]],
        ensure_fresh: bool = False,
    ) -> Dict[str, Dict]:
        if ensure_fresh and not self.get_snapshot():
            self.refresh()
        snapshot = self.get_snapshot()

        macro_series_map: Dict[str, List[MacroDataPoint]] = {}
        for series_id in (
            "unemployment_rate",
            "yield_curve_spread",
            "buffett_indicator",
        ):
            stored = self.store.load_macro_series(series_id)
            if stored:
                macro_series_map[series_id] = [
                    MacroDataPoint(_ensure_aware(row["date"]), float(row["value"]))
                    for row in stored
                    if row.get("value") is not None
                ]

        # Buffett indicator is not a FRED series by default; enrich if missing by deriving from snapshot.
        if "buffett_indicator" not in macro_series_map:
            buf_path = self.data_dir / "macro" / "buffett_indicator.csv"
            if buf_path.exists():
                macro_series_map["buffett_indicator"] = self._read_csv_series(buf_path)

        signals = self.recession.evaluate(macro_series_map)
        sentiment = self.sentiment.summarise(
            {
                key: self._safe_series_from_store(key)
                for key in ("global_valuation_percentile", "institutional_flows")
            }
        )
        alignment = self.alignment.align(snapshot, fundamentals_trends)

        return {
            "snapshot": snapshot,
            "recession_signals": signals,
            "sentiment": sentiment,
            "alignment": alignment,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers

    def _collect_series(
        self, series_id: str, config: MacroSeriesConfig
    ) -> List[MacroDataPoint]:
        if config.series and self._fred is not None:
            try:
                raw = self._fred.get_series(config.series)
                if raw is not None and not raw.empty:
                    return self._transform_series(raw, config)
            except Exception:
                pass
        if config.fallback:
            path = self.data_dir / "macro" / config.fallback
            if path.exists():
                return self._read_csv_series(path)
        return []

    def _transform_series(
        self, data: pd.Series, config: MacroSeriesConfig
    ) -> List[MacroDataPoint]:
        series = data.dropna()
        if series.empty:
            return []

        if config.transform == "yoy_pct":
            series = series.pct_change(periods=12) * 100
        elif config.transform == "mom_pct":
            series = series.pct_change(periods=1) * 100

        series = series.dropna().tail(config.limit)

        points: List[MacroDataPoint] = []
        for index, value in series.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if math.isnan(numeric):
                continue
            date = index.to_pydatetime() if hasattr(index, "to_pydatetime") else index
            date = _ensure_aware(date)
            points.append(MacroDataPoint(date, numeric))
        return points

    def _read_csv_series(self, path: Path) -> List[MacroDataPoint]:
        points: List[MacroDataPoint] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    date_raw = row.get("date") or row.get("Date")
                    value_raw = row.get("value") or row.get("Value")
                    if not date_raw or value_raw is None:
                        continue
                    try:
                        date = datetime.fromisoformat(str(date_raw))
                    except ValueError:
                        continue
                    try:
                        value = float(value_raw)
                    except (TypeError, ValueError):
                        continue
                    points.append(MacroDataPoint(_ensure_aware(date), value))
        except FileNotFoundError:
            return []
        return points

    def _safe_series_from_store(self, series_id: str) -> List[MacroDataPoint]:
        rows = self.store.load_macro_series(series_id)
        return [
            MacroDataPoint(_ensure_aware(row["date"]), float(row["value"]))
            for row in rows
            if row.get("value") is not None
        ]


__all__ = ["MacroContextService", "FRED_SERIES"]
