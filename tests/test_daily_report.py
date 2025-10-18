from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from bd_stockevaluator.reports import daily_report


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
        "ticker,quantity,buy_price,buy_date,currency\n"
        "AAPL,1,100,2024-01-01,USD\n",
        encoding="utf-8",
    )

    (tmp_path / "fundamentals").mkdir()

    return module


def test_daily_report_invokes_sections(daily_report_module, monkeypatch):
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

    def fake_send_email(*, xlsx_file=None, body_data=None):
        calls.append("send_email")
        email_payload["xlsx_file"] = xlsx_file
        email_payload["body_data"] = body_data

    monkeypatch.setattr(module, "prices", fake_prices)
    monkeypatch.setattr(module, "fundamentals", fake_fundamentals)
    monkeypatch.setattr(module, "my_holdings", fake_my_holdings)
    monkeypatch.setattr(module, "send_email_daily", fake_send_email)
    monkeypatch.setattr(module, "print_elapsed_time", lambda *a, **k: None)

    module.daily_report(
        run_prices=True,
        run_fundamentals=True,
        run_my_holdings=True,
        run_email=True,
    )

    assert calls == ["prices", "fundamentals", "my_holdings", "send_email"]
    assert Path(email_payload["xlsx_file"]).name == "fundamental_metrics_yfinance.xlsx"
    assert "holdings" in (email_payload["body_data"] or "")
