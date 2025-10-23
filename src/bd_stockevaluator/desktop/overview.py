"""
Streamlit dashboard combining fundamentals, technicals, and macro context.

The implementation intentionally leans on the ``ux.dashboard`` helpers so the
layout stays declarative and easy to snapshot test.
"""

from __future__ import annotations

import json
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import List, Optional, Sequence

try:  # Streamlit is an optional dependency at runtime
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - exercised via tests
    st = None  # type: ignore[assignment]

try:  # Plotly optional
    import plotly.graph_objects as go
    import plotly.io as pio
except Exception:  # pragma: no cover - graceful fallback
    go = None
    pio = None

try:
    # Prefer absolute imports when running as a package
    from bd_stockevaluator.core.service import STATIC_DIR, StockAnalysisService
    from bd_stockevaluator.reports.per_ticker import (
        compose_ticker_report,
        export_report_pdf,
        pdf_generation_available,
        render_report_html,
    )
    from bd_stockevaluator.ux.dashboard import (
        DashboardSnapshot,
        build_dashboard_layout_spec,
        collect_dashboard_snapshot,
    )
    from bd_stockevaluator.ux.chart_explorer import collect_chart_explorer_payload
except Exception:  # pragma: no cover - fallback for direct script execution
    # Fallback to relative imports when package context is available
    from ..core.service import STATIC_DIR, StockAnalysisService
    from ..reports.per_ticker import (
        compose_ticker_report,
        export_report_pdf,
        pdf_generation_available,
        render_report_html,
    )
    from ..ux.dashboard import (
        DashboardSnapshot,
        build_dashboard_layout_spec,
        collect_dashboard_snapshot,
    )
    from ..ux.chart_explorer import collect_chart_explorer_payload


DEFAULT_TICKERS = ("AAPL", "MSFT", "GOOGL")


def _sanitize_tickers(raw: Sequence[str]) -> List[str]:
    return [token.strip().upper() for token in raw if token and token.strip()]


def _resolve_tickers(sidebar_value: str) -> List[str]:
    if not sidebar_value:
        return list(DEFAULT_TICKERS)
    tokens = [piece.strip() for piece in sidebar_value.replace("\n", ",").split(",")]
    sanitized = _sanitize_tickers(tokens)
    return sanitized or list(DEFAULT_TICKERS)


def _render_macro_section(snapshot: DashboardSnapshot) -> None:
    if not snapshot.macro_snapshot:
        st.info("Macro dashboard will appear after the first analysis refresh.")
        return
    st.subheader("Macro Dashboard")
    with st.expander("Macro snapshot", expanded=False):
        st.json(snapshot.macro_snapshot)


def _render_ticker_sections(snapshot_spec: dict, service: StockAnalysisService) -> None:
    for section in snapshot_spec["sections"]:
        st.markdown(f"### {section['ticker']} · {section['company_name']}")
        if section.get("verdict"):
            st.caption(f"Verdict: **{section['verdict']}**")

        metrics = section.get("metrics") or {}
        if metrics:
            columns = st.columns(min(4, max(1, len(metrics))))
            for col, (label, value) in zip(columns, metrics.items()):
                with suppress(Exception):
                    col.metric(label, value)

        tab_labels = [tab["label"] for tab in section["tabs"]] + ["Chart Explorer"]
        tabs = st.tabs(tab_labels)
        base_tabs = tabs[:-1]
        for streamlit_tab, tab_spec in zip(base_tabs, section["tabs"]):
            with streamlit_tab:
                payload = tab_spec.get("payload") or {}
                if payload:
                    st.json(payload)
                else:
                    st.info("Awaiting data for this tab.")

        with tabs[-1]:
            _render_chart_explorer_tab(section["ticker"], service)

        report_error: Optional[str] = None
        report_html: Optional[str] = None
        report_pdf: Optional[bytes] = None
        pdf_error: Optional[str] = None
        try:
            report = compose_ticker_report(
                section["ticker"], service=service, include_opinion=False
            )
            report_html = render_report_html(report)
            if report_html and pdf_generation_available():
                tmp_path: Optional[Path] = None
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as tmp_file:
                        tmp_path = Path(tmp_file.name)
                    pdf_output = export_report_pdf(report_html, tmp_path)
                    report_pdf = pdf_output.read_bytes()
                except Exception as pdf_exc:
                    pdf_error = str(pdf_exc)
                finally:
                    if tmp_path and tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - guarded downstream
            report_error = str(exc)

        with st.expander("Printable report"):
            if report_html:
                st.download_button(
                    "Download HTML report",
                    data=report_html.encode("utf-8"),
                    file_name=f"{section['ticker'].lower()}_report.html",
                    mime="text/html",
                    key=f"download-html-{section['ticker']}",
                )
                if report_pdf is not None:
                    st.download_button(
                        "Download PDF report",
                        data=report_pdf,
                        file_name=f"{section['ticker'].lower()}_report.pdf",
                        mime="application/pdf",
                        key=f"download-pdf-{section['ticker']}",
                    )
                elif pdf_error:
                    st.warning(
                        f"PDF export unavailable for {section['ticker']}: {pdf_error}"
                    )
            else:
                st.warning(
                    f"Report unavailable for {section['ticker']}: {report_error or 'unknown error'}"
                )


