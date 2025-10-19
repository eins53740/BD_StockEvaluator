from __future__ import annotations

import datetime as dt
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from bd_stockevaluator.core.portfolio import PortfolioSnapshot
from bd_stockevaluator.core.watchlist import WatchlistAlert
from bd_stockevaluator.reports import daily_report
from bd_stockevaluator.reports.portfolio_automation import PortfolioDigest


@pytest.fixture
def daily_report_module(tmp_path, monkeypatch):
    module = importlib.reload(daily_report)

    # Point the script helpers to a disposable workspace
    monkeypatch.setattr(module, "CURRENT_DIR", tmp_path)
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "api_keys.txt").write_text("api_key_demo=123\n", encoding="utf-8")
    (config_dir / "sp500_tickers.txt").write_text("AAPL,MSFT", encoding="utf-8")
    (config_dir / "my_tickers_y.txt").write_text("MSFT,AAPL", encoding="utf-8")
    (config_dir / "portfolio.csv").write_text(
        "ticker,quantity,buy_price,buy_date,currency\n" "AAPL,1,100,2024-01-01,USD\n",
        encoding="utf-8",
    )

    (tmp_path / "fundamentals").mkdir()

    return module


def test_daily_report_invokes_sections(daily_report_module, monkeypatch, tmp_path):
    module = daily_report_module

    calls: list[str] = []
    email_payload = {}

    def fake_prices(*args, **kwargs):
        calls.append("prices")
        return "<p>prices</p>"

    def fake_fundamentals(*args, **kwargs):
        calls.append("fundamentals")

    def fake_my_holdings(*args, **kwargs):
        calls.append("my_holdings")
        return "<p>holdings</p>"

    def fake_portfolio_automation(*args, **kwargs):
        calls.append("portfolio_automation")
        return SimpleNamespace(
            pdf_path=Path(tmp_path / "portfolio_report.pdf"),
            html="<p>automation</p>",
            email_body="automation body",
            email_subject="Portfolio Digest",
        )

    def fake_send_email(*, xlsx_file=None, body_data=None, attachments=None):
        calls.append("send_email")
        email_payload["xlsx_file"] = xlsx_file
        email_payload["body_data"] = body_data
        email_payload["attachments"] = attachments

    monkeypatch.setattr(module, "prices", fake_prices)
    monkeypatch.setattr(module, "fundamentals", fake_fundamentals)
    monkeypatch.setattr(module, "my_holdings", fake_my_holdings)
    monkeypatch.setattr(module, "portfolio_automation", fake_portfolio_automation)
    monkeypatch.setattr(module, "send_email_daily", fake_send_email)
    monkeypatch.setattr(module, "print_elapsed_time", lambda *a, **k: None)

    module.daily_report(
        run_prices=True,
        run_fundamentals=True,
        run_my_holdings=True,
        run_email=True,
        run_portfolio_automation=True,
    )

    assert calls == [
        "prices",
        "fundamentals",
        "my_holdings",
        "portfolio_automation",
        "send_email",
    ]
    assert Path(email_payload["xlsx_file"]).name == "fundamental_metrics_yfinance.xlsx"
    assert "holdings" in (email_payload["body_data"] or "")
    assert email_payload["attachments"] and len(email_payload["attachments"]) == 1


def test_portfolio_automation_uses_watchlist_alerts(tmp_path, monkeypatch):
    module = importlib.reload(daily_report)
    monkeypatch.setattr(module, "CURRENT_DIR", tmp_path / "reports")
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "portfolio.csv").write_text(
        "ticker,quantity,buy_price,buy_date,currency\nAAPL,1,100,2024-01-01,USD\n",
        encoding="utf-8",
    )
    (config_dir / "watchlist.json").write_text(
        '[{"ticker": "AAPL", "rules": [{"path": "metrics.revenue", "operator": ">=", "value": 1, "message": "Revenue surge"}]}]',
        encoding="utf-8",
    )

    snapshot = PortfolioSnapshot(
        positions=[],
        total_value=0.0,
        total_cost=0.0,
        total_gain=0.0,
        sector_exposure={},
        base_currency="USD",
        as_of=dt.date(2024, 1, 1),
        source_path=config_dir / "portfolio.csv",
    )

    class DummyAnalytics:
        def __init__(self, *args, **kwargs):
            pass

        def load(self, path):
            return snapshot

    alerts = [
        WatchlistAlert(
            ticker="AAPL",
            triggered_rules=["Revenue surge"],
            channels=["email"],
            payload={"values": {"metrics.revenue": 1.2}},
        )
    ]

    class DummyService:
        def __init__(self, *args, **kwargs):
            pass

        def evaluate_watchlist(self, watchlist, include_opinion=False):
            return alerts, {"AAPL": {"metrics": {"revenue": 1.2}}}

    captured = {"alerts": None}

    def fake_report(snapshot, **kwargs):
        captured["alerts"] = kwargs.get("alerts")
        digest = PortfolioDigest(
            snapshot=snapshot,
            metrics={
                "cagr": 0.0,
                "benchmark_cagr": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
                "beta_adjusted_return": 0.0,
                "volatility": 0.0,
                "tracking_error": 0.0,
            },
            alerts=[],
            watchlist_alerts=alerts,
            macro_context={},
            html="<p>digest</p>",
            email_subject="Digest",
            email_body="Body",
            pdf_path=tmp_path / "reports" / "portfolio_report.pdf",
        )
        digest.pdf_path.parent.mkdir(parents=True, exist_ok=True)
        digest.pdf_path.write_text("stub", encoding="utf-8")
        return digest

    monkeypatch.setattr(module, "PortfolioAnalytics", DummyAnalytics)
    monkeypatch.setattr(module, "StockAnalysisService", DummyService)
    monkeypatch.setattr(module, "generate_portfolio_report", fake_report)

    digest = module.portfolio_automation()

    assert digest is not None
    assert captured["alerts"] == alerts
    assert digest.watchlist_alerts == alerts
