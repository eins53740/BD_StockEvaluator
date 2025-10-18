"""
Command-line wrapper for the legacy daily report workflow.

The original BD_Finance repository exposed a ``daily_report_cli.py`` entry
point.  During the repository split the file was dropped which breaks the
automated tests that still exercise the CLI contract.  This lightweight module
restores the behaviour: ensure UTF-8 output and delegate to the modernised
report module.
"""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType


def _load_daily_report_module() -> ModuleType:
    """Import and return the daily report workflow module."""

    return import_module("bd_stockevaluator.reports.daily_report")


def main() -> None:
    """Invoke the daily report entry point with UTF-8 stdout/stderr."""

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    module = _load_daily_report_module()
    if hasattr(module, "main") and callable(module.main):
        module.main()
    elif hasattr(module, "daily_report") and callable(module.daily_report):
        module.daily_report()


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    main()
