from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from bd_stockevaluator.core.portfolio import (
    PortfolioAnalytics,
    PortfolioPosition,
    PortfolioSnapshot,
)
from bd_stockevaluator.core.portfolio_performance import compute_performance_metrics
from bd_stockevaluator.core.watchlist import WatchlistAlert
from bd_stockevaluator.reports.portfolio_automation import (
    generate_portfolio_report,
    PortfolioDigest,
)


class DummyProvider:
    def __init__(self, snapshots: dict[str, dict[str, object]]) -> None:
        self._snapshots = snapshots
        self.calls: list[str] = []

    def get_snapshot(self, ticker: str) -> dict[str, object]:
        self.calls.append(ticker)
        try:
            return self._snapshots[ticker]
        except KeyError as exc:  # pragma: no cover - guard rail
            raise ValueError(f"Missing snapshot for {ticker}") from exc


class DummyRates:
    def __init__(self, rates: dict[tuple[str, str], float]) -> None:
        self._rates = rates

    def convert(
        self, src: str, dst: str, amount: float, date: dt.date | None = None
    ) -> float:
        if src == dst:
            return amount
        try:
            factor = self._rates[(src, dst)]
        except KeyError as exc:  # pragma: no cover - guard rail
            raise ValueError(f"Missing FX rate {src}->{dst}") from exc
        return amount * factor


def test_prepare_snapshot_from_csv_computes_weights_and_exposure(tmp_path: Path):
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text(
        "ticker,quantity,buy_price,buy_date,currency\n"
        "AAPL,5,100,2023-01-01,USD\n"
        "NESN.SW,10,90,2023-04-01,CHF\n",
        encoding="utf-8",
    )

    provider = DummyProvider(
        {
            "AAPL": {"last_price": 120.0, "currency": "USD", "sector": "Technology"},
            "NESN.SW": {
                "last_price": 110.0,
                "currency": "CHF",
                "sector": "Consumer Defensive",
            },
        }
    )
    rates = DummyRates({("CHF", "USD"): 1.1})

    analytics = PortfolioAnalytics(
        data_provider=provider,
        fx_provider=rates,
        base_currency="USD",
    )
    snapshot = analytics.load(csv_path)

    assert provider.calls == ["AAPL", "NESN.SW"]
    assert pytest.approx(snapshot.total_value, rel=1e-5) == 1810.0
    assert pytest.approx(snapshot.total_cost, rel=1e-5) == 1490.0
    assert pytest.approx(snapshot.total_gain, rel=1e-5) == 320.0

    weights = {position.ticker: position.weight for position in snapshot.positions}
    assert pytest.approx(weights["AAPL"], rel=1e-5) == 600.0 / 1810.0
    assert pytest.approx(weights["NESN.SW"], rel=1e-5) == 1210.0 / 1810.0

    sector_weights = snapshot.sector_exposure
    assert pytest.approx(sum(sector_weights.values()), rel=1e-5) == 1.0
    assert pytest.approx(sector_weights["Technology"], rel=1e-5) == weights["AAPL"]
    assert (
        pytest.approx(sector_weights["Consumer Defensive"], rel=1e-5)
        == weights["NESN.SW"]
    )

    assert snapshot.source_path == csv_path
    assert snapshot.base_currency == "USD"
    assert isinstance(snapshot.as_of, dt.date)


def test_load_supports_excel_sources(tmp_path: Path):
    df = pd.DataFrame(
        [
            {
                "ticker": "MSFT",
                "quantity": 3,
                "buy_price": 200,
                "buy_date": "2022-06-01",
                "currency": "USD",
            }
        ]
    )
    xlsx_path = tmp_path / "portfolio.xlsx"
    df.to_excel(xlsx_path, index=False)

    provider = DummyProvider(
        {"MSFT": {"last_price": 250.0, "currency": "USD", "sector": "Technology"}}
    )
    analytics = PortfolioAnalytics(data_provider=provider)
    snapshot = analytics.load(xlsx_path)

    assert snapshot.source_path == xlsx_path
    assert len(snapshot.positions) == 1
    position = snapshot.positions[0]
    assert position.ticker == "MSFT"
    assert position.currency == "USD"
    assert pytest.approx(position.current_value, rel=1e-5) == 750.0


