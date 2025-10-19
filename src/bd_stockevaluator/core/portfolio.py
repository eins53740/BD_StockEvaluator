"""
Portfolio analytics helpers supporting Epic 6 automation features.

The module focuses on ingesting investor holdings, enriching them with market
data, and exposing sector/weight breakdowns ready for downstream reporting. The
implementation stays dependency-light and embraces loose coupling so tests can
inject fakes for external services (quotes, FX, etc.).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Protocol

import pandas as pd

try:  # Optional dependency for FX conversion
    from forex_python.converter import CurrencyRates  # type: ignore
except Exception:  # pragma: no cover - fallback when package unavailable

    class CurrencyRates:  # type: ignore
        def convert(
            self, src: str, dst: str, amount: float, date: dt.date | None = None
        ) -> float:
            if src == dst:
                return float(amount)
            raise ValueError("Currency conversion unavailable without forex-python")


try:  # Optional dependency for live quotes
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without yfinance

    class _YFinanceStub:  # type: ignore
        class Ticker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol

            def fast_info(self) -> MutableMapping[str, Any]:  # pragma: no cover
                return {}

            def info(self) -> MutableMapping[str, Any]:  # pragma: no cover
                return {}

    yf = _YFinanceStub()  # type: ignore


class PortfolioDataProvider(Protocol):
    """Contract for retrieving per-ticker snapshot data."""

    def get_snapshot(self, ticker: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class PortfolioPosition:
    """Normalized view of a single holding."""

    ticker: str
    quantity: float
    buy_price: float
    buy_date: dt.date | None
    currency: str
    sector: str
    last_price: float
    last_price_converted: float
    current_value: float
    cost_basis: float
    gain: float
    weight: float


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Aggregated portfolio analytics ready for reporting."""

    positions: List[PortfolioPosition]
    total_value: float
    total_cost: float
    total_gain: float
    sector_exposure: Dict[str, float]
    base_currency: str
    as_of: dt.date
    source_path: Path | None = None


class YFinancePortfolioProvider:
    """Very small adapter around yfinance used as default data provider."""

    def get_snapshot(self, ticker: str) -> Mapping[str, Any]:
        ticker_obj = yf.Ticker(ticker)
        info = {}

        try:
            fast_info = getattr(ticker_obj, "fast_info", None)
            if fast_info:
                info.update(fast_info)
        except Exception:
            info.update({})

        try:
            raw_info = getattr(ticker_obj, "info", None)
            if callable(raw_info):
                info.update(raw_info())
            elif isinstance(raw_info, Mapping):
                info.update(raw_info)
        except Exception:
            info.update({})

        price = info.get("last_price") or info.get("regularMarketPrice")
        currency = info.get("currency") or info.get("financialCurrency") or "USD"
        sector = info.get("sector") or ""
        fetched = info.get("regularMarketTime")

        return {
            "last_price": price,
            "currency": currency,
            "sector": sector,
            "as_of": fetched,
        }


