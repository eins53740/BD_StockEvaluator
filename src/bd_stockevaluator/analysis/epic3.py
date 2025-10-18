from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:  # Plotly optional; fallback to placeholder rendering.
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:  # pragma: no cover - graceful fallback when plotly missing.
    go = None
    make_subplots = None

import yfinance as yf


MIN_HISTORY_POINTS = 60
DEFAULT_PERIOD = "2y"
DEFAULT_INTERVAL = "1d"
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_DEFAULT = 0.02

PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06"
    b"\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88"
    b"\x00\x00\x00\x19tEXtSoftware\x00python-epic3\x17\xce\x8c\x1e\x00\x00\x00"
    b"\x0cIDATx\x9cc````\x00\x00\x00\x06\x00\x03\x06\x91\xdd\xd5\x00\x00\x00\x00"
    b"IEND\xaeB`\x82"
)


def _ensure_dataframe(price_history: Sequence[MutableMapping[str, Any]]) -> pd.DataFrame:
    """Normalise the supplied price history into a sorted DataFrame."""

    if not price_history:
        raise ValueError("Price history is required for technical analysis.")

    df = pd.DataFrame(price_history)
    expected_columns = {"open", "high", "low", "close"}
    if not expected_columns <= set(df.columns):
        raise ValueError(f"Price history entries must contain {expected_columns}")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
    else:
        df = df.copy()
        df.index = pd.RangeIndex(len(df))

    if "volume" not in df.columns:
        df["volume"] = np.nan

    df = df.astype({"open": float, "high": float, "low": float, "close": float}, copy=False)
    return df


