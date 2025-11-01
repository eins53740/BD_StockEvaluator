from __future__ import annotations

import csv
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
)

try:
    # Python 3.9+ zoneinfo
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback
    ZoneInfo = None

import requests
import uuid
import yfinance as yf

from .keys import get_api_key

DEFAULT_PRECEDENCE: Dict[str, Sequence[str]] = {
    "prices": ("fmp", "yahoo", "alpha"),
    "fundamentals": ("fmp", "finnhub", "alpha", "yahoo", "csv"),
    "dividends": ("yahoo", "fmp"),
    "profile": ("fmp", "yahoo", "csv"),
    "exchange_rates": ("fmp", "alpha"),
    "history": ("fmp", "finnhub", "alpha"),
    "price_history": ("fmp", "yahoo"),
    "ownership": ("fmp", "yahoo"),
}


class ProviderError(Exception):
    """Raised when a provider cannot satisfy a data request."""


class CurrencyConverter:
    """Simple converter that works with rates expressed relative to USD."""

    def __init__(
        self, rates_to_usd: Optional[MutableMapping[str, float]] = None
    ) -> None:
        base = rates_to_usd or {"USD": 1.0}
        self._rates = {
            code.upper(): float(rate)
            for code, rate in base.items()
            if rate is not None and float(rate) > 0
        }
        self._rates.setdefault("USD", 1.0)

    def extend(
        self, overrides: Optional[MutableMapping[str, float]] = None
    ) -> "CurrencyConverter":
        if not overrides:
            return CurrencyConverter(self._rates)
        merged = self._rates.copy()
        for code, rate in overrides.items():
            try:
                rate_val = float(rate)
            except (TypeError, ValueError):
                continue
            if rate_val <= 0:
                continue
            merged[code.upper()] = rate_val
        return CurrencyConverter(merged)

    def convert(
        self, amount: Optional[float], source: Optional[str], target: str
    ) -> Optional[float]:
        if amount is None:
            return None
        source_code = (source or "USD").upper()
        target_code = target.upper()
        if source_code not in self._rates or target_code not in self._rates:
            return None
        usd_value = amount * self._rates[source_code]
        target_rate = self._rates[target_code]
        if target_rate == 0:
            return None
        return usd_value / target_rate

    @property
    def rates(self) -> Dict[str, float]:
        return dict(self._rates)