class PortfolioAnalytics:
    """High-level API orchestrating holdings ingestion and enrichment."""

    REQUIRED_COLUMNS = {"ticker", "quantity", "buy_price", "buy_date"}

    def __init__(
        self,
        *,
        data_provider: PortfolioDataProvider | None = None,
        fx_provider: CurrencyRates | None = None,
        base_currency: str = "USD",
    ) -> None:
        self.data_provider = data_provider or YFinancePortfolioProvider()
        self.fx_provider = fx_provider or CurrencyRates()
        self.base_currency = base_currency.upper()

    def load(self, source: str | Path | pd.DataFrame) -> PortfolioSnapshot:
        """Load holdings from *source* and return an enriched snapshot."""

        dataframe, source_path = self._ensure_dataframe(source)
        positions = self._build_positions(dataframe)
        total_value = sum(position.current_value for position in positions)
        total_cost = sum(position.cost_basis for position in positions)
        total_gain = total_value - total_cost
        sector_totals: Dict[str, float] = {}
        for position in positions:
            sector_totals[position.sector] = (
                sector_totals.get(position.sector, 0.0) + position.weight
            )

        as_of = self._infer_as_of(positions)
        return PortfolioSnapshot(
            positions=positions,
            total_value=total_value,
            total_cost=total_cost,
            total_gain=total_gain,
            sector_exposure=sector_totals,
            base_currency=self.base_currency,
            as_of=as_of,
            source_path=source_path,
        )

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _ensure_dataframe(
        self, source: str | Path | pd.DataFrame
    ) -> tuple[pd.DataFrame, Path | None]:
        if isinstance(source, pd.DataFrame):
            df = source.copy()
            src_path = None
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Portfolio file not found: {path}")

            suffix = path.suffix.lower()
            if suffix in {".csv", ".txt"}:
                df = pd.read_csv(path)
            elif suffix in {".xlsx", ".xls", ".xlsm"}:
                df = pd.read_excel(path)
            else:
                raise ValueError(f"Unsupported portfolio format: {path.suffix}")
            src_path = path

        missing = self.REQUIRED_COLUMNS.difference(df.columns)
        if missing:
            raise ValueError(
                f"Portfolio data missing columns: {', '.join(sorted(missing))}"
            )

        return df, src_path

    def _build_positions(self, dataframe: pd.DataFrame) -> List[PortfolioPosition]:
        total_value = 0.0
        rows: List[MutableMapping[str, Any]] = []

        for _, row in dataframe.iterrows():
            ticker = str(row["ticker"]).strip()
            quantity = float(row["quantity"])
            buy_price = float(row["buy_price"])
            buy_currency = str(row.get("currency") or self.base_currency).upper()
            buy_date = self._coerce_date(row.get("buy_date"))

            snapshot = self.data_provider.get_snapshot(ticker)
            market_price = float(snapshot.get("last_price") or 0.0)
            market_currency = str(
                snapshot.get("currency") or buy_currency or self.base_currency
            ).upper()
            sector = str(snapshot.get("sector") or "Unknown").strip() or "Unknown"

            converted_price = self._convert(market_price, market_currency)
            converted_cost = self._convert(buy_price, buy_currency)
            current_value = converted_price * quantity
            cost_basis = converted_cost * quantity
            gain = current_value - cost_basis

            row_dict: MutableMapping[str, Any] = {
                "ticker": ticker,
                "quantity": quantity,
                "buy_price": buy_price,
                "buy_date": buy_date,
                "currency": market_currency,
                "sector": sector,
                "last_price": market_price,
                "last_price_converted": converted_price,
                "current_value": current_value,
                "cost_basis": cost_basis,
                "gain": gain,
            }
            rows.append(row_dict)
            total_value += current_value

        positions: List[PortfolioPosition] = []
        for row in rows:
            weight = (row["current_value"] / total_value) if total_value else 0.0
            position = PortfolioPosition(
                ticker=row["ticker"],
                quantity=row["quantity"],
                buy_price=row["buy_price"],
                buy_date=row["buy_date"],
                currency=row["currency"],
                sector=row["sector"],
                last_price=row["last_price"],
                last_price_converted=row["last_price_converted"],
                current_value=row["current_value"],
                cost_basis=row["cost_basis"],
                gain=row["gain"],
                weight=weight,
            )
            positions.append(position)

        return positions

    def _convert(self, amount: float, source_currency: str) -> float:
        amount = float(amount)
        source = (source_currency or self.base_currency).upper()
        if source == self.base_currency:
            return amount
        try:
            return float(self.fx_provider.convert(source, self.base_currency, amount))
        except Exception as exc:
            raise ValueError(
                f"Failed to convert {amount} from {source} to {self.base_currency}"
            ) from exc

    @staticmethod
    def _coerce_date(value: Any) -> dt.date | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        try:
            parsed = pd.to_datetime(value, errors="coerce")
        except Exception:
            return None
        if pd.isna(parsed):
            return None
        if isinstance(parsed, pd.Timestamp):
            parsed = parsed.to_pydatetime()
        if isinstance(parsed, dt.datetime):
            return parsed.date()
        if isinstance(parsed, dt.date):
            return parsed
        return None

    def _infer_as_of(self, positions: Iterable[PortfolioPosition]) -> dt.date:
        candidates: List[dt.date] = []
        for position in positions:
            if isinstance(position.buy_date, dt.date):
                candidates.append(position.buy_date)
        return max(candidates, default=dt.date.today())


__all__ = [
    "PortfolioAnalytics",
    "PortfolioDataProvider",
    "PortfolioPosition",
    "PortfolioSnapshot",
    "YFinancePortfolioProvider",
]