def test_compute_performance_metrics_portfolio_beats_benchmark():
    dates = pd.to_datetime(
        [
            "2020-01-01",
            "2020-07-01",
            "2021-01-01",
            "2021-07-01",
            "2022-01-01",
            "2022-07-01",
            "2023-01-01",
        ]
    )
    portfolio = pd.Series(
        [100, 110, 120, 125, 140, 150, 165],
        index=dates,
    )
    benchmark = pd.Series(
        [100, 105, 108, 112, 118, 122, 130],
        index=dates,
    )

    metrics = compute_performance_metrics(portfolio, benchmark)

    assert metrics["cagr"] > metrics["benchmark_cagr"]
    assert pytest.approx(metrics["cagr"], rel=1e-4) == 0.181486
    assert pytest.approx(metrics["benchmark_cagr"], rel=1e-4) == 0.091306
    assert pytest.approx(metrics["alpha"], rel=1e-4) == 0.09018
    assert pytest.approx(metrics["beta_adjusted_return"], rel=1e-4) == 0.080153
    assert pytest.approx(metrics["beta"], rel=1e-4) == 1.109818


def test_generate_portfolio_report_writes_pdf_and_email(tmp_path: Path):
    snapshot = PortfolioSnapshot(
        positions=[
            PortfolioPosition(
                ticker="AAPL",
                quantity=5,
                buy_price=100.0,
                buy_date=dt.date(2023, 1, 1),
                currency="USD",
                sector="Technology",
                last_price=120.0,
                last_price_converted=120.0,
                current_value=600.0,
                cost_basis=500.0,
                gain=100.0,
                weight=0.6,
            ),
            PortfolioPosition(
                ticker="JNJ",
                quantity=4,
                buy_price=140.0,
                buy_date=dt.date(2023, 1, 1),
                currency="USD",
                sector="Healthcare",
                last_price=150.0,
                last_price_converted=150.0,
                current_value=600.0,
                cost_basis=560.0,
                gain=40.0,
                weight=0.4,
            ),
        ],
        total_value=1200.0,
        total_cost=1060.0,
        total_gain=140.0,
        sector_exposure={"Technology": 0.6, "Healthcare": 0.4},
        base_currency="USD",
        as_of=dt.date(2024, 1, 1),
        source_path=Path("portfolio.csv"),
    )
    portfolio_series = pd.Series(
        [1060.0, 1200.0],
        index=pd.to_datetime(["2023-01-01", "2024-01-01"]),
    )
    benchmark_series = pd.Series(
        [1060.0, 1120.0],
        index=pd.to_datetime(["2023-01-01", "2024-01-01"]),
    )

    digest = generate_portfolio_report(
        snapshot,
        portfolio_series=portfolio_series,
        benchmark_series=benchmark_series,
        alerts=["AAPL nearing target price"],
        macro_context={"headline": "Neutral outlook", "indicators": {"cpi": "cooling"}},
        output_dir=tmp_path,
    )

    assert isinstance(digest, PortfolioDigest)
    assert digest.pdf_path.suffix == ".pdf"
    assert digest.pdf_path.exists()
    content = digest.pdf_path.read_text(encoding="utf-8")
    assert "BD Portfolio Automation" in content

    assert "Technology" in digest.html
    assert "AAPL" in digest.email_body
    assert "Neutral outlook" in digest.html
    assert digest.metrics["alpha"] > 0
    assert digest.watchlist_alerts == []


def test_generate_portfolio_report_formats_watchlist_alerts(tmp_path: Path):
    snapshot = PortfolioSnapshot(
        positions=[
            PortfolioPosition(
                ticker="AAPL",
                quantity=5,
                buy_price=100.0,
                buy_date=dt.date(2023, 1, 1),
                currency="USD",
                sector="Technology",
                last_price=120.0,
                last_price_converted=120.0,
                current_value=600.0,
                cost_basis=500.0,
                gain=100.0,
                weight=0.6,
            )
        ],
        total_value=600.0,
        total_cost=500.0,
        total_gain=100.0,
        sector_exposure={"Technology": 1.0},
        base_currency="USD",
        as_of=dt.date(2024, 6, 1),
        source_path=Path("portfolio.csv"),
    )
    alert = WatchlistAlert(
        ticker="AAPL",
        triggered_rules=[
            "Valuation score above target",
            "Technical signal in buy zone",
        ],
        channels=["email"],
        payload={"values": {"valuation": 85}},
    )

    digest = generate_portfolio_report(
        snapshot,
        portfolio_series=pd.Series(
            [500.0, 600.0], index=pd.to_datetime(["2023-06-01", "2024-06-01"])
        ),
        alerts=[alert],
        macro_context={},
        output_dir=tmp_path,
    )

    assert digest.watchlist_alerts == [alert]
    assert "AAPL" in digest.html
    assert "Valuation score above target" in digest.html
    assert "Technical signal in buy zone" in digest.email_body