def _ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _json_serializer(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Type {type(value)} is not JSON serialisable")


def _to_iso(dt: datetime) -> str:
    return _ensure_tz(dt).isoformat().replace("+00:00", "Z")


def _from_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    return _ensure_tz(dt)


def _restore_macro_snapshot_dates(snapshot: MutableMapping[str, Any]) -> None:
    dashboard = snapshot.get("dashboard")
    if isinstance(dashboard, MutableMapping):
        for entry in dashboard.values():
            if not isinstance(entry, MutableMapping):
                continue
            for key in ("latest", "previous"):
                section = entry.get(key)
                if isinstance(section, MutableMapping):
                    date_val = section.get("date")
                    if isinstance(date_val, str):
                        try:
                            section["date"] = _from_iso(date_val)
                        except (TypeError, ValueError):
                            continue


@dataclass
class NormalizedSnapshot:
    ticker: str
    as_of: datetime
    currency: str
    exchange: Optional[str]
    country: Optional[str]
    fundamentals: Dict[str, Any]
    fundamentals_converted: Dict[str, Any]
    prices: Dict[str, Any]
    prices_converted: Dict[str, Any]
    dividends: Dict[str, Any]
    profile: Dict[str, Any]
    providers: Dict[str, Optional[str]]
    history: List[Dict[str, Any]]
    price_history: List[Dict[str, Any]]
    fx_rates: Dict[str, float]


class SQLiteDataStore:
    """SQLite-backed cache used by the multi-source pipeline."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            self.path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._priority_lookup: Dict[tuple[str, str], int] = {}
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cursor = self._conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fundamentals_snapshot (
                ticker TEXT PRIMARY KEY,
                as_of TEXT NOT NULL,
                provider TEXT,
                currency TEXT,
                exchange TEXT,
                country TEXT,
                eps REAL,
                pe REAL,
                peg REAL,
                ev_to_ebit REAL,
                pb REAL,
                fcf_yield REAL,
                revenue_growth REAL,
                profit_margins REAL,
                roe REAL,
                debt_to_equity REAL,
                quick_ratio REAL,
                eps_usd REAL,
                eps_eur REAL,
                raw_json TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fundamentals_history (
                ticker TEXT NOT NULL,
                period TEXT NOT NULL,
                provider TEXT,
                as_of TEXT NOT NULL,
                currency TEXT,
                eps REAL,
                pe REAL,
                peg REAL,
                ev_to_ebit REAL,
                pb REAL,
                fcf_yield REAL,
                eps_usd REAL,
                eps_eur REAL,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (ticker, period)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prices_daily (
                ticker TEXT NOT NULL,
                price_date TEXT NOT NULL,
                provider TEXT,
                currency TEXT,
                close REAL,
                close_usd REAL,
                close_eur REAL,
                previous_close REAL,
                open_price REAL,
                raw_json TEXT NOT NULL,
                PRIMARY KEY (ticker, price_date, provider)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS providers_meta (
                provider TEXT NOT NULL,
                category TEXT NOT NULL,
                priority INTEGER,
                last_success TEXT,
                last_failure TEXT,
                message TEXT,
                PRIMARY KEY (provider, category)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ownership_history (
                ticker TEXT NOT NULL,
                as_of TEXT NOT NULL,
                source TEXT,
                institutional REAL,
                insider REAL,
                PRIMARY KEY (ticker, as_of, source)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_series (
                series_id TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                value REAL NOT NULL,
                frequency TEXT,
                provider TEXT,
                ingested_at TEXT NOT NULL,
                PRIMARY KEY (series_id, observation_date)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_snapshot (
                as_of TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fx_snapshot (
                id TEXT PRIMARY KEY,
                as_of TEXT NOT NULL,
                provider TEXT,
                rates_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        self._conn.commit()

    def set_precedence(self, precedence: Dict[str, Sequence[str]]) -> None:
        lookup: Dict[tuple[str, str], int] = {}
        for category, providers in precedence.items():
            for index, provider in enumerate(providers):
                lookup[(provider, category)] = index
        self._priority_lookup = lookup

    def persist_snapshot(self, snapshot: NormalizedSnapshot) -> None:
        payload = {
            "fundamentals": snapshot.fundamentals,
            "fundamentals_converted": snapshot.fundamentals_converted,
            "prices": snapshot.prices,
            "prices_converted": snapshot.prices_converted,
            "dividends": snapshot.dividends,
            "profile": snapshot.profile,
            "providers": snapshot.providers,
            "as_of": snapshot.as_of.isoformat(),
            "price_history": snapshot.price_history,
        }
        as_of_iso = snapshot.as_of.isoformat()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO fundamentals_snapshot (
                    ticker,
                    as_of,
                    provider,
                    currency,
                    exchange,
                    country,
                    eps,
                    pe,
                    peg,
                    ev_to_ebit,
                    pb,
                    fcf_yield,
                    revenue_growth,
                    profit_margins,
                    roe,
                    debt_to_equity,
                    quick_ratio,
                    eps_usd,
                    eps_eur,
                    raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    as_of=excluded.as_of,
                    provider=excluded.provider,
                    currency=excluded.currency,
                    exchange=excluded.exchange,
                    country=excluded.country,
                    eps=excluded.eps,
                    pe=excluded.pe,
                    peg=excluded.peg,
                    ev_to_ebit=excluded.ev_to_ebit,
                    pb=excluded.pb,
                    fcf_yield=excluded.fcf_yield,
                    revenue_growth=excluded.revenue_growth,
                    profit_margins=excluded.profit_margins,
                    roe=excluded.roe,
                    debt_to_equity=excluded.debt_to_equity,
                    quick_ratio=excluded.quick_ratio,
                    eps_usd=excluded.eps_usd,
                    eps_eur=excluded.eps_eur,
                    raw_json=excluded.raw_json
                """,
                (
                    snapshot.ticker,
                    as_of_iso,
                    snapshot.providers.get("fundamentals"),
                    snapshot.currency,
                    snapshot.exchange,
                    snapshot.country,
                    snapshot.fundamentals.get("eps"),
                    snapshot.fundamentals.get("pe"),
                    snapshot.fundamentals.get("peg"),
                    snapshot.fundamentals.get("ev_to_ebit"),
                    snapshot.fundamentals.get("pb"),
                    snapshot.fundamentals.get("fcf_yield"),
                    snapshot.fundamentals.get("revenue_growth"),
                    snapshot.fundamentals.get("profit_margins"),
                    snapshot.fundamentals.get("roe"),
                    snapshot.fundamentals.get("debt_to_equity"),
                    snapshot.fundamentals.get("quick_ratio"),
                    snapshot.fundamentals_converted.get("eps_usd"),
                    snapshot.fundamentals_converted.get("eps_eur"),
                    json.dumps(payload, default=_json_serializer),
                ),
            )

    def save_fx_snapshot(
        self, as_of: datetime, provider: Optional[str], rates: Dict[str, float]
    ) -> str:
        """Persist FX rates as a snapshot and return the generated id."""
        fx_id = str(uuid.uuid4())
        as_of_iso = _to_iso(as_of)
        created = _to_iso(datetime.now(timezone.utc))
        rates_json = json.dumps(rates)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO fx_snapshot (id, as_of, provider, rates_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (fx_id, as_of_iso, provider, rates_json, created),
            )
        return fx_id

    def load_fx_snapshot(self, fx_id: Optional[str] = None) -> Dict[str, Any]:
        """Load an fx_snapshot by id or return empty dict if not found."""
        if not fx_id:
            return {}
        row = self._conn.execute(
            """
            SELECT id, as_of, provider, rates_json, created_at
            FROM fx_snapshot
            WHERE id = ?
            """,
            (fx_id,),
        ).fetchone()
        if not row:
            return {}
        return {
            "id": row["id"],
            "as_of": row["as_of"],
            "provider": row["provider"],
            "rates": json.loads(row["rates_json"]),
            "created_at": row["created_at"],
        }

    def persist_history(
        self,
        ticker: str,
        history_entries: Iterable[Dict[str, Any]],
        provider: Optional[str],
        as_of: datetime,
        converter: CurrencyConverter,
    ) -> None:
        if not history_entries:
            return

        as_of_iso = as_of.isoformat()

        with self._conn:
            for entry in history_entries:
                period = entry.get("period") or entry.get("date")
                if not period:
                    continue
                currency = (
                    entry.get("currency") or entry.get("financialCurrency") or "USD"
                ).upper()
                eps = entry.get("eps")
                eps_usd = (
                    converter.convert(eps, currency, "USD") if eps is not None else None
                )
                eps_eur = (
                    converter.convert(eps, currency, "EUR") if eps is not None else None
                )
                self._conn.execute(
                    """
                    INSERT INTO fundamentals_history (
                        ticker,
                        period,
                        provider,
                        as_of,
                        currency,
                        eps,
                        pe,
                        peg,
                        ev_to_ebit,
                        pb,
                        fcf_yield,
                        eps_usd,
                        eps_eur,
                        raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, period) DO UPDATE SET
                        provider=excluded.provider,
                        as_of=excluded.as_of,
                        currency=excluded.currency,
                        eps=excluded.eps,
                        pe=excluded.pe,
                        peg=excluded.peg,
                        ev_to_ebit=excluded.ev_to_ebit,
                        pb=excluded.pb,
                        fcf_yield=excluded.fcf_yield,
                        eps_usd=excluded.eps_usd,
                        eps_eur=excluded.eps_eur,
                        raw_json=excluded.raw_json
                    """,
                    (
                        ticker,
                        period,
                        provider,
                        as_of_iso,
                        currency,
                        eps,
                        entry.get("pe"),
                        entry.get("peg"),
                        entry.get("ev_to_ebit"),
                        entry.get("pb"),
                        entry.get("fcf_yield"),
                        eps_usd,
                        eps_eur,
                        json.dumps(entry, default=_json_serializer),
                    ),
                )

    def persist_price(
        self,
        ticker: str,
        price_payload: Dict[str, Any],
        provider: Optional[str],
        as_of: datetime,
        converter: CurrencyConverter,
    ) -> None:
        currency = (price_payload.get("currency") or "USD").upper()
        close = price_payload.get("close")
        prev_close = price_payload.get("previous_close")
        open_price = price_payload.get("open")

        close_usd = (
            converter.convert(close, currency, "USD") if close is not None else None
        )
        close_eur = (
            converter.convert(close, currency, "EUR") if close is not None else None
        )

        price_date = _ensure_tz(as_of).date().isoformat()

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO prices_daily (
                    ticker,
                    price_date,
                    provider,
                    currency,
                    close,
                    close_usd,
                    close_eur,
                    previous_close,
                    open_price,
                    raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, price_date, provider) DO UPDATE SET
                    currency=excluded.currency,
                    close=excluded.close,
                    close_usd=excluded.close_usd,
                    close_eur=excluded.close_eur,
                    previous_close=excluded.previous_close,
                    open_price=excluded.open_price,
                    raw_json=excluded.raw_json
                """,
                (
                    ticker,
                    price_date,
                    provider,
                    currency,
                    close,
                    close_usd,
                    close_eur,
                    prev_close,
                    open_price,
                    json.dumps(price_payload, default=_json_serializer),
                ),
            )

    def update_provider_meta(
        self,
        provider: Optional[str],
        category: str,
        success: bool,
        as_of: datetime,
        message: Optional[str] = None,
    ) -> None:
        if not provider:
            return

        timestamp = as_of.isoformat()
        priority = self._priority_lookup.get((provider, category))
        text_message = (message or "").strip()

        with self._conn:
            if success:
                self._conn.execute(
                    """
                    INSERT INTO providers_meta (provider, category, priority, last_success, message)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(provider, category) DO UPDATE SET
                        priority=excluded.priority,
                        last_success=excluded.last_success,
                        message=CASE
                            WHEN excluded.message <> '' THEN excluded.message
                            ELSE providers_meta.message
                        END
                    """,
                    (provider, category, priority, timestamp, text_message),
                )
            else:
                self._conn.execute(
                    """
                    INSERT INTO providers_meta (provider, category, priority, last_failure, message)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(provider, category) DO UPDATE SET
                        priority=excluded.priority,
                        last_failure=excluded.last_failure,
                        message=CASE
                            WHEN excluded.message <> '' THEN excluded.message
                            ELSE providers_meta.message
                        END
                    """,
                    (provider, category, priority, timestamp, text_message),
                )

    def load_latest_snapshot(self, ticker: str) -> Dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT
                ticker,
                as_of,
                provider,
                currency,
                exchange,
                country,
                eps,
                pe,
                peg,
                ev_to_ebit,
                pb,
                fcf_yield,
                revenue_growth,
                profit_margins,
                roe,
                debt_to_equity,
                quick_ratio,
                eps_usd,
                eps_eur
            FROM fundamentals_snapshot
            WHERE ticker = ?
            """,
            (ticker,),
        ).fetchone()
        return dict(row) if row else {}

    def load_history(self, ticker: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT ticker, period, provider, as_of, currency, eps, pe, peg, ev_to_ebit, pb, fcf_yield, eps_usd, eps_eur
            FROM fundamentals_history
            WHERE ticker = ?
            ORDER BY as_of DESC
            """,
            (ticker,),
        ).fetchall()
        return [dict(row) for row in rows]

    def load_latest_price(self, ticker: str) -> Dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT ticker, price_date, provider, currency, close, close_usd, close_eur, previous_close, open_price
            FROM prices_daily
            WHERE ticker = ?
            ORDER BY price_date DESC
            LIMIT 1
            """,
            (ticker,),
        ).fetchone()
        return dict(row) if row else {}

    def load_provider_meta(self, provider: str, category: str) -> Dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT provider, category, priority, last_success, last_failure, message
            FROM providers_meta
            WHERE provider = ? AND category = ?
            """,
            (provider, category),
        ).fetchone()
        if row:
            return dict(row)
        return {
            "provider": provider,
            "category": category,
            "priority": self._priority_lookup.get((provider, category)),
            "last_success": None,
            "last_failure": None,
            "message": None,
        }

    def save_ownership_history(
        self,
        ticker: str,
        history_entries: Sequence[Mapping[str, Any]],
        provider: Optional[str],
        as_of: datetime,
    ) -> None:
        if not history_entries:
            return
        source = provider or "unknown"
        with self._conn:
            for entry in history_entries:
                date_value = entry.get("date") or entry.get("as_of")
                if not date_value:
                    continue
                if isinstance(date_value, datetime):
                    as_iso = _to_iso(date_value)
                else:
                    try:
                        as_iso = _to_iso(_from_iso(str(date_value)))
                    except Exception:
                        as_iso = str(date_value)
                institutional = entry.get("institutional")
                insider = entry.get("insider")
                try:
                    inst_val = (
                        float(institutional) if institutional is not None else None
                    )
                except (TypeError, ValueError):
                    inst_val = None
                try:
                    insider_val = float(insider) if insider is not None else None
                except (TypeError, ValueError):
                    insider_val = None
                if inst_val is None and insider_val is None:
                    continue
                self._conn.execute(
                    """
                    INSERT INTO ownership_history (
                        ticker,
                        as_of,
                        source,
                        institutional,
                        insider
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, as_of, source) DO UPDATE SET
                        institutional=excluded.institutional,
                        insider=excluded.insider
                    """,
                    (ticker, as_iso, source, inst_val, insider_val),
                )

    def load_ownership_history(self, ticker: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT as_of, source, institutional, insider
            FROM ownership_history
            WHERE ticker = ?
            ORDER BY as_of ASC
            """,
            (ticker,),
        ).fetchall()
        history: List[Dict[str, Any]] = []
        for row in rows:
            raw_date = row["as_of"]
            try:
                date_val = _from_iso(raw_date)
            except Exception:
                try:
                    date_val = datetime.fromisoformat(raw_date)
                except Exception:
                    continue
            history.append(
                {
                    "date": date_val,
                    "source": row["source"],
                    "institutional": row["institutional"],
                    "insider": row["insider"],
                }
            )
        return history

    def save_macro_series(
        self,
        series_id: str,
        points: Sequence[Dict[str, Any]],
        *,
        frequency: Optional[str],
        provider: Optional[str],
        ingested_at: Optional[datetime] = None,
    ) -> None:
        if not points:
            return
        timestamp = _to_iso(ingested_at or datetime.now(timezone.utc))
        with self._conn:
            for entry in points:
                observation_date = entry.get("date")
                value = entry.get("value")
                if observation_date is None or value is None:
                    continue
                if isinstance(observation_date, datetime):
                    date_iso = _to_iso(observation_date)
                else:
                    date_iso = str(observation_date)
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue
                self._conn.execute(
                    """
                    INSERT INTO macro_series (
                        series_id,
                        observation_date,
                        value,
                        frequency,
                        provider,
                        ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(series_id, observation_date) DO UPDATE SET
                        value=excluded.value,
                        frequency=excluded.frequency,
                        provider=excluded.provider,
                        ingested_at=excluded.ingested_at
                    """,
                    (
                        series_id,
                        date_iso,
                        numeric_value,
                        frequency,
                        provider,
                        timestamp,
                    ),
                )

    def load_macro_series(self, series_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT observation_date, value, frequency, provider
            FROM macro_series
            WHERE series_id = ?
            ORDER BY observation_date ASC
            """,
            (series_id,),
        ).fetchall()
        results: List[Dict[str, Any]] = []
        for row in rows:
            date_raw = row["observation_date"]
            try:
                date_dt = _from_iso(date_raw)
            except Exception:
                date_dt = datetime.fromisoformat(date_raw)
            results.append(
                {
                    "date": date_dt,
                    "value": float(row["value"]) if row["value"] is not None else None,
                    "frequency": row["frequency"],
                    "provider": row["provider"],
                }
            )
        return results

    def save_macro_snapshot(self, as_of: datetime, payload: Dict[str, Any]) -> None:
        as_of_iso = _to_iso(as_of)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO macro_snapshot (as_of, payload)
                VALUES (?, ?)
                ON CONFLICT(as_of) DO UPDATE SET payload=excluded.payload
                """,
                (as_of_iso, json.dumps(payload, default=_json_serializer)),
            )

    def load_macro_snapshot(self) -> Dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT as_of, payload
            FROM macro_snapshot
            ORDER BY as_of DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return {}
        payload = json.loads(row["payload"])
        as_of_raw = row["as_of"]
        payload["as_of"] = as_of_raw
        if isinstance(as_of_raw, str):
            try:
                payload["as_of_dt"] = _from_iso(as_of_raw)
            except (TypeError, ValueError):
                pass
        _restore_macro_snapshot_dates(payload)
        return payload


