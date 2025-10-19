"""
Performance analytics helpers for Epic 6 portfolio automation.

The functions exposed here operate on pre-aggregated portfolio valuations and
benchmark series, keeping the implementation deterministic so unit tests can
exercise the full calculation stack without network access.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PerformanceMetrics:
    """Container for the primary performance outputs."""

    cagr: float
    benchmark_cagr: float
    alpha: float
    beta: float
    beta_adjusted_return: float
    volatility: float
    tracking_error: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "cagr": self.cagr,
            "benchmark_cagr": self.benchmark_cagr,
            "alpha": self.alpha,
            "beta": self.beta,
            "beta_adjusted_return": self.beta_adjusted_return,
            "volatility": self.volatility,
            "tracking_error": self.tracking_error,
        }


def _prepare_series(series: pd.Series) -> pd.Series:
    cleaned = series.dropna().sort_index()
    if cleaned.empty:
        raise ValueError("Time series must contain at least one data point.")
    if not isinstance(cleaned.index, pd.DatetimeIndex):
        raise TypeError("Time series index must be a DatetimeIndex.")
    return cleaned.astype(float)


def _annualisation_factor(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 1.0
    total_days = (index[-1] - index[0]).days
    if total_days <= 0:
        return 1.0
    years = total_days / 365.0
    return years if years > 0 else 1.0


def compute_cagr(series: pd.Series) -> float:
    ordered = series.sort_index()
    start, end = float(ordered.iloc[0]), float(ordered.iloc[-1])
    factor_years = _annualisation_factor(ordered.index)
    if start <= 0:
        raise ValueError("CAGR requires strictly positive starting value.")
    if factor_years == 0:
        return (end / start) - 1.0
    return (end / start) ** (1.0 / factor_years) - 1.0


def compute_performance_metrics(
    portfolio_series: pd.Series,
    benchmark_series: Optional[pd.Series] = None,
) -> Dict[str, float]:
    """
    Compute annualised performance metrics relative to an optional benchmark.

    Parameters
    ----------
    portfolio_series:
        Series of portfolio valuations indexed by ``DatetimeIndex``.
    benchmark_series:
        Matching benchmark valuations. When omitted, benchmark metrics default
        to zero.
    """

    portfolio = _prepare_series(portfolio_series)
    if benchmark_series is not None:
        benchmark = _prepare_series(benchmark_series)
        joined = pd.concat(
            [portfolio, benchmark.rename("benchmark")], axis=1, join="inner"
        ).dropna()
        portfolio = joined.iloc[:, 0]
        benchmark = joined.iloc[:, 1]
    else:
        benchmark = None

    cagr = compute_cagr(portfolio)
    benchmark_cagr = compute_cagr(benchmark) if benchmark is not None else 0.0

    returns_portfolio = portfolio.pct_change().dropna()
    if benchmark is not None:
        returns_benchmark = benchmark.pct_change().dropna()
        shared_index = returns_portfolio.index.intersection(returns_benchmark.index)
        returns_portfolio = returns_portfolio.reindex(shared_index)
        returns_benchmark = returns_benchmark.reindex(shared_index)
    else:
        returns_benchmark = None

    volatility = (
        float(returns_portfolio.std(ddof=0) * math.sqrt(252))
        if not returns_portfolio.empty
        else 0.0
    )
    if returns_benchmark is None or returns_benchmark.empty:
        beta = 0.0
        tracking_error = 0.0
        alpha = cagr - benchmark_cagr
        beta_adjusted = cagr
    else:
        cov = float(np.cov(returns_portfolio, returns_benchmark, ddof=0)[0, 1])
        var = float(np.var(returns_benchmark, ddof=0))
        beta = cov / var if var > 0 else 0.0
        tracking_series = returns_portfolio - returns_benchmark
        tracking_error = float(tracking_series.std(ddof=0) * math.sqrt(252))
        alpha = cagr - benchmark_cagr
        beta_adjusted = cagr - beta * benchmark_cagr

    metrics = PerformanceMetrics(
        cagr=cagr,
        benchmark_cagr=benchmark_cagr,
        alpha=alpha,
        beta=beta,
        beta_adjusted_return=beta_adjusted,
        volatility=volatility,
        tracking_error=tracking_error,
    )
    return metrics.as_dict()


__all__ = [
    "PerformanceMetrics",
    "compute_performance_metrics",
    "compute_cagr",
]
