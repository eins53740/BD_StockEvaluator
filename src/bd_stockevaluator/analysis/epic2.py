from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..core.benchmarks import get_benchmark_value


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_period_year(entry: Dict[str, Any]) -> Optional[int]:
    period = entry.get("period") or entry.get("date") or entry.get("as_of")
    if period is None:
        return None
    if isinstance(period, int):
        return period
    if isinstance(period, float):
        return int(period)
    if isinstance(period, str):
        digits = "".join(ch for ch in period if ch.isdigit())
        if len(digits) >= 4:
            try:
                return int(digits[:4])
            except ValueError:
                return None
    return None


def _relative_score(
    value: Optional[float],
    benchmark: Optional[float],
    *,
    higher_is_better: bool,
) -> Optional[float]:
    """Return a 0-100 score assessing value versus benchmark."""

    value = _safe_float(value)
    benchmark = _safe_float(benchmark)
    if value is None or benchmark is None or benchmark == 0:
        return None

    if higher_is_better:
        if value <= 0:
            return None
        ratio = value / benchmark
    else:
        if value <= 0:
            return None
        ratio = benchmark / value

    score = ratio * 100
    # Clamp to reasonable bounds so extreme values do not dominate.
    score = max(0.0, min(score, 120.0))
    # Normalise to 0-100 scale.
    return round(min(score, 100.0), 2)


def _blend_scores(
    scores: Iterable[Optional[float]],
    weights: Iterable[float],
) -> Optional[float]:
    weighted_pairs = [
        (score, weight)
        for score, weight in zip(scores, weights)
        if score is not None and weight > 0
    ]
    if not weighted_pairs:
        return None
    numerator = sum(score * weight for score, weight in weighted_pairs)
    denominator = sum(weight for _, weight in weighted_pairs)
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)


def _average(values: Sequence[float]) -> Optional[float]:
    cleaned = [val for val in values if val is not None]
    if not cleaned:
        return None
    return sum(cleaned) / len(cleaned)


def _stddev(values: Sequence[float]) -> Optional[float]:
    cleaned = [val for val in values if val is not None]
    if len(cleaned) < 2:
        return None
    mean_value = sum(cleaned) / len(cleaned)
    variance = sum((val - mean_value) ** 2 for val in cleaned) / (len(cleaned) - 1)
    return math.sqrt(variance)


@dataclass
class GrowthFigure:
    cagr_5y: Optional[float]
    cagr_10y: Optional[float]
    sector_5y: Optional[float]
    sector_10y: Optional[float]

    @property
    def acceleration(self) -> Optional[str]:
        if self.cagr_5y is None or self.cagr_10y is None:
            return None
        delta = self.cagr_5y - self.cagr_10y
        if delta > 0.01:
            return "accelerating"
        if delta < -0.01:
            return "decelerating"
        return "stable"