class BaseProvider:
    """Base class for provider implementations."""

    name: str = "base"
    categories: Sequence[str] = ()

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        raise NotImplementedError


class YahooFinanceProvider(BaseProvider):
    name = "yahoo"
    categories = ("prices", "profile", "dividends", "fundamentals")
    _throttle_until: Optional[datetime] = None

    @classmethod
    def _is_throttled(cls) -> bool:
        if cls._throttle_until is None:
            return False
        return datetime.now(timezone.utc) < cls._throttle_until

    @classmethod
    def _set_throttle(cls, minutes: int = 15) -> None:
        cls._throttle_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        message = str(exc).lower()
        if "429" in message or "too many requests" in message:
            return True
        response = getattr(exc, "response", None)
        if response is not None and getattr(response, "status_code", None) == 429:
            return True
        return False

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        if self._is_throttled():
            until = type(self)._throttle_until
            until_str = until.isoformat() if until else "later"
            raise ProviderError(
                f"Yahoo Finance temporarily throttled until {until_str}"
            )

        stock = yf.Ticker(ticker)
        payload: Dict[str, Dict[str, Any]] = {}

        info: Dict[str, Any] = {}
        try:
            if hasattr(stock, "get_info"):
                result = stock.get_info()
                if isinstance(result, dict):
                    info = result
        except Exception as exc:
            if self._is_rate_limit_error(exc):
                self._set_throttle()
                raise ProviderError("Yahoo Finance rate limited (429)") from exc
            info = {}

        fast_info = getattr(stock, "fast_info", None)
        price_data: Dict[str, Any] = {}
        if fast_info:
            price_data["currency"] = (
                getattr(fast_info, "currency", None) or info.get("currency") or "USD"
            )
            price_data["close"] = getattr(fast_info, "last_price", None) or getattr(
                fast_info, "lastPrice", None
            )
            price_data["previous_close"] = getattr(
                fast_info, "previous_close", None
            ) or info.get("previousClose")
            price_data["open"] = getattr(fast_info, "open", None)

        if not price_data.get("close"):
            try:
                hist = stock.history(period="5d")
                if not hist.empty:
                    price_data["close"] = float(hist["Close"].iloc[-1])
                    price_data.setdefault("currency", info.get("currency", "USD"))
                    if len(hist) > 1:
                        price_data["previous_close"] = float(hist["Close"].iloc[-2])
            except Exception as exc:
                if self._is_rate_limit_error(exc):
                    self._set_throttle()
                    raise ProviderError("Yahoo Finance rate limited (429)") from exc
                pass

        if price_data:
            payload["prices"] = price_data

        dividends = {}
        if info:
            dividends = {
                "forward_yield": info.get("dividendYield"),
                "payout_ratio": info.get("payoutRatio"),
            }
            payload["profile"] = {
                key: info.get(key)
                for key in (
                    "longName",
                    "shortName",
                    "sector",
                    "industry",
                    "exchange",
                    "marketCap",
                    "country",
                )
                if info.get(key) is not None
            }

            fundamentals_map = {
                "financialCurrency": "currency",
                "trailingPE": "pe",
                "pegRatio": "peg",
                "priceToBook": "pb",
                "revenueGrowth": "revenue_growth",
                "profitMargins": "profit_margins",
                "returnOnEquity": "roe",
                "debtToEquity": "debt_to_equity",
                "quickRatio": "quick_ratio",
            }

            fundamentals = {}
            for info_key, new_key in fundamentals_map.items():
                value = info.get(info_key)
                if value is not None:
                    fundamentals[new_key] = value

            if fundamentals:
                fundamentals.setdefault(
                    "currency", info.get("financialCurrency") or info.get("currency")
                )
                payload["fundamentals"] = fundamentals

        if dividends:
            payload["dividends"] = dividends

        return payload


