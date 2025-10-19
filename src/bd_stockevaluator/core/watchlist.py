"""
Watchlist alert engine for Epic 6 portfolio automation.

The engine keeps configuration flexible via dot-path rule definitions while
remaining lightweight enough for deterministic unit testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, MutableMapping, Sequence


class UnsupportedOperatorError(ValueError):
    """Raised when a watchlist rule describes an unknown operator."""


@dataclass(frozen=True)
class WatchlistAlert:
    ticker: str
    triggered_rules: Sequence[str]
    channels: Sequence[str]
    payload: Mapping[str, Any]


def _resolve_path(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _evaluate_rule(value: Any, operator: str, target: Any) -> bool:
    if value is None:
        return False
    try:
        if operator == ">=":
            return value >= target
        if operator == ">":
            return value > target
        if operator == "<=":
            return value <= target
        if operator == "<":
            return value < target
        if operator == "==":
            return value == target
        if operator == "!=":
            return value != target
    except TypeError:
        return False
    raise UnsupportedOperatorError(f"Unsupported operator: {operator}")


class WatchlistAlertEngine:
    """Evaluate analysis results against configured watchlist rules."""

    def evaluate(
        self,
        watchlist: Iterable[Mapping[str, Any]],
        analysis_results: Mapping[str, Mapping[str, Any]],
    ) -> List[WatchlistAlert]:
        alerts: List[WatchlistAlert] = []
        for entry in watchlist:
            ticker = str(entry.get("ticker", "")).strip()
            if not ticker:
                continue
            data = analysis_results.get(ticker) or analysis_results.get(ticker.upper())
            if not data:
                continue
            rules = entry.get("rules") or []
            triggered: List[str] = []
            values: MutableMapping[str, Any] = {}
            for rule in rules:
                path = rule.get("path")
                operator = rule.get("operator", ">=")
                target = rule.get("value")
                if not path:
                    continue
                value = _resolve_path(data, path)
                if not _evaluate_rule(value, operator, target):
                    continue
                message = rule.get("message") or f"{path} {operator} {target}"
                triggered.append(message)
                values[path] = value

            if not triggered:
                continue

            payload = {
                "values": dict(values),
                "configured_channels": list(entry.get("channels", [])),
            }
            alerts.append(
                WatchlistAlert(
                    ticker=ticker,
                    triggered_rules=triggered,
                    channels=list(entry.get("channels", [])),
                    payload=payload,
                )
            )
        return alerts


__all__ = ["WatchlistAlert", "WatchlistAlertEngine", "UnsupportedOperatorError"]
