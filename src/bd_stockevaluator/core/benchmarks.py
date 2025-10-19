from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parents[3]
SECTOR_BENCHMARKS_PATH = BASE_DIR / "benchmarks" / "sector_medians.json"


@lru_cache()
def _load_sector_benchmarks() -> Dict[str, Any]:
    """Load sector benchmark file from disk with simple caching."""

    try:
        with SECTOR_BENCHMARKS_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(f"Invalid benchmark JSON: {SECTOR_BENCHMARKS_PATH}") from exc
    return data or {}


def reload_benchmarks() -> None:
    """Clear benchmark cache (primarily for tests)."""

    _load_sector_benchmarks.cache_clear()


def list_benchmark_sectors() -> list[str]:
    """Return sorted list of sectors available in benchmark file."""

    data = _load_sector_benchmarks()
    return sorted(key for key in data.keys() if key.lower() != "default")


def _resolve_sector_entry(sector: Optional[str]) -> Dict[str, Any]:
    data = _load_sector_benchmarks()
    if not data:
        return {}

    if sector:
        normalized = sector.strip().lower()
        for key, value in data.items():
            if key.lower() == normalized:
                return value or {}

    return data.get("default", {})


def get_benchmark_value(
    sector: Optional[str],
    category: str,
    metric: str,
    default: Optional[float] = None,
) -> Optional[float]:
    """Retrieve benchmark value for a given sector/category/metric."""

    if not category or not metric:
        return default

    entry = _resolve_sector_entry(sector)
    category_map = entry.get(category, {})
    if metric in category_map:
        return category_map[metric]

    default_map = _load_sector_benchmarks().get("default", {}).get(category, {})
    return default_map.get(metric, default)


__all__ = [
    "get_benchmark_value",
    "list_benchmark_sectors",
    "reload_benchmarks",
]
