"""
Resilient helpers wrapped around ``yfinance``.

The original BD_Finance project ships a fair amount of defensive code to keep
Yahoo Finance calls alive in spite of throttling and transient HTTPS issues.
For the test-suite we only need a lightweight, dependency free shim that
implements the same public surface (`download_data_robust`,
`get_ticker_info_robust`) and behaves sensibly when the network or upstream
service refuses to cooperate.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional


def _load_yfinance():
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised when library missing
        raise ImportError(
            "yfinance is required for utils.yfinance_utils helpers"
        ) from exc
    return yf


def _sleep(backoff: float, jitter: float) -> None:
    time.sleep(backoff + random.random() * jitter)


def download_data_robust(
    ticker: str,
    *,
    period: str = "1mo",
    interval: str = "1d",
    max_retries: int = 5,
    base_backoff: float = 1.5,
    jitter: float = 0.75,
) -> Any:
    """
    Download OHLCV data with simple retry/back-off logic.

    The helper purposely keeps the surface area extremely small – callers get
    back whatever ``yfinance.download`` returns (usually a pandas ``DataFrame``),
    and we only raise if every attempt fails.
    """

    yf = _load_yfinance()
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                threads=False,
            )
            if getattr(data, "empty", True):
                # Empty responses are common when Yahoo throttles – retry.
                last_exception = RuntimeError("Empty payload received from yfinance")
            else:
                return data
        except Exception as exc:  # pragma: no cover - dependent on network issues
            last_exception = exc

        # Progressive back-off with jitter to avoid hammering Yahoo.
        _sleep(base_backoff * (attempt + 1), jitter)

    if last_exception:
        raise last_exception
    return None


def get_ticker_info_robust(
    ticker: str,
    *,
    include_fast_info: bool = True,
    max_retries: int = 4,
    base_backoff: float = 1.0,
) -> Dict[str, Any]:
    """
    Retrieve ticker metadata with retries and graceful degradation.
    """

    yf = _load_yfinance()
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            instrument = yf.Ticker(ticker)
            info: Dict[str, Any] = {}

            try:
                raw_info = instrument.get_info()
                if isinstance(raw_info, dict):
                    info.update(raw_info)
            except Exception:  # pragma: no cover - depends on upstream behaviour
                # ``get_info`` is notoriously brittle – we silently ignore failures.
                pass

            if include_fast_info:
                fast_info = getattr(instrument, "fast_info", None)
                if fast_info:
                    info.setdefault("longName", getattr(fast_info, "longName", None))
                    info.setdefault("currency", getattr(fast_info, "currency", None))

            if info:
                return info
            last_exception = RuntimeError("yfinance returned no metadata")
        except Exception as exc:  # pragma: no cover - network dependent
            last_exception = exc

        _sleep(base_backoff * (attempt + 1), 0.5)

    if last_exception:
        raise last_exception
    return {}


__all__ = ["download_data_robust", "get_ticker_info_robust"]