class FMPProvider(BaseProvider):
    name = "fmp"
    categories = (
        "fundamentals",
        "profile",
        "exchange_rates",
        "history",
        "price_history",
    )

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        self.base_url = os.getenv(
            "FMP_BASE_URL", "https://financialmodelingprep.com/api/v3"
        )

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        if not self.api_key:
            raise ProviderError("Missing FMP API key")

        params = {"apikey": self.api_key}
        payload: Dict[str, Dict[str, Any]] = {}

        try:
            profile_resp = requests.get(
                f"{self.base_url}/profile/{ticker}", params=params, timeout=10
            )
            profile_resp.raise_for_status()
            profile_data = profile_resp.json()
            if isinstance(profile_data, list) and profile_data:
                data = profile_data[0]
                payload["profile"] = {
                    "name": data.get("companyName"),
                    "sector": data.get("sector"),
                    "industry": data.get("industry"),
                    "exchange": data.get("exchange"),
                    "currency": data.get("currency"),
                    "marketCap": data.get("mktCap"),
                }
        except Exception as exc:
            raise ProviderError(f"FMP profile fetch failed: {exc}") from exc

        try:
            metrics_resp = requests.get(
                f"{self.base_url}/key-metrics/{ticker}",
                params={**params, "limit": 1},
                timeout=10,
            )
            metrics_resp.raise_for_status()
            metrics_data = metrics_resp.json()
            if isinstance(metrics_data, list) and metrics_data:
                metrics = metrics_data[0]
                fundamentals = {
                    "currency": metrics.get("financialCurrency")
                    or payload.get("profile", {}).get("currency"),
                    "eps": metrics.get("eps"),
                    "pe": metrics.get("peRatio"),
                    "peg": metrics.get("pegRatio"),
                    "ev_to_ebit": metrics.get("evToEbit"),
                    "pb": metrics.get("pbRatio"),
                    "fcf_yield": metrics.get("freeCashFlowPerShareTTM"),
                    "revenue_growth": metrics.get("revenueGrowthTTMYoy"),
                    "roe": metrics.get("roeTTM"),
                    "profit_margins": metrics.get("netProfitMarginTTM"),
                    "debt_to_equity": metrics.get("debtToEquityTTM"),
                    "quick_ratio": metrics.get("quickRatioTTM"),
                }
                payload["fundamentals"] = {
                    k: v for k, v in fundamentals.items() if v is not None
                }
        except Exception as exc:
            raise ProviderError(f"FMP metrics fetch failed: {exc}") from exc

        try:
            history_resp = requests.get(
                f"{self.base_url}/historical-key-metrics/{ticker}",
                params={**params, "period": "annual", "limit": 6},
                timeout=10,
            )
            history_resp.raise_for_status()
            history_data = history_resp.json()
            if isinstance(history_data, list) and history_data:
                cleaned: List[Dict[str, Any]] = []
                for entry in history_data:
                    cleaned.append(
                        {
                            "period": entry.get("calendarYear"),
                            "currency": entry.get("financialCurrency")
                            or payload.get("fundamentals", {}).get("currency")
                            or "USD",
                            "eps": entry.get("eps"),
                            "pe": entry.get("peRatio"),
                            "peg": entry.get("pegRatio"),
                            "ev_to_ebit": entry.get("evToEbit"),
                            "pb": entry.get("pbRatio"),
                            "fcf_yield": entry.get("freeCashFlowPerShareTTM"),
                        }
                    )
                payload["history"] = cleaned
        except Exception:
            pass

        currency = payload.get("fundamentals", {}).get("currency")
        if currency and currency.upper() != "USD":
            try:
                fx_resp = requests.get(
                    f"{self.base_url}/fx/{currency.upper()}USD",
                    params=params,
                    timeout=10,
                )
                fx_resp.raise_for_status()
                fx_json = fx_resp.json()
                if isinstance(fx_json, list) and fx_json:
                    latest = fx_json[0]
                    price = latest.get("price")
                    if price:
                        payload["exchange_rates"] = {
                            "USD": 1.0,
                            currency.upper(): float(price),
                        }
            except Exception:
                pass

        try:
            history_resp = requests.get(
                f"{self.base_url}/historical-price-full/{ticker}",
                params={**params, "timeseries": 365},
                timeout=10,
            )
            history_resp.raise_for_status()
            history_json = history_resp.json() or {}
            items = history_json.get("historical", [])
            if isinstance(items, list) and items:
                cleaned_prices: List[Dict[str, Any]] = []
                for entry in items:
                    cleaned_prices.append(
                        {
                            "date": entry.get("date"),
                            "open": _safe_float(entry.get("open")),
                            "high": _safe_float(entry.get("high")),
                            "low": _safe_float(entry.get("low")),
                            "close": _safe_float(entry.get("close")),
                            "volume": _safe_float(entry.get("volume")),
                        }
                    )
                cleaned_prices = [
                    row
                    for row in cleaned_prices
                    if row["date"] and row["close"] is not None
                ]
                cleaned_prices.sort(key=lambda row: row["date"])
                if cleaned_prices:
                    payload["price_history"] = cleaned_prices
                    latest = cleaned_prices[-1]
                    prev_close = (
                        cleaned_prices[-2]["close"] if len(cleaned_prices) > 1 else None
                    )
                    currency_code = (
                        payload.get("fundamentals", {}).get("currency")
                        or payload.get("profile", {}).get("currency")
                        or "USD"
                    )
                    price_payload = {
                        "currency": (currency_code or "USD"),
                        "close": latest["close"],
                        "open": latest["open"],
                    }
                    if prev_close is not None:
                        price_payload["previous_close"] = prev_close
                    payload["prices"] = price_payload
        except Exception:
            pass

        return payload


