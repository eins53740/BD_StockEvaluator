from __future__ import annotations

import pandas as pd
import pytest

from bd_stockevaluator.reports import my_holdings as mh


class DummyCurrencyRates:
    def get_rate(self, src: str, dst: str) -> float:
        return 0.9

    def convert(self, src: str, dst: str, amount: float, date=None) -> float:
        return amount * 0.9


class DummyTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, period: str) -> pd.DataFrame:
        if period == "1d":
            return pd.DataFrame(
                {"Close": [110.0], "Open": [109.0]},
                index=pd.to_datetime(["2024-01-02"]),
            )
        if period == "2d":
            return pd.DataFrame(
                {"Close": [108.0, 110.0], "Open": [107.0, 109.0]},
                index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
            )
        return pd.DataFrame()


@pytest.fixture(autouse=True)
def _force_headless_backend():
    # Ensure consistent backend for plots in tests
    mh.matplotlib.use("Agg", force=True)


def test_my_holdings_generates_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    portfolio_csv = tmp_path / "portfolio.csv"
    portfolio_csv.write_text(
        "ticker,quantity,buy_price,buy_date,currency\n"
        "AAPL,5,100,2023-01-01,USD\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(mh, "CurrencyRates", DummyCurrencyRates)
    monkeypatch.setattr(mh.yf, "Ticker", DummyTicker)

    fake_store_called = {"called": False}

    def fake_store_plot_portfolio(*, date=None, value=0, plot_en=True):
        fake_store_called["called"] = True

    monkeypatch.setattr(mh, "store_plot_portfolio", fake_store_plot_portfolio)
    monkeypatch.setattr(mh, "get_deltas_portfolio", lambda db_path=None: (1, 2, 3, 4))

    html = mh.my_holdings(
        portfolio=str(portfolio_csv),
        plot_en=False,
        db_path=str(tmp_path / "Portfolio" / "portfolio.db"),
    )

    assert "BD Portfolio Report" in html
    assert "Todays gains" in html
    assert fake_store_called["called"] is True
