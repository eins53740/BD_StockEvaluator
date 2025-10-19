"""
User-experience helpers for desktop and cross-platform surfaces.

The ``ux`` package complements the core analysis modules by providing
presentation-friendly structures that higher-level interfaces (e.g.
Streamlit dashboards) can consume without reimplementing extraction logic.
"""

from .dashboard import (
    DashboardSnapshot,
    DashboardTickerOverview,
    build_dashboard_layout_spec,
    collect_dashboard_snapshot,
)
from .chart_explorer import ChartExplorerPayload, collect_chart_explorer_payload

__all__ = [
    "DashboardSnapshot",
    "DashboardTickerOverview",
    "build_dashboard_layout_spec",
    "collect_dashboard_snapshot",
    "ChartExplorerPayload",
    "collect_chart_explorer_payload",
]