class AlphaVantageProvider(BaseProvider):
    name = "alpha"
    categories = ("fundamentals", "prices", "exchange_rates")

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        self.base_url = os.getenv(
            "ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co/query"
        )

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        if not self.api_key:
            raise ProviderError("Missing Alpha Vantage API key")

        payload: Dict[str, Dict[str, Any]] = {}

        try:
            overview_resp = requests.get(
                self.base_url,
                params={
                    "function": "OVERVIEW",
                    "symbol": ticker,
                    "apikey": self.api_key,
                },
                timeout=10,
            )
            overview_resp.raise_for_status()
            overview = overview_resp.json()
            if overview:
                payload["fundamentals"] = {
                    "currency": overview.get("Currency"),
                    "eps": _safe_float(overview.get("EPS")),
                    "pe": _safe_float(overview.get("PERatio")),
                    "peg": _safe_float(overview.get("PEGRatio")),
                    "pb": _safe_float(overview.get("PriceToBookRatio")),
                    "fcf_yield": _safe_float(overview.get("DividendYield")),
                    "revenue_growth": _safe_float(
                        overview.get("QuarterlyRevenueGrowthYOY")
                    ),
                    "profit_margins": _safe_float(overview.get("ProfitMargin")),
                    "roe": _safe_float(overview.get("ReturnOnEquityTTM")),
                    "debt_to_equity": _safe_float(overview.get("DebtToEquityRatio")),
                }
                payload["profile"] = {
                    "name": overview.get("Name"),
                    "sector": overview.get("Sector"),
                    "industry": overview.get("Industry"),
                    "exchange": overview.get("Exchange"),
                }
        except Exception as exc:
            raise ProviderError(f"Alpha Vantage overview fetch failed: {exc}") from exc

        try:
            price_resp = requests.get(
                self.base_url,
                params={
                    "function": "TIME_SERIES_DAILY_ADJUSTED",
                    "symbol": ticker,
                    "apikey": self.api_key,
                    "outputsize": "compact",
                },
                timeout=10,
            )
            price_resp.raise_for_status()
            price_json = price_resp.json()
            series = price_json.get("Time Series (Daily)", {})
            if series:
                latest_date = sorted(series.keys())[-1]
                latest_values = series[latest_date]
                payload["prices"] = {
                    "currency": payload.get("fundamentals", {}).get("currency", "USD"),
                    "close": _safe_float(latest_values.get("4. close")),
                    "open": _safe_float(latest_values.get("1. open")),
                }
        except Exception:
            pass

        currency = payload.get("fundamentals", {}).get("currency")
        if currency and currency.upper() != "USD":
            try:
                fx_resp = requests.get(
                    self.base_url,
                    params={
                        "function": "CURRENCY_EXCHANGE_RATE",
                        "from_currency": currency.upper(),
                        "to_currency": "USD",
                        "apikey": self.api_key,
                    },
                    timeout=10,
                )
                fx_resp.raise_for_status()
                fx_json = fx_resp.json()
                exchange = fx_json.get("Realtime Currency Exchange Rate", {})
                rate = exchange.get("5. Exchange Rate")
                if rate:
                    payload["exchange_rates"] = {
                        "USD": 1.0,
                        currency.upper(): float(rate),
                    }
            except Exception:
                pass

        return payload