def _fetch_price_history(
    ticker: str,
    *,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> List[Dict[str, Any]]:
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval, auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError(f"Unable to download history for {ticker}")
    hist = hist.reset_index()

    records: List[Dict[str, Any]] = []
    for row in hist.itertuples(index=False):
        date = getattr(row, "Date")
        records.append(
            {
                "date": datetime.fromtimestamp(date.timestamp()) if hasattr(date, "timestamp") else date,
                "open": float(getattr(row, "Open")),
                "high": float(getattr(row, "High")),
                "low": float(getattr(row, "Low")),
                "close": float(getattr(row, "Close")),
                "volume": float(getattr(row, "Volume", np.nan)),
            }
        )
    return records


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _wilder_smoothing(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False).mean()


def _rolling_levels(series: pd.Series, window: int, mode: str) -> List[float]:
    levels: List[float] = []
    comparator = np.less if mode == "support" else np.greater
    for idx in range(window, len(series) - window):
        window_slice = series.iloc[idx - window : idx + window + 1]
        center_value = series.iloc[idx]
        if comparator(center_value, window_slice.drop(series.index[idx]).values).all():
            levels.append(center_value)
    return levels


def _deduplicate_levels(levels: Iterable[float], tolerance: float = 0.01, reverse: bool = False) -> List[float]:
    uniques: List[float] = []
    for level in sorted(levels, reverse=reverse):
        if not uniques:
            uniques.append(level)
            continue
        if abs(level - uniques[-1]) / max(abs(level), 1e-6) > tolerance:
            uniques.append(level)
    return uniques[:3]


def _write_placeholder_png(path: Path) -> None:
    path.write_bytes(PLACEHOLDER_PNG)


@dataclass
class Hysteresis:
    bucket: str
    entry_buy: float = 7.0
    exit_buy: float = 6.0
    entry_sell: float = 3.0
    exit_sell: float = 4.0

    def transition(self, score: float) -> str:
        if self.bucket == "buy":
            if score < self.exit_buy:
                return "hold" if score > self.exit_sell else "sell"
            return "buy"
        if self.bucket == "sell":
            if score > self.exit_sell:
                return "hold" if score < self.exit_buy else "buy"
            return "sell"

        # current = hold
        if score >= self.entry_buy:
            return "buy"
        if score <= self.entry_sell:
            return "sell"
        return "hold"


class Epic3TechnicalAnalyzer:
    """Compute Epic 3 technical analytics for a given ticker or price history."""

    def __init__(
        self,
        price_history: Sequence[MutableMapping[str, Any]],
        *,
        ticker: Optional[str] = None,
    ) -> None:
        self.ticker = ticker
        self._df = _ensure_dataframe(price_history)
        if len(self._df) < MIN_HISTORY_POINTS:
            # Allow but flag for downstream logic.
            self._insufficient_history = True
        else:
            self._insufficient_history = False
        self._cache: Dict[str, Any] = {}

    @classmethod
    def from_ticker(
        cls,
        ticker: str,
        *,
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
    ) -> "Epic3TechnicalAnalyzer":
        records = _fetch_price_history(ticker, period=period, interval=interval)
        return cls(records, ticker=ticker)

    # ------------------------------------------------------------------ #
    # Indicator Suite

    def compute_indicator_suite(self) -> Dict[str, Any]:
        if "indicators" in self._cache:
            return self._cache["indicators"]

        df = self._df.copy()
        close = df["close"]

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        delta = close.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)
        avg_gain = _wilder_smoothing(gains, 14)
        avg_loss = _wilder_smoothing(losses, 14)
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50.0)

        high = df["high"]
        low = df["low"]
        prev_close = close.shift(1)

        tr_components = pd.concat(
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        )
        true_range = tr_components.max(axis=1)
        atr = _wilder_smoothing(true_range, 14)

        up_move = high.diff()
        down_move = low.diff() * -1
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)

        plus_di = 100 * (_wilder_smoothing(plus_dm, 14) / atr.replace(0, np.nan))
        minus_di = 100 * (_wilder_smoothing(minus_dm, 14) / atr.replace(0, np.nan))
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
        adx = _wilder_smoothing(dx.fillna(0.0), 14)

        sma20_series = close.rolling(window=20).mean()
        sma50_series = close.rolling(window=50).mean()
        sma200_series = close.rolling(window=200).mean()

        std20 = close.rolling(window=20).std(ddof=0)
        middle_band = sma20_series
        upper_band = middle_band + 2 * std20
        lower_band = middle_band - 2 * std20

        last_close = close.iloc[-1]
        last_upper = _safe_float(upper_band.iloc[-1])
        last_lower = _safe_float(lower_band.iloc[-1])
        last_middle = _safe_float(middle_band.iloc[-1])

        if last_upper is None or last_lower is None:
            price_position = "middle"
        elif last_close >= last_upper:
            price_position = "upper"
        elif last_close <= last_lower:
            price_position = "lower"
        else:
            price_position = "middle"

        indicators = {
            "macd": {
                "line": _safe_float(macd_line.iloc[-1]),
                "signal": _safe_float(signal_line.iloc[-1]),
                "histogram": _safe_float(macd_hist.iloc[-1]),
            },
            "rsi": {
                "value": round(float(rsi.iloc[-1]), 2),
            },
            "adx": {
                "adx": _safe_float(adx.iloc[-1]),
                "plus_di": _safe_float(plus_di.iloc[-1]),
                "minus_di": _safe_float(minus_di.iloc[-1]),
            },
            "bollinger": {
                "upper": last_upper,
                "middle": last_middle,
                "lower": last_lower,
                "price_position": price_position,
            },
            "sma": {
                "sma20": _safe_float(sma20_series.iloc[-1]),
                "sma50": _safe_float(sma50_series.iloc[-1]),
                "sma200": _safe_float(sma200_series.iloc[-1]),
                "last_close": last_close,
            },
        }

        self._cache["indicators"] = indicators
        return indicators

    # ------------------------------------------------------------------ #
    # Pattern Detection

    def detect_price_patterns(self) -> Dict[str, Any]:
        if "patterns" in self._cache:
            return self._cache["patterns"]

        df = self._df
        closes = df["close"]

        supports_raw = _rolling_levels(closes, window=3, mode="support")
        resistances_raw = _rolling_levels(closes, window=3, mode="resistance")

        supports = _deduplicate_levels(supports_raw, tolerance=0.015)
        resistances = _deduplicate_levels(resistances_raw, tolerance=0.015, reverse=True)

        lookback_high = df["high"].rolling(window=90, min_periods=1).max().iloc[-1]
        lookback_low = df["low"].rolling(window=90, min_periods=1).min().iloc[-1]
        price_range = lookback_high - lookback_low
        if price_range <= 0:
            price_range = max(df["high"].max() - df["low"].min(), 1e-6)

        peak_level = round(float(lookback_high), 2)
        if not resistances:
            resistances = [peak_level]
        elif all(abs(level - peak_level) > 0.5 for level in resistances):
            resistances = [peak_level, *resistances]
        else:
            resistances[0] = peak_level

        fibonacci = {
            "0.0": lookback_high,
            "0.236": lookback_high - price_range * 0.236,
            "0.382": lookback_high - price_range * 0.382,
            "0.5": lookback_high - price_range * 0.5,
            "0.618": lookback_high - price_range * 0.618,
            "0.786": lookback_high - price_range * 0.786,
            "1.0": lookback_low,
        }

        trend_window = min(len(closes), 90)
        y = closes.iloc[-trend_window:]
        x = np.arange(len(y))
        if len(y) >= 2:
            slope, intercept = np.polyfit(x, y, 1)
        else:
            slope, intercept = 0.0, y.iloc[-1] if not y.empty else 0.0

        start_price = intercept
        end_price = intercept + slope * (len(y) - 1)

        trendline = {
            "slope": round(float(slope), 6),
            "intercept": round(float(intercept), 4),
            "endpoints": {
                "start": {
                    "index": int(df.index[-trend_window].to_julian_date()) if hasattr(df.index, "to_julian_date") else int(x[0]),
                    "price": round(float(start_price), 2),
                },
                "end": {
                    "index": int(df.index[-1].to_julian_date()) if hasattr(df.index, "to_julian_date") else int(x[-1]),
                    "price": round(float(end_price), 2),
                },
            },
        }

        patterns = {
            "support_levels": [round(float(level), 2) for level in supports],
            "resistance_levels": [round(float(level), 2) for level in resistances],
            "fibonacci": {key: round(float(value), 2) for key, value in fibonacci.items()},
            "trendline": trendline,
        }

        self._cache["patterns"] = patterns
        return patterns

    # ------------------------------------------------------------------ #
    # Signal Generation

    def generate_signal(
        self,
        *,
        verdict: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        indicators = self.compute_indicator_suite()
        patterns = self.detect_price_patterns()
        momentum_score, trend_score, notes = self._score_components(indicators, patterns)
        total_score = min(10.0, round(trend_score + momentum_score, 2))

        fundamental_bias = 0.0
        verdict_normalized = (verdict or "").lower()
        if "do not buy" in verdict_normalized or "sell" in verdict_normalized:
            fundamental_bias = -1.0
        elif "buy" in verdict_normalized:
            fundamental_bias = 0.5

        biased_score = max(0.0, min(10.0, total_score + fundamental_bias))

        thresholds = {"buy": 7.0, "sell": 3.0}
        if previous_state and "bucket" in previous_state:
            hysteresis = Hysteresis(
                bucket=previous_state.get("bucket", "hold"),
                entry_buy=thresholds["buy"],
                exit_buy=thresholds["buy"] - 1.0,
                entry_sell=thresholds["sell"],
                exit_sell=thresholds["sell"] + 1.0,
            )
            bucket = hysteresis.transition(biased_score)
        else:
            if biased_score >= thresholds["buy"]:
                bucket = "buy"
            elif biased_score <= thresholds["sell"]:
                bucket = "sell"
            else:
                bucket = "hold"

        action_map = {"buy": "Buy", "hold": "Hold", "sell": "Sell"}
        signal = {
            "score": biased_score,
            "action": action_map[bucket],
            "components": {
                "trend": round(trend_score, 2),
                "momentum": round(momentum_score, 2),
            },
            "notes": notes,
            "hysteresis_state": {
                "bucket": bucket,
                "thresholds": thresholds,
            },
        }
        self._cache["signal"] = signal
        return signal

    def _score_components(
        self,
        indicators: Dict[str, Any],
        patterns: Dict[str, Any],
    ) -> Tuple[float, float, List[str]]:
        notes: List[str] = []
        momentum = 0.0
        trend = 0.0

        macd_hist = indicators["macd"]["histogram"] or 0.0
        if macd_hist > 0:
            momentum += 1.8 if macd_hist > 0.5 else 1.2
            notes.append("MACD histogram positive.")
            if macd_hist > 1.0:
                momentum += 0.5
                notes.append("MACD momentum accelerating.")
        elif macd_hist < 0:
            momentum += 0.2  # retain slight momentum despite pullback
            notes.append("MACD histogram negative, momentum cooling.")
        else:
            notes.append("MACD flat.")

        rsi_value = indicators["rsi"]["value"]
        if rsi_value >= 80:
            momentum += 0.4
            notes.append("RSI overbought – watch for pullback.")
        elif rsi_value >= 68:
            momentum += 1.4
            notes.append("RSI showing strong upside momentum.")
        elif rsi_value >= 55:
            momentum += 1.0
            notes.append("RSI in bullish zone.")
        elif rsi_value >= 50:
            momentum += 0.6
            notes.append("RSI tilting bullish.")
        else:
            momentum += 0.2
            notes.append("RSI neutral.")

        price_position = indicators["bollinger"]["price_position"]
        upper_band = indicators["bollinger"]["upper"]
        lower_band = indicators["bollinger"]["lower"]
        if price_position == "upper":
            momentum += 0.9
        elif price_position == "middle":
            momentum += 0.5
        else:
            momentum += 0.2

        last_close = indicators["sma"]["last_close"]
        if upper_band and lower_band and last_close:
            band_range = upper_band - lower_band
            if band_range > 0:
                distance = upper_band - last_close
                if distance <= band_range * 0.15:
                    momentum += 0.4
                    notes.append("Price hugging upper Bollinger band.")

        sma20 = indicators["sma"]["sma20"]
        sma50 = indicators["sma"]["sma50"]
        sma200 = indicators["sma"]["sma200"]

        if sma20 and sma50 and sma20 > sma50:
            trend += 1.3
            notes.append("20-day SMA above 50-day – short-term uptrend.")
        if sma50 and sma200 and sma50 > sma200:
            trend += 1.4
            notes.append("50-day SMA above 200-day – long-term uptrend intact.")
        if last_close and sma200 and last_close > sma200:
            trend += 0.8
        if last_close and sma20 and last_close > sma20 * 1.02:
            trend += 0.5
            notes.append("Price extended above short-term average.")

        adx_value = indicators["adx"]["adx"] or 0.0
        if adx_value >= 35:
            trend += 1.6
            notes.append("ADX indicates strong trend.")
        elif adx_value >= 25:
            trend += 1.1
            notes.append("ADX confirms trend strength.")
        elif adx_value >= 20:
            trend += 0.6
        elif adx_value >= 15:
            trend += 0.3

        plus_di = indicators["adx"]["plus_di"] or 0.0
        minus_di = indicators["adx"]["minus_di"] or 0.0
        di_spread = plus_di - minus_di
        if di_spread > 10:
            trend += 0.8
            notes.append("+DI strongly leading -DI.")
        elif di_spread > 5:
            trend += 0.5
            notes.append("+DI modestly ahead of -DI.")
        elif di_spread > 0:
            trend += 0.3

        slope = patterns["trendline"]["slope"]
        if slope > 0 and last_close:
            # Normalise slope relative to price level.
            slope_strength = min(1.5, max(0.4, slope / (max(last_close, 1.0) * 0.0005)))
            trend += slope_strength
            notes.append("Upward trendline slope confirmed.")
        else:
            trend += 0.2

        supports = patterns["support_levels"]
        if supports and last_close:
            nearest_support = min(supports, key=lambda level: abs(level - last_close))
            if last_close - nearest_support <= max(1.5, last_close * 0.02):
                trend += 0.4
                notes.append("Price holding above recent support.")

        fibonacci = patterns["fibonacci"]
        fib_mid = fibonacci.get("0.5")
        if fib_mid and last_close and last_close >= fib_mid:
            trend += 0.3

        trend = min(5.0, trend)
        momentum = min(5.0, momentum)
        return momentum, trend, notes

    # ------------------------------------------------------------------ #
    # Performance Metrics

    def compute_performance_metrics(self, *, risk_free_rate: float = RISK_FREE_DEFAULT) -> Dict[str, Any]:
        if "performance" in self._cache and self._cache["performance"].get("risk_free_rate") == risk_free_rate:
            return self._cache["performance"]

        df = self._df
        returns = df["close"].pct_change().dropna()
        if returns.empty:
            metrics = {
                "risk_free_rate": risk_free_rate,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "calmar_ratio": 0.0,
                "volatility": 0.0,
                "total_return": 0.0,
                "annual_return": 0.0,
                "period_days": len(df),
            }
            self._cache["performance"] = metrics
            return metrics

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(drawdowns.min())

        avg_daily_return = returns.mean()
        volatility = returns.std(ddof=0) * math.sqrt(TRADING_DAYS_PER_YEAR)

        annual_return = (1 + avg_daily_return) ** TRADING_DAYS_PER_YEAR - 1
        excess_return = avg_daily_return - risk_free_rate / TRADING_DAYS_PER_YEAR
        sharpe = (
            (excess_return / returns.std(ddof=0)) * math.sqrt(TRADING_DAYS_PER_YEAR)
            if returns.std(ddof=0) > 0
            else 0.0
        )
        calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else float("inf")

        metrics = {
            "risk_free_rate": risk_free_rate,
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(float(sharpe), 3),
            "calmar_ratio": round(float(calmar), 3) if math.isfinite(calmar) else float("inf"),
            "volatility": round(float(volatility), 4),
            "total_return": round(float(cumulative.iloc[-1] - 1), 4),
            "annual_return": round(float(annual_return), 4),
            "period_days": int(len(df)),
        }

        self._cache["performance"] = metrics
        return metrics

    # ------------------------------------------------------------------ #
    # Chart Rendering

    def export_charts(self, ticker: str, output_dir: Path) -> Dict[str, Path]:
        chart_dir = (output_dir / "charts").resolve()
        chart_dir.mkdir(parents=True, exist_ok=True)
        png_path = chart_dir / f"{ticker.upper()}.png"
        json_path = chart_dir / f"{ticker.upper()}.json"

        df = self._df.reset_index()
        df.rename(columns={"index": "date"}, inplace=True)

        figure_payload: Dict[str, Any] = {"data": [], "layout": {}}

        if go and make_subplots:
            try:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(
                    go.Candlestick(
                        x=df["date"],
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        name="Price",
                    ),
                    row=1,
                    col=1,
                )

                indicators = self.compute_indicator_suite()
                sma = indicators["sma"]
                fig.add_trace(
                    go.Scatter(x=df["date"], y=df["close"].rolling(window=20).mean(), name="SMA 20", line=dict(width=1)),
                    row=1,
                    col=1,
                )
                if sma["sma50"]:
                    fig.add_trace(
                        go.Scatter(x=df["date"], y=df["close"].rolling(window=50).mean(), name="SMA 50", line=dict(width=1)),
                        row=1,
                        col=1,
                    )
                if sma["sma200"]:
                    fig.add_trace(
                        go.Scatter(x=df["date"], y=df["close"].rolling(window=200).mean(), name="SMA 200", line=dict(width=1)),
                        row=1,
                        col=1,
                    )

                macd = self.compute_indicator_suite()["macd"]
                macd_line = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line

                fig.add_trace(
                    go.Scatter(x=df["date"], y=macd_line, name="MACD", line=dict(color="#2962FF")),
                    row=2,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(x=df["date"], y=signal_line, name="Signal", line=dict(color="#FF6D00")),
                    row=2,
                    col=1,
                )
                fig.add_trace(
                    go.Bar(x=df["date"], y=histogram, name="Histogram", marker_color=np.where(histogram >= 0, "#00c853", "#d50000")),
                    row=2,
                    col=1,
                )

                fig.update_layout(
                    title=f"{ticker.upper()} Technical Overview",
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                )

                figure_payload = json.loads(fig.to_json())
                try:
                    fig.write_image(str(png_path), format="png", width=1280, height=720, scale=2)
                except Exception:
                    _write_placeholder_png(png_path)
            except Exception:  # pragma: no cover - fallback path
                _write_placeholder_png(png_path)
        else:
            _write_placeholder_png(png_path)

        if not json_path.exists():
            json_path.write_text(json.dumps(figure_payload, default=str), encoding="utf-8")
        else:
            json_path.write_text(json.dumps(figure_payload, default=str), encoding="utf-8")

        return {"png": png_path, "json": json_path}


__all__ = ["Epic3TechnicalAnalyzer"]
