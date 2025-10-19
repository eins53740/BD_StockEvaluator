from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _env_key_candidates(key_name: str) -> list[str]:
    """Derive possible environment variable names for a configured API key."""
    if not key_name:
        return []

    candidates = {key_name.strip().upper()}

    if key_name.startswith("api_key_"):
        suffix = key_name[len("api_key_") :].strip()
        if suffix:
            upper_suffix = suffix.upper()
            candidates.update(
                {
                    upper_suffix,
                    f"{upper_suffix}_API_KEY",
                    f"API_KEY_{upper_suffix}",
                }
            )

    return [name for name in candidates if name]


def get_api_key(key_name: str) -> Optional[str]:
    """Read API keys from environment variables or repo config fallback."""

    for env_key in _env_key_candidates(key_name):
        env_value = os.getenv(env_key)
        if env_value:
            return env_value.strip()

    config_path = Path(__file__).resolve().parents[2] / "config" / "api_keys.txt"
    try:
        for raw in config_path.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            sep = " = " if " = " in line else ("=" if "=" in line else None)
            if not sep:
                continue
            key, value = line.split(sep, 1)
            if key.strip() == key_name:
                return value.strip().strip('"')
    except FileNotFoundError:
        logger.debug("Config file not found at %s", config_path)
    except Exception as exc:
        logger.warning("Could not read API key file %s: %s", config_path, exc)
    return None


__all__ = ["get_api_key"]