class FinnhubProvider(BaseProvider):
    name = "finnhub"
    categories = ("fundamentals", "profile")

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        self.base_url = os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1")

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        if not self.api_key:
            raise ProviderError("Missing Finnhub API key")

        payload: Dict[str, Dict[str, Any]] = {}
        params = {"symbol": ticker, "token": self.api_key}

        try:
            profile_resp = requests.get(
                f"{self.base_url}/stock/profile2", params=params, timeout=10
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()
            payload["profile"] = {
                "name": profile.get("name"),
                "sector": profile.get("finnhubIndustry"),
                "industry": profile.get("finnhubIndustry"),
                "exchange": profile.get("exchange"),
                "currency": profile.get("currency"),
            }
        except Exception as exc:
            raise ProviderError(f"Finnhub profile fetch failed: {exc}") from exc

        try:
            metrics_resp = requests.get(
                f"{self.base_url}/stock/metric",
                params={**params, "metric": "all"},
                timeout=10,
            )
            metrics_resp.raise_for_status()
            metrics_json = metrics_resp.json() or {}
            series = metrics_json.get("metric") or {}
            payload["fundamentals"] = {
                "currency": payload.get("profile", {}).get("currency", "USD"),
                "eps": _safe_float(series.get("epsBasicExclExtraTTM")),
                "pe": _safe_float(series.get("peTTM")),
                "peg": _safe_float(series.get("pegratio")),
                "ev_to_ebit": _safe_float(
                    series.get("enterpriseValueOverEBITDAAnnual")
                ),
                "pb": _safe_float(series.get("pbAnnual")),
                "fcf_yield": _safe_float(series.get("freeCashFlowPerShareTTM")),
                "revenue_growth": _safe_float(series.get("revenueGrowthAnnualYY")),
                "profit_margins": _safe_float(series.get("netProfitMarginAnnual")),
                "roe": _safe_float(series.get("roeAnnual")),
                "debt_to_equity": _safe_float(series.get("totalDebtTotalEquityAnnual")),
                "quick_ratio": _safe_float(series.get("quickRatioAnnual")),
            }
        except Exception as exc:
            raise ProviderError(f"Finnhub metrics fetch failed: {exc}") from exc

        return payload


class CSVImportProvider(BaseProvider):
    name = "csv"
    categories = ("fundamentals", "profile")

    def __init__(self, directory: Optional[Path]) -> None:
        self.directory = directory

    def fetch(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        if not self.directory:
            return {}
        csv_path = self.directory / f"{ticker.upper()}.csv"
        if not csv_path.exists():
            return {}

        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            first_row = next(reader, None)
            if not first_row:
                return {}

        fundamentals = {
            "currency": first_row.get("currency", "USD"),
            "eps": _safe_float(first_row.get("eps")),
            "pe": _safe_float(first_row.get("pe")),
            "peg": _safe_float(first_row.get("peg")),
            "ev_to_ebit": _safe_float(first_row.get("ev_to_ebit")),
            "pb": _safe_float(first_row.get("pb")),
            "fcf_yield": _safe_float(first_row.get("fcf_yield")),
            "revenue_growth": _safe_float(first_row.get("revenue_growth")),
            "roe": _safe_float(first_row.get("roe")),
            "profit_margins": _safe_float(first_row.get("profit_margins")),
            "debt_to_equity": _safe_float(first_row.get("debt_to_equity")),
            "quick_ratio": _safe_float(first_row.get("quick_ratio")),
        }

        profile = {
            "name": first_row.get("name") or ticker.upper(),
            "sector": first_row.get("sector"),
            "industry": first_row.get("industry"),
            "exchange": first_row.get("exchange"),
        }

        return {
            "fundamentals": {k: v for k, v in fundamentals.items() if v is not None},
            "profile": {k: v for k, v in profile.items() if v},
        }


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def create_default_providers(
    base_path: Optional[Path] = None,
) -> Dict[str, BaseProvider]:
    directory = None
    if base_path:
        directory = (base_path / "docs" / "imports").resolve()
        if not directory.exists():
            directory = None

    providers: Dict[str, BaseProvider] = {
        "yahoo": YahooFinanceProvider(),
        "fmp": FMPProvider(get_api_key("api_key_fmp")),
        "alpha": AlphaVantageProvider(get_api_key("api_key_alphavantage")),
        "finnhub": FinnhubProvider(get_api_key("api_key_finnhub")),
        "csv": CSVImportProvider(directory),
    }
    return providers


class MultiSourceDataClient:
    """Aggregates financial data across providers, normalises, then persists to SQLite."""

    def __init__(
        self,
        store: SQLiteDataStore,
        converter: CurrencyConverter,
        providers: Optional[Dict[str, BaseProvider]] = None,
        precedence: Optional[Dict[str, Sequence[str]]] = None,
    ) -> None:
        self.store = store
        self.base_converter = converter
        base_path = Path(__file__).resolve().parents[1]
        self.providers = providers or create_default_providers(base_path)
        self.precedence = precedence or DEFAULT_PRECEDENCE
        self.category_order = tuple(self.precedence.keys())
        self.store.set_precedence(self.precedence)

    def sync_ticker(
        self,
        ticker: str,
        as_of: Optional[datetime] = None,
        categories: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        as_of_dt = _ensure_tz(as_of or datetime.now(timezone.utc))

        request_categories = tuple(categories) if categories else self.category_order

        aggregated: Dict[str, Any] = {}
        providers_used: Dict[str, Optional[str]] = {}
        provider_cache: Dict[str, Dict[str, Any]] = {}
        rate_overrides: Dict[str, float] = {}

        for category in request_categories:
            provider_names = self.precedence.get(category, ())

            for provider_name in provider_names:
                provider = self.providers.get(provider_name)
                if not provider:
                    continue

                if provider_name in provider_cache:
                    payload = provider_cache[provider_name]
                else:
                    try:
                        payload = provider.fetch(ticker)
                    except ProviderError as exc:
                        provider_cache[provider_name] = {}
                        self.store.update_provider_meta(
                            provider_name,
                            category,
                            success=False,
                            as_of=as_of_dt,
                            message=str(exc),
                        )
                        continue
                    except Exception as exc:  # pragma: no cover
                        provider_cache[provider_name] = {}
                        self.store.update_provider_meta(
                            provider_name,
                            category,
                            success=False,
                            as_of=as_of_dt,
                            message=f"{type(exc).__name__}: {exc}",
                        )
                        continue
                    provider_cache[provider_name] = payload or {}

                payload = provider_cache[provider_name]
                category_payload = payload.get(category)
                if category_payload:
                    aggregated[category] = category_payload
                    providers_used[category] = provider_name
                    self.store.update_provider_meta(
                        provider_name, category, True, as_of_dt
                    )
                    if category == "exchange_rates":
                        try:
                            rate_overrides.update(
                                {
                                    code.upper(): float(rate)
                                    for code, rate in category_payload.items()
                                    if rate is not None
                                }
                            )
                        except Exception:
                            pass
                    break
                else:
                    self.store.update_provider_meta(
                        provider_name,
                        category,
                        False,
                        as_of_dt,
                        "no data",
                    )
            else:
                providers_used.setdefault(category, None)

        converter = self.base_converter.extend(rate_overrides)
        snapshot = self._normalize_snapshot(
            ticker, as_of_dt, aggregated, providers_used, converter
        )

        # Persist normalized snapshot (fundamentals/prices) as before
        self.store.persist_snapshot(snapshot)

        # Persist FX snapshot (rates) and obtain fx_snapshot_id for reproducibility
        try:
            fx_snapshot_id = self.store.save_fx_snapshot(
                as_of_dt, providers_used.get("exchange_rates"), converter.rates
            )
        except Exception:
            fx_snapshot_id = None
        if aggregated.get("history"):
            self.store.persist_history(
                ticker,
                aggregated["history"],
                providers_used.get("fundamentals"),
                as_of_dt,
                converter,
            )
        if aggregated.get("prices"):
            self.store.persist_price(
                ticker,
                aggregated["prices"],
                providers_used.get("prices"),
                as_of_dt,
                converter,
            )
        if aggregated.get("ownership"):
            ownership_payload = aggregated["ownership"]
            if isinstance(ownership_payload, dict):
                ownership_entries = [ownership_payload]
            else:
                ownership_entries = list(ownership_payload)
            self.store.save_ownership_history(
                ticker,
                ownership_entries,
                providers_used.get("ownership"),
                as_of_dt,
            )

        return self._build_stock_info(snapshot, fx_snapshot_id=fx_snapshot_id)

    def _normalize_snapshot(
        self,
        ticker: str,
        as_of: datetime,
        aggregated: Dict[str, Any],
        providers_used: Dict[str, Optional[str]],
        converter: CurrencyConverter,
    ) -> NormalizedSnapshot:
        fundamentals = aggregated.get("fundamentals") or {}
        prices = aggregated.get("prices") or {}
        dividends = aggregated.get("dividends") or {}
        profile = aggregated.get("profile") or {}
        history_entries_raw = aggregated.get("history") or []
        price_history_raw = aggregated.get("price_history") or []
        history_entries = []
        for entry in history_entries_raw:
            if isinstance(entry, dict):
                history_entries.append(entry.copy())
        history_entries.sort(
            key=lambda item: (
                item.get("as_of") or item.get("period") or item.get("date") or ""
            ),
            reverse=True,
        )

        price_history_entries: List[Dict[str, Any]] = []
        for entry in price_history_raw:
            if not isinstance(entry, dict):
                continue
            date = entry.get("date") or entry.get("datetime")
            open_price = _safe_float(entry.get("open") or entry.get("open_price"))
            high_price = _safe_float(entry.get("high"))
            low_price = _safe_float(entry.get("low"))
            close_price = _safe_float(entry.get("close"))
            volume = entry.get("volume")
            if (
                date is None
                or open_price is None
                or high_price is None
                or low_price is None
                or close_price is None
            ):
                continue
            price_history_entries.append(
                {
                    "date": date,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": float(volume) if volume not in (None, "") else None,
                }
            )
        price_history_entries.sort(key=lambda item: item["date"])

        currency = (
            fundamentals.get("currency")
            or prices.get("currency")
            or profile.get("currency")
            or "USD"
        )
        currency = currency.upper() if isinstance(currency, str) else "USD"

        exchange = profile.get("exchange")
        country = profile.get("country")

        fundamentals_converted = {}
        eps = fundamentals.get("eps")
        if eps is not None:
            fundamentals_converted["eps_usd"] = converter.convert(eps, currency, "USD")
            fundamentals_converted["eps_eur"] = converter.convert(eps, currency, "EUR")

        price_currency = (prices.get("currency") or currency).upper()
        close = (
            prices.get("close")
            or prices.get("price")
            or prices.get("regularMarketPrice")
        )
        prev_close = prices.get("previous_close") or prices.get("previousClose")
        open_price = prices.get("open") or prices.get("open_price")

        prices_clean = {
            "currency": price_currency,
            "close": close,
            "previous_close": prev_close,
            "open": open_price,
        }

        prices_converted: Dict[str, Optional[float]] = {}
        if close is not None:
            prices_converted["close_usd"] = converter.convert(
                close, price_currency, "USD"
            )
            prices_converted["close_eur"] = converter.convert(
                close, price_currency, "EUR"
            )
        if prev_close is not None:
            prices_converted["previous_close_usd"] = converter.convert(
                prev_close, price_currency, "USD"
            )
            prices_converted["previous_close_eur"] = converter.convert(
                prev_close, price_currency, "EUR"
            )
        if open_price is not None:
            prices_converted["open_usd"] = converter.convert(
                open_price, price_currency, "USD"
            )
            prices_converted["open_eur"] = converter.convert(
                open_price, price_currency, "EUR"
            )

        providers_map = {
            category: providers_used.get(category) for category in self.category_order
        }

        return NormalizedSnapshot(
            ticker=ticker,
            as_of=as_of,
            currency=currency,
            exchange=exchange,
            country=country,
            fundamentals=fundamentals,
            fundamentals_converted=fundamentals_converted,
            prices=prices_clean,
            prices_converted=prices_converted,
            dividends=dividends,
            profile=profile,
            providers=providers_map,
            history=history_entries,
            price_history=price_history_entries,
            fx_rates=converter.rates,
        )

    def _build_stock_info(
        self, snapshot: NormalizedSnapshot, fx_snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "ticker": snapshot.ticker,
            "currency": snapshot.prices.get("currency", snapshot.currency),
            "exchange": snapshot.exchange,
            "country": snapshot.country,
            "regularMarketPrice": snapshot.prices.get("close"),
            "regularMarketPreviousClose": snapshot.prices.get("previous_close"),
            "regularMarketPriceUSD": snapshot.prices_converted.get("close_usd"),
            "regularMarketPriceEUR": snapshot.prices_converted.get("close_eur"),
            "previousCloseUSD": snapshot.prices_converted.get("previous_close_usd"),
            "previousCloseEUR": snapshot.prices_converted.get("previous_close_eur"),
            "normalized": {
                "fundamentals": snapshot.fundamentals_converted,
                "prices": snapshot.prices_converted,
            },
            "fetched_at": snapshot.as_of.isoformat().replace("+00:00", "Z"),
            "historicalMetrics": snapshot.history,
            "priceHistory": snapshot.price_history,
        }

        # Add FX snapshot metadata and timestamps
        info["fx_snapshot"] = snapshot.fx_rates or {}
        info["fx_snapshot_id"] = fx_snapshot_id
        # Small human-readable summary: top 5 currencies by code
        if snapshot.fx_rates:
            try:
                top_items = sorted(snapshot.fx_rates.items(), key=lambda kv: kv[0])[:5]
                info["fx_snapshot_summary"] = {k: v for k, v in top_items}
            except Exception:
                info["fx_snapshot_summary"] = {}
        info["asof_utc"] = snapshot.as_of.isoformat().replace("+00:00", "Z")
        # Compute asof_exchange_tz using a simple exchange->timezone mapping when possible.
        exchange_tz_map = {
            "NYSE": "America/New_York",
            "NASDAQ": "America/New_York",
            "AMEX": "America/New_York",
            "TSX": "America/Toronto",
            "LSE": "Europe/London",
            "XETRA": "Europe/Berlin",
            "FWB": "Europe/Berlin",
            "SSE": "Asia/Shanghai",
            "SZSE": "Asia/Shanghai",
            "HKEX": "Asia/Hong_Kong",
            "JPX": "Asia/Tokyo",
            "BSE": "Asia/Kolkata",
        }

        asof_utc_dt = snapshot.as_of
        tz_name = None
        try:
            if snapshot.exchange and isinstance(snapshot.exchange, str):
                tz_name = exchange_tz_map.get(snapshot.exchange.upper())
        except Exception:
            tz_name = None

        if tz_name and ZoneInfo is not None:
            try:
                local_dt = asof_utc_dt.astimezone(ZoneInfo(tz_name))
                info["asof_exchange_tz"] = local_dt.isoformat()
            except Exception:
                info["asof_exchange_tz"] = info["asof_utc"]
        else:
            info["asof_exchange_tz"] = info["asof_utc"]

        # Determine if any category used a fallback provider (not the top-precedence provider)
        fallback = False
        for category, provider in snapshot.providers.items():
            if provider is None:
                continue
            preferred = None
            try:
                preferred = self.precedence.get(category, ())[0]
            except Exception:
                preferred = None
            if preferred and provider != preferred:
                fallback = True
                break
        info["provider_fallback"] = fallback

        data_providers = {
            "fundamentals": snapshot.providers.get("fundamentals"),
            "prices": snapshot.providers.get("prices"),
            "dividends": snapshot.providers.get("dividends"),
            "profile": snapshot.providers.get("profile"),
            "history": snapshot.providers.get("history"),
            "price_history": snapshot.providers.get("price_history"),
            "ownership": snapshot.providers.get("ownership"),
        }
        info["data_providers"] = {
            key: (value or "unavailable") for key, value in data_providers.items()
        }

        fundamentals = snapshot.fundamentals
        info.update(
            {
                "eps": fundamentals.get("eps"),
                "trailingPE": fundamentals.get("pe"),
                "pegRatio": fundamentals.get("peg"),
                "priceToBook": fundamentals.get("pb"),
                "fcfYield": fundamentals.get("fcf_yield"),
                "revenueGrowth": fundamentals.get("revenue_growth"),
                "profitMargins": fundamentals.get("profit_margins"),
                "returnOnEquity": fundamentals.get("roe"),
                "returnOnEquityTTM": fundamentals.get("roe"),
                "debtToEquity": fundamentals.get("debt_to_equity"),
                "quickRatio": fundamentals.get("quick_ratio"),
                "evToEbit": fundamentals.get("ev_to_ebit"),
            }
        )

        dividends = snapshot.dividends
        info["dividendYield"] = dividends.get("forward_yield")
        info["payoutRatio"] = dividends.get("payout_ratio")

        profile = snapshot.profile
        info["longName"] = (
            profile.get("longName")
            or profile.get("name")
            or profile.get("companyName")
            or snapshot.ticker
        )
        info["sector"] = profile.get("sector")
        info["industry"] = profile.get("industry")
        info["exchange"] = profile.get("exchange")
        info["marketCap"] = profile.get("marketCap")
        info["country"] = profile.get("country")

        ownership_rows = self.store.load_ownership_history(snapshot.ticker)
        info["ownershipHistory"] = [
            {
                "date": row["date"].isoformat().replace("+00:00", "Z"),
                "source": row.get("source"),
                "institutional": row.get("institutional"),
                "insider": row.get("insider"),
            }
            for row in ownership_rows
        ]

        return info


class SchedulerHooks:
    """Exposes scheduler-friendly descriptors for refresh jobs."""

    def __init__(
        self,
        client: MultiSourceDataClient,
        desktop_cron_expression: str = "0 */6 * * *",
        android_interval_minutes: int = 360,
        android_flex_minutes: int = 45,
    ) -> None:
        self.client = client
        self.desktop_cron_expression = desktop_cron_expression
        self.android_interval_minutes = android_interval_minutes
        self.android_flex_minutes = android_flex_minutes

    def build_jobs(
        self,
        tickers: Sequence[str],
        categories: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        cat_order = list(categories or self.client.category_order)
        jobs: List[Dict[str, Any]] = []

        for ticker in tickers:
            work_job = {
                "platform": "android",
                "work_manager": {
                    "name": f"sync-{ticker.lower()}",
                    "ticker": ticker,
                    "interval_minutes": self.android_interval_minutes,
                    "flex_minutes": self.android_flex_minutes,
                    "requires_network": True,
                    "requires_battery_not_low": True,
                    "categories": cat_order,
                },
                "categories": cat_order,
            }
            jobs.append(work_job)

            callable_ref = partial(self.client.sync_ticker, ticker, categories=None)
            cron_job = {
                "platform": "desktop",
                "cron": {"expression": self.desktop_cron_expression},
                "callable": callable_ref,
                "ticker": ticker,
                "categories": cat_order,
            }
            jobs.append(cron_job)

        return jobs


__all__ = [
    "CurrencyConverter",
    "DEFAULT_PRECEDENCE",
    "MultiSourceDataClient",
    "SchedulerHooks",
    "SQLiteDataStore",
    "create_default_providers",
]