def _build_ratio_figure(history: List[dict]) -> Optional["go.Figure"]:
    if not history or go is None:
        return None
    sorted_history = sorted(
        history,
        key=lambda item: item.get("as_of") or item.get("period") or "",
    )
    x_values = [
        entry.get("as_of") or entry.get("period") or f"Point {index + 1}"
        for index, entry in enumerate(sorted_history)
    ]
    fig = go.Figure()
    metrics = [
        ("pe", "P/E"),
        ("peg", "PEG"),
        ("fcf_yield", "FCF Yield"),
        ("roe", "ROE"),
    ]
    for key, label in metrics:
        y_values = [entry.get(key) for entry in sorted_history]
        if any(value is not None for value in y_values):
            fig.add_trace(
                go.Scatter(x=x_values, y=y_values, name=label, mode="lines+markers")
            )
    if not fig.data:
        return None
    fig.update_layout(
        title="Ratio History",
        xaxis_title="Period",
        yaxis_title="Value",
        template="plotly_white",
    )
    return fig


def _build_price_figure(history: List[dict]) -> Optional["go.Figure"]:
    if not history or go is None:
        return None
    sorted_history = sorted(history, key=lambda item: item.get("date") or "")
    dates = [entry.get("date") for entry in sorted_history]
    closes = [entry.get("close") for entry in sorted_history]
    if not any(closes):
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=closes, name="Close", mode="lines"))
    fig.update_layout(
        title="Price History",
        xaxis_title="Date",
        yaxis_title="Close Price",
        template="plotly_white",
    )
    return fig


def _render_chart_explorer_tab(
    ticker: str,
    service: StockAnalysisService,
) -> None:
    try:
        payload = collect_chart_explorer_payload(
            ticker,
            service,
            chart_json_root=STATIC_DIR,
        )
    except Exception as exc:  # pragma: no cover - guarded downstream
        st.warning(f"Chart Explorer unavailable for {ticker}: {exc}")
        return

    ratio_fig = _build_ratio_figure(payload.fundamentals_history)
    if ratio_fig is not None:
        st.plotly_chart(ratio_fig, use_container_width=True)
    elif payload.fundamentals_history:
        st.json(payload.fundamentals_history)
    else:
        st.info("No fundamentals history available yet.")

    price_fig = _build_price_figure(payload.price_history)
    if price_fig is not None:
        st.plotly_chart(price_fig, use_container_width=True)
    elif payload.price_history:
        st.json(payload.price_history)

    technical_figure = None
    if pio is not None and payload.technical_figure_json:
        try:
            technical_figure = pio.from_json(json.dumps(payload.technical_figure_json))
        except Exception:
            technical_figure = None

    if technical_figure is not None:
        st.plotly_chart(technical_figure, use_container_width=True)
    else:
        st.info("Technical chart unavailable.")


def render_dashboard(
    tickers: Optional[Sequence[str]] = None,
    *,
    service: Optional[StockAnalysisService] = None,
) -> DashboardSnapshot:
    """
    Render the desktop overview dashboard and return the computed snapshot.
    """

    if st is None:  # pragma: no cover - Streamlit missing in runtime
        raise RuntimeError("Streamlit is required to render the desktop overview.")

    st.set_page_config(
        page_title="BD Finance Desktop Overview",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("BD Finance Desktop Overview")

    resolved_service = service or StockAnalysisService()

    sidebar_value = st.sidebar.text_input(
        "Comma separated tickers",
        value=",".join(tickers or DEFAULT_TICKERS),
        help="Enter up to 10 tickers. Duplicates and blanks are ignored.",
    )
    resolved_tickers = _resolve_tickers(
        sidebar_value if tickers is None else ",".join(tickers)
    )

    snapshot = collect_dashboard_snapshot(
        resolved_tickers,
        resolved_service,
        macro_service=resolved_service.macro_service,
        include_opinion=False,
    )

    layout_spec = build_dashboard_layout_spec(snapshot)

    st.sidebar.caption(f"Generated at {layout_spec['generated_at']}")
    _render_macro_section(snapshot)
    _render_ticker_sections(layout_spec, resolved_service)

    return snapshot


def main() -> None:
    """Entrypoint compatible with ``streamlit run -m bd_stockevaluator.desktop.overview``."""
    render_dashboard()


if __name__ == "__main__":  # pragma: no cover
    main()
