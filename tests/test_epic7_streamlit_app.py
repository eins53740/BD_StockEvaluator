from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from bd_stockevaluator.desktop.overview import render_dashboard
from bd_stockevaluator.ux.dashboard import DashboardSnapshot, DashboardTickerOverview
from bd_stockevaluator.reports.per_ticker import TickerReport
from bd_stockevaluator.ux.chart_explorer import ChartExplorerPayload


class _DummyContext:
    def __enter__(self) -> "_DummyContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _DummyColumn:
    def __init__(self) -> None:
        self.metric_calls: List[tuple[Any, Any]] = []

    def metric(self, label: Any, value: Any) -> None:
        self.metric_calls.append((label, value))


class _DummyTab(_DummyContext):
    pass


class DummyStreamlit:
    def __init__(self) -> None:
        self.page_configs: List[Dict[str, Any]] = []
        self.titles: List[str] = []
        self.subheaders: List[str] = []
        self.markdowns: List[str] = []
        self.captions: List[str] = []
        self.json_payloads: List[Dict[str, Any]] = []
        self.info_messages: List[str] = []
        self.tab_calls: List[List[str]] = []
        self.columns_counts: List[int] = []
        self.columns_history: List[List[_DummyColumn]] = []
        self.expanders: List[tuple[str, bool]] = []
        self.sidebar_value = "ACME,ZEUS"
        self.sidebar_captions: List[tuple[tuple[Any, ...], Dict[str, Any]]] = []
        self.download_payloads: List[Dict[str, Any]] = []
        self.plotly_calls: List[Any] = []

        self.sidebar = SimpleNamespace(
            text_input=self._sidebar_text_input,
            caption=self._sidebar_caption,
        )

    def _sidebar_text_input(self, *args: Any, **kwargs: Any) -> str:
        self.sidebar_text_input_args = (args, kwargs)
        return self.sidebar_value

    def _sidebar_caption(self, *args: Any, **kwargs: Any) -> None:
        self.sidebar_captions.append((args, kwargs))

    def set_page_config(self, **kwargs: Any) -> None:
        self.page_configs.append(kwargs)

    def title(self, text: str) -> None:
        self.titles.append(text)

    def subheader(self, text: str) -> None:
        self.subheaders.append(text)

    def markdown(self, text: str) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def json(self, payload: Dict[str, Any]) -> None:
        self.json_payloads.append(payload)

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def columns(self, count: int) -> List[_DummyColumn]:
        self.columns_counts.append(count)
        columns = [_DummyColumn() for _ in range(count)]
        self.columns_history.append(columns)
        return columns

    def tabs(self, labels: List[str]) -> List[_DummyTab]:
        self.tab_calls.append(labels)
        return [_DummyTab() for _ in labels]

    def expander(self, label: str, expanded: bool = False) -> _DummyContext:
        self.expanders.append((label, expanded))
        return _DummyContext()

    def download_button(self, label: str, **kwargs: Any) -> None:
        self.download_payloads.append({"label": label, **kwargs})

    def plotly_chart(self, figure: Any, use_container_width: bool = False) -> None:
        self.plotly_calls.append((figure, use_container_width))


@pytest.fixture
def dummy_snapshot() -> DashboardSnapshot:
    return DashboardSnapshot(
        tickers=[
            DashboardTickerOverview(
                ticker="ACME",
                company_name="Acme Corp",
                verdict="BUY",
                fundamentals={"valuation": {"score": 7.2}},
                technicals={"momentum": {"score": 6}},
                macro={"alignment": {"summary": "supportive"}},
                metrics={"price": 125.0},
                generated_at="2024-01-02T00:00:00Z",
            )
        ],
        macro_snapshot={"headline": "Soft landing"},
        generated_at="2024-02-01T12:00:00Z",
    )