class Epic2Analyzer:
    """Run Epic 2 analytics (valuation, profitability, growth, intrinsic value)."""

    def __init__(
        self,
        stock_info: Dict[str, Any],
        history: Optional[Sequence[Dict[str, Any]]] = None,
        *,
        sector: Optional[str] = None,
    ) -> None:
        self.stock_info = stock_info or {}
        self.history = list(history or stock_info.get("historicalMetrics") or [])
        self.sector = sector or stock_info.get("sector")
        self.price = _safe_float(
            stock_info.get("regularMarketPrice")
            or stock_info.get("regularMarketPriceUSD")
        )
        self._series_cache: Dict[Tuple[str, ...], List[Tuple[int, float]]] = {}

    # ------------------------------------------------------------------ #
    # Public API

    def analyze(self) -> Dict[str, Any]:
        growth = self._growth_trends()
        valuation = self._valuation_scorecard()
        profitability = self._profitability_and_stability()
        intrinsic = self._intrinsic_values(growth)
        historical = self._historical_context()

        return {
            "valuation": valuation,
            "profitability": profitability,
            "growth": growth,
            "intrinsic_values": intrinsic,
            "historical_context": historical,
        }

    # ------------------------------------------------------------------ #
    # Helpers

    def _history_series(self, *keys: str) -> List[Tuple[int, float]]:
        cache_key = tuple(keys)
        if cache_key in self._series_cache:
            return self._series_cache[cache_key]

        series: List[Tuple[int, float]] = []
        for entry in self.history:
            year = _parse_period_year(entry)
            if year is None:
                continue
            value = None
            for key in keys:
                if key in entry and entry[key] is not None:
                    value = _safe_float(entry[key])
                    break
            if value is not None:
                series.append((year, value))

        series.sort(key=lambda item: item[0])
        self._series_cache[cache_key] = series
        return series

    def _history_average(self, keys: Sequence[str], window: int = 10) -> Optional[float]:
        series = self._history_series(*keys)
        if not series:
            return None
        if window:
            series = series[-window:]
        values = [value for _, value in series if value is not None]
        return _average(values)

    def _history_stddev(self, keys: Sequence[str], window: int = 10) -> Optional[float]:
        series = self._history_series(*keys)
        if not series:
            return None
        if window:
            series = series[-window:]
        values = [value for _, value in series if value is not None]
        return _stddev(values)

    def _compute_cagr(self, keys: Sequence[str], horizon: int) -> Optional[float]:
        if horizon <= 0:
            return None
        series = self._history_series(*keys)
        if len(series) < 2:
            return None
        latest_year, latest_value = series[-1]
        if latest_value is None or latest_value <= 0:
            return None

        candidate = None
        for year, value in series:
            if value is None or value <= 0:
                continue
            diff = latest_year - year
            if diff >= horizon:
                if candidate is None or diff < candidate[0]:
                    candidate = (diff, year, value)

        if candidate is None:
            return None

        years, start_year, start_value = candidate
        if years <= 0 or start_value <= 0:
            return None

        cagr = (latest_value / start_value) ** (1 / years) - 1
        return cagr

    # ------------------------------------------------------------------ #
    # Valuation

    def _valuation_scorecard(self) -> Dict[str, Any]:
        metrics = {
            "pe": {
                "current": self.stock_info.get("trailingPE") or self.stock_info.get("pe"),
                "benchmark_key": ("valuation", "pe"),
                "history_keys": ("pe", "trailingPE"),
                "higher_is_better": False,
            },
            "peg": {
                "current": self.stock_info.get("pegRatio"),
                "benchmark_key": ("valuation", "peg"),
                "history_keys": ("peg",),
                "higher_is_better": False,
            },
            "pb": {
                "current": self.stock_info.get("priceToBook"),
                "benchmark_key": ("valuation", "pb"),
                "history_keys": ("pb", "price_to_book"),
                "higher_is_better": False,
            },
            "ev_to_ebit": {
                "current": self.stock_info.get("evToEbit"),
                "benchmark_key": ("valuation", "ev_to_ebit"),
                "history_keys": ("ev_to_ebit", "evToEbit"),
                "higher_is_better": False,
            },
            "fcf_yield": {
                "current": self.stock_info.get("fcfYield"),
                "benchmark_key": ("valuation", "fcf_yield"),
                "history_keys": ("fcf_yield", "fcfYield"),
                "higher_is_better": True,
            },
        }

        breakdown: Dict[str, Any] = {}
        scores: List[float] = []

        for key, meta in metrics.items():
            section, metric_key = meta["benchmark_key"]
            sector_benchmark = get_benchmark_value(self.sector, section, metric_key)
            history_average = self._history_average(meta["history_keys"], window=10)

            sector_score = _relative_score(
                meta["current"],
                sector_benchmark,
                higher_is_better=meta["higher_is_better"],
            )
            history_score = _relative_score(
                meta["current"],
                history_average,
                higher_is_better=meta["higher_is_better"],
            )
            blended_score = _blend_scores(
                (sector_score, history_score),
                (0.6, 0.4),
            )
            if blended_score is not None:
                scores.append(blended_score)

            breakdown[key] = {
                "value": _safe_float(meta["current"]),
                "sector_benchmark": sector_benchmark,
                "ten_year_average": history_average,
                "sector_score": sector_score,
                "history_score": history_score,
                "score": blended_score,
            }

        overall_score = round(sum(scores) / len(scores), 2) if scores else None

        return {
            "overall_score": overall_score,
            "metrics": breakdown,
        }

    # ------------------------------------------------------------------ #
    # Profitability & Stability

    def _profitability_and_stability(self) -> Dict[str, Any]:
        metrics = {
            "roe": {
                "current": self.stock_info.get("returnOnEquity") or self.stock_info.get("returnOnEquityTTM"),
                "benchmark_key": ("profitability", "roe"),
                "history_keys": ("roe", "returnOnEquity"),
                "higher_is_better": True,
            },
            "roa": {
                "current": self.stock_info.get("returnOnAssets"),
                "benchmark_key": ("profitability", "roa"),
                "history_keys": ("roa", "returnOnAssets"),
                "higher_is_better": True,
            },
            "net_margin": {
                "current": self.stock_info.get("profitMargins"),
                "benchmark_key": ("profitability", "margin"),
                "history_keys": ("profit_margins", "profitMargins"),
                "higher_is_better": True,
            },
            "operating_margin": {
                "current": self.stock_info.get("operatingMargins") or self.stock_info.get("operatingMargin"),
                "benchmark_key": ("profitability", "operating_margin"),
                "history_keys": ("operating_margin", "operatingMargins"),
                "higher_is_better": True,
            },
            "debt_to_equity": {
                "current": self.stock_info.get("debtToEquity"),
                "benchmark_key": ("profitability", "debt_to_equity"),
                "history_keys": ("debt_to_equity", "debtToEquity"),
                "higher_is_better": False,
            },
        }

        breakdown: Dict[str, Any] = {}
        scores: List[float] = []

        for key, meta in metrics.items():
            section, metric_key = meta["benchmark_key"]
            benchmark = get_benchmark_value(self.sector, section, metric_key)
            history_average = self._history_average(meta["history_keys"], window=8)
            history_stability = self._history_stddev(meta["history_keys"], window=8)

            sector_score = _relative_score(
                meta["current"],
                benchmark,
                higher_is_better=meta["higher_is_better"],
            )
            history_score = _relative_score(
                meta["current"],
                history_average,
                higher_is_better=meta["higher_is_better"],
            )
            blended = _blend_scores((sector_score, history_score), (0.7, 0.3))
            if blended is not None:
                scores.append(blended)

            breakdown[key] = {
                "value": _safe_float(meta["current"]),
                "sector_benchmark": benchmark,
                "history_average": history_average,
                "stability": history_stability,
                "sector_score": sector_score,
                "history_score": history_score,
                "score": blended,
            }

        overall = round(sum(scores) / len(scores), 2) if scores else None
        stability_label = None
        if overall is not None:
            if overall >= 80:
                stability_label = "Excellent"
            elif overall >= 60:
                stability_label = "Solid"
            elif overall >= 40:
                stability_label = "Moderate"
            else:
                stability_label = "Weak"

        return {
            "overall_score": overall,
            "stability_label": stability_label,
            "metrics": breakdown,
        }

    # ------------------------------------------------------------------ #
    # Growth Trends

    def _growth_trends(self) -> Dict[str, Any]:
        growth_metrics = {
            "revenue": {
                "history_keys": ("revenue", "totalRevenue", "revenueTTM"),
                "benchmark_keys": ("growth", "revenue_cagr"),
            },
            "eps": {
                "history_keys": ("eps", "epsDiluted"),
                "benchmark_keys": ("growth", "eps_cagr"),
            },
            "fcf": {
                "history_keys": ("free_cash_flow", "freeCashFlow"),
                "benchmark_keys": ("growth", "fcf_cagr"),
            },
        }

        total_scores: List[float] = []
        metric_output: Dict[str, Any] = {}

        for name, meta in growth_metrics.items():
            cagr_5 = self._compute_cagr(meta["history_keys"], horizon=5)
            cagr_10 = self._compute_cagr(meta["history_keys"], horizon=10)
            sector_5 = get_benchmark_value(self.sector, meta["benchmark_keys"][0], f"{meta['benchmark_keys'][1]}_5y")
            sector_10 = get_benchmark_value(self.sector, meta["benchmark_keys"][0], f"{meta['benchmark_keys'][1]}_10y")

            figure = GrowthFigure(
                cagr_5y=cagr_5,
                cagr_10y=cagr_10,
                sector_5y=sector_5,
                sector_10y=sector_10,
            )

            score_components = []
            if cagr_5 is not None and sector_5 is not None:
                score_components.append(
                    _relative_score(cagr_5, sector_5, higher_is_better=True)
                )
            if cagr_10 is not None and sector_10 is not None:
                score_components.append(
                    _relative_score(cagr_10, sector_10, higher_is_better=True)
                )
            score_components = [score for score in score_components if score is not None]
            blended = round(sum(score_components) / len(score_components), 2) if score_components else None
            if blended is not None:
                total_scores.append(blended)

            metric_output[name] = {
                "cagr_5y": cagr_5,
                "cagr_10y": cagr_10,
                "sector_5y": sector_5,
                "sector_10y": sector_10,
                "acceleration": figure.acceleration,
                "score": blended,
            }

        overall = round(sum(total_scores) / len(total_scores), 2) if total_scores else None

        return {
            "overall_score": overall,
            "metrics": metric_output,
        }

    # ------------------------------------------------------------------ #
    # Intrinsic Value Models

    def _intrinsic_values(self, growth_output: Dict[str, Any]) -> Dict[str, Any]:
        eps = _safe_float(self.stock_info.get("eps"))
        dividend_yield = _safe_float(self.stock_info.get("dividendYield"))
        payout_ratio = _safe_float(self.stock_info.get("payoutRatio"))
        fcf_yield = _safe_float(
            self.stock_info.get("fcfYield")
            or self.stock_info.get("freeCashFlowYield")
        )

        price = self.price or 0.0
        models: Dict[str, Any] = {}

        # DCF model
        if price and fcf_yield and fcf_yield > 0:
            fcf_per_share = price * fcf_yield
            fcf_growth = None
            fc_metric = growth_output.get("metrics", {}).get("fcf", {})
            if fc_metric:
                fcf_growth = fc_metric.get("cagr_5y") or fc_metric.get("cagr_10y")
            if fcf_growth is None:
                fcf_growth = 0.05
            growth_rate = min(max(fcf_growth, -0.05), 0.15)
            discount_rate = 0.10
            terminal_growth = 0.02
            years = 5
            discounted_sum = 0.0
            for year in range(1, years + 1):
                projected = fcf_per_share * (1 + growth_rate) ** year
                discounted = projected / ((1 + discount_rate) ** year)
                discounted_sum += discounted
            terminal_base = fcf_per_share * (1 + growth_rate) ** years
            terminal_value = (
                terminal_base * (1 + terminal_growth) / (discount_rate - terminal_growth)
            )
            terminal_discounted = terminal_value / ((1 + discount_rate) ** years)
            intrinsic_value = discounted_sum + terminal_discounted
            margin_of_safety_price = intrinsic_value * 0.75  # 25% safety margin
            models["dcf"] = {
                "value": round(intrinsic_value, 2),
                "margin_of_safety_price": round(margin_of_safety_price, 2),
                "upside": round(intrinsic_value / price - 1, 2) if price else None,
                "assumptions": {
                    "fcf_per_share": round(fcf_per_share, 2),
                    "growth_rate": round(growth_rate, 4),
                    "discount_rate": discount_rate,
                    "terminal_growth": terminal_growth,
                },
            }

        # Ben Graham formula
        if eps and eps > 0:
            eps_growth = None
            eps_metric = growth_output.get("metrics", {}).get("eps", {})
            if eps_metric:
                eps_growth = eps_metric.get("cagr_5y") or eps_metric.get("cagr_10y")
            if eps_growth is None:
                eps_growth = 0.05
            g_percent = max(0.0, min(eps_growth * 100, 15.0))
            aaa_yield = 4.0  # percent
            graham_value = eps * (8.5 + 2 * g_percent) * 4.4 / aaa_yield
            models["ben_graham"] = {
                "value": round(graham_value, 2),
                "margin_of_safety_price": round(graham_value * 0.75, 2),
                "upside": round(graham_value / price - 1, 2) if price else None,
                "assumptions": {
                    "eps": round(eps, 2),
                    "growth_percent": round(g_percent, 2),
                    "aaa_yield_percent": aaa_yield,
                },
            }

        # Dividend Discount Model
        if (
            price
            and dividend_yield
            and dividend_yield > 0
            and (payout_ratio is None or payout_ratio < 0.8)
        ):
            dividend_per_share = price * dividend_yield
            div_growth = None
            revenue_metric = growth_output.get("metrics", {}).get("revenue", {})
            if revenue_metric:
                div_growth = revenue_metric.get("cagr_5y")
            if div_growth is None:
                div_growth = 0.03
            div_growth = min(div_growth, 0.08)
            discount_rate = 0.095
            if discount_rate > div_growth:
                ddm_value = dividend_per_share * (1 + div_growth) / (discount_rate - div_growth)
                models["ddm"] = {
                    "value": round(ddm_value, 2),
                    "margin_of_safety_price": round(ddm_value * 0.75, 2),
                    "upside": round(ddm_value / price - 1, 2) if price else None,
                    "assumptions": {
                        "dividend_per_share": round(dividend_per_share, 2),
                        "growth_rate": round(div_growth, 4),
                        "discount_rate": discount_rate,
                    },
                }

        return {
            "price": price,
            "models": models,
        }

    # ------------------------------------------------------------------ #
    # Historical Context

    def _historical_context(self) -> Dict[str, Any]:
        metrics = {
            "pe": {
                "current": self.stock_info.get("trailingPE"),
                "history_keys": ("pe", "trailingPE"),
                "higher_is_better": False,
            },
            "fcf_yield": {
                "current": self.stock_info.get("fcfYield"),
                "history_keys": ("fcf_yield", "fcfYield"),
                "higher_is_better": True,
            },
            "profit_margin": {
                "current": self.stock_info.get("profitMargins"),
                "history_keys": ("profit_margins", "profitMargins"),
                "higher_is_better": True,
            },
            "roe": {
                "current": self.stock_info.get("returnOnEquity"),
                "history_keys": ("roe", "returnOnEquity"),
                "higher_is_better": True,
            },
            "debt_to_equity": {
                "current": self.stock_info.get("debtToEquity"),
                "history_keys": ("debt_to_equity", "debtToEquity"),
                "higher_is_better": False,
            },
        }

        context: Dict[str, Any] = {}

        for key, meta in metrics.items():
            average = self._history_average(meta["history_keys"], window=10)
            current_value = _safe_float(meta["current"])
            if current_value is None or average is None or average == 0:
                delta_pct = None
            else:
                delta_pct = (current_value - average) / average

            favourable = None
            if delta_pct is not None:
                if meta["higher_is_better"]:
                    favourable = delta_pct >= 0
                else:
                    favourable = delta_pct <= 0

            context[key] = {
                "current": current_value,
                "ten_year_average": average,
                "delta_pct": delta_pct,
                "favourable": favourable,
            }

        return context


__all__ = ["Epic2Analyzer"]
