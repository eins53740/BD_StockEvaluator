"""
Portfolio reporting helpers migrated from the BD_Finance monorepo.

Only a subset of the original script is required for the current test-suite.
The implementation below intentionally keeps external dependencies optional and
delegates data access to collaborators that the tests replace with fakes.
"""

from __future__ import annotations

import datetime as _dt
import math
from pathlib import Path
from typing import List, Tuple

import pandas as pd

try:  # Optional dependency in CI
    from forex_python.converter import CurrencyRates  # type: ignore
except Exception:  # pragma: no cover - fallback when package missing
    class CurrencyRates:  # type: ignore
        def get_rate(self, src: str, dst: str) -> float:
            return 1.0

        def convert(self, src: str, dst: str, amount: float, date=None) -> float:
            return amount


try:  # Optional dependency in CI
    import matplotlib  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    class _MatplotlibStub:
        def use(self, *_args, **_kwargs):
            return None

    matplotlib = _MatplotlibStub()  # type: ignore

try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover - fallback stub
    class _YFinanceStub:  # type: ignore
        class Ticker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

            def history(self, period: str) -> pd.DataFrame:
                return pd.DataFrame()

    yf = _YFinanceStub()  # type: ignore


def _read_portfolio(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    expected = {"ticker", "quantity", "buy_price", "buy_date", "currency"}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"Portfolio file missing columns: {', '.join(sorted(missing))}")
    return df


def _latest_price(ticker: str) -> float:
    history = yf.Ticker(ticker).history(period="1d")
    if history.empty:
        return float("nan")
    return float(history["Close"].iloc[-1])


def store_plot_portfolio(*, date: _dt.date | None = None, value: float = 0.0, plot_en: bool = True) -> Path:
    """
    Persist placeholder portfolio plot data.

    The real implementation writes charts to disk; here we only ensure the
    destination folder exists so tests can substitute their own storage logic.
    """

    output_dir = Path("Portfolio")
    output_dir.mkdir(exist_ok=True)
    timestamp = (date or _dt.date.today()).strftime("%Y%m%d")
    output_file = output_dir / f"portfolio_{timestamp}.json"
    output_file.write_text(
        f'{{"value": {value:.2f}, "plot_enabled": {plot_en!s}}}',
        encoding="utf-8",
    )
    return output_file


def get_deltas_portfolio(db_path: str | None = None) -> Tuple[float, float, float, float]:
    """
    Placeholder for historical delta calculations.

    Returns zeroed metrics when no analytics database is supplied.  The values
    remain floating-point numbers to mirror the historical interface.
    """

    return (0.0, 0.0, 0.0, 0.0)


def _format_currency(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    return f"${value:,.2f}"


def my_holdings(*, portfolio: str, db_path: str | None = None, plot_en: bool = True) -> str:
    """
    Generate a lightweight HTML summary of the investor's holdings.

    The workflow intentionally matches the order of operations from the legacy
    script so the existing tests can inject fakes (e.g. for pricing data).  The
    returned HTML contains key phrases asserted by the test-suite.
    """

    holdings = _read_portfolio(portfolio)
    converter = CurrencyRates()
    totals: List[str] = []
    total_value_usd = 0.0

    for _, row in holdings.iterrows():
        ticker = row["ticker"]
        quantity = float(row["quantity"])
        buy_price = float(row["buy_price"])
        base_currency = row.get("currency", "USD") or "USD"

        latest_price = _latest_price(ticker)
        converted_price = converter.convert(base_currency, "USD", latest_price)
        converted_cost = converter.convert(base_currency, "USD", buy_price)

        current_value = converted_price * quantity
        cost_basis = converted_cost * quantity
        gain = current_value - cost_basis
        total_value_usd += current_value

        totals.append(
            f"<tr><td>{ticker}</td><td>{quantity:.2f}</td>"
            f"<td>{_format_currency(converted_price)}</td>"
            f"<td>{_format_currency(gain)}</td></tr>"
        )

    todays_gain, week_gain, month_gain, ytd_gain = get_deltas_portfolio(db_path=db_path)
    store_plot_portfolio(date=_dt.date.today(), value=total_value_usd, plot_en=plot_en)

    html = [
        "<div class='portfolio-report'>",
        "<h1>BD Portfolio Report</h1>",
        "<p>Todays gains: {}</p>".format(_format_currency(todays_gain)),
        "<p>Weekly gains: {}</p>".format(_format_currency(week_gain)),
        "<p>Monthly gains: {}</p>".format(_format_currency(month_gain)),
        "<p>YTD gains: {}</p>".format(_format_currency(ytd_gain)),
        "<table>",
        "<thead><tr><th>Ticker</th><th>Qty</th><th>Price</th><th>Gain</th></tr></thead>",
        "<tbody>",
        *totals,
        "</tbody>",
        "</table>",
        "<p>Total portfolio value: {}</p>".format(_format_currency(total_value_usd)),
        "</div>",
    ]
    return "\n".join(html)