def test_render_dashboard_uses_snapshot(monkeypatch, dummy_snapshot) -> None:
    dummy_streamlit = DummyStreamlit()
    monkeypatch.setattr("bd_stockevaluator.desktop.overview.st", dummy_streamlit)

    captured: Dict[str, Any] = {}

    report_calls: Dict[str, Any] = {}

    def fake_collect(
        tickers, service, *, macro_service=None, include_opinion=False
    ) -> DashboardSnapshot:
        captured["tickers"] = tickers
        captured["include_opinion"] = include_opinion
        captured["service"] = service
        captured["macro_service"] = macro_service
        return dummy_snapshot

    def fake_compose(ticker: str, *, service=None, include_opinion=False):
        report_calls.setdefault("tickers", []).append(
            (ticker, service, include_opinion)
        )
        return TickerReport(
            ticker=ticker,
            company_name=f"{ticker} Inc",
            verdict="BUY",
            generated_at="2024-01-02T00:00:00Z",
            fundamentals={"valuation": {}, "profitability": {}, "growth": {}},
            intrinsic_values={},
            technicals={},
            macro={},
            metrics={"price": 100},
            flowchart_definition="graph TD;A-->B;",
        )

    def fake_render(report: TickerReport) -> str:
        report_calls.setdefault("rendered", []).append(report.ticker)
        return f"<html><body>{report.ticker}</body></html>"

    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.collect_dashboard_snapshot", fake_collect
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.compose_ticker_report", fake_compose
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.render_report_html", fake_render
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.collect_chart_explorer_payload",
        lambda ticker, service, chart_json_root=None: ChartExplorerPayload(
            ticker="ACME",
            company_name="Acme Corp",
            fundamentals_history=[{"period": "FY2023", "pe": 22.0}],
            price_history=[{"date": "2024-01-01", "close": 150.0}],
            technical_figure_json={"data": [], "layout": {"title": "Chart"}},
        ),
    )

    service_stub = SimpleNamespace(macro_service="macro-service")

    result = render_dashboard(tickers=["acme"], service=service_stub)

    assert result is dummy_snapshot
    assert captured["tickers"] == ["ACME"]
    assert captured["include_opinion"] is False
    assert captured["service"] is service_stub
    assert captured["macro_service"] == "macro-service"
    assert report_calls["tickers"] == [("ACME", service_stub, False)]
    assert report_calls["rendered"] == ["ACME"]

    assert dummy_streamlit.titles[0] == "BD Finance Desktop Overview"
    assert dummy_streamlit.subheaders[0] == "Macro Dashboard"
    assert dummy_streamlit.json_payloads[0] == dummy_snapshot.macro_snapshot
    assert dummy_streamlit.json_payloads[1] == dummy_snapshot.tickers[0].fundamentals
    assert dummy_streamlit.tab_calls[0] == [
        "Fundamentals",
        "Technicals",
        "Macro Context",
        "Chart Explorer",
    ]
    assert dummy_streamlit.columns_counts[0] == 1
    assert dummy_streamlit.columns_history[0][0].metric_calls == [("price", 125.0)]
    chart_rendered = bool(dummy_streamlit.plotly_calls)
    if not chart_rendered:
        chart_rendered = len(dummy_streamlit.json_payloads) >= 3
    assert chart_rendered
    assert len(dummy_streamlit.download_payloads) == 1
    assert dummy_streamlit.download_payloads[0]["file_name"] == "acme_report.html"
    assert (
        dummy_streamlit.download_payloads[0]["data"]
        == b"<html><body>ACME</body></html>"
    )


def test_render_dashboard_adds_pdf_download_when_available(
    monkeypatch, dummy_snapshot, tmp_path: Path
) -> None:
    dummy_streamlit = DummyStreamlit()
    monkeypatch.setattr("bd_stockevaluator.desktop.overview.st", dummy_streamlit)

    def fake_collect(
        tickers, service, *, macro_service=None, include_opinion=False
    ) -> DashboardSnapshot:
        return dummy_snapshot

    def fake_compose(ticker: str, *, service=None, include_opinion=False):
        return TickerReport(
            ticker=ticker,
            company_name="Acme Inc",
            verdict="BUY",
            generated_at="2024-01-02T00:00:00Z",
            fundamentals={"valuation": {}, "profitability": {}, "growth": {}},
            intrinsic_values={},
            technicals={},
            macro={},
            metrics={"price": 100},
            flowchart_definition="graph TD;A-->B;",
        )

    def fake_render(report: TickerReport) -> str:
        return "<html><body>ACME</body></html>"

    def fake_pdf_available() -> bool:
        return True

    def fake_export(html: str, output_path: Path) -> Path:
        output_path.write_bytes(b"%PDF-1.4 fake")
        return output_path

    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.collect_dashboard_snapshot", fake_collect
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.compose_ticker_report", fake_compose
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.render_report_html", fake_render
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.pdf_generation_available",
        fake_pdf_available,
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.collect_chart_explorer_payload",
        lambda ticker, service, chart_json_root=None: ChartExplorerPayload(
            ticker="ACME",
            company_name="Acme Corp",
            fundamentals_history=[{"period": "FY2023", "pe": 22.0}],
            price_history=[{"date": "2024-01-01", "close": 150.0}],
            technical_figure_json={"data": [], "layout": {"title": "Chart"}},
        ),
    )
    monkeypatch.setattr(
        "bd_stockevaluator.desktop.overview.export_report_pdf",
        fake_export,
    )

    service_stub = SimpleNamespace(macro_service="macro")
    render_dashboard(tickers=["ACME"], service=service_stub)

    assert dummy_streamlit.tab_calls[0][-1] == "Chart Explorer"
    chart_rendered = bool(dummy_streamlit.plotly_calls)
    if not chart_rendered:
        chart_rendered = len(dummy_streamlit.json_payloads) >= 3
    assert chart_rendered
    assert len(dummy_streamlit.download_payloads) == 2
    html_payload, pdf_payload = dummy_streamlit.download_payloads
    assert html_payload["mime"] == "text/html"
    assert pdf_payload["mime"] == "application/pdf"
    assert pdf_payload["file_name"] == "acme_report.pdf"
    assert pdf_payload["data"] == b"%PDF-1.4 fake"
