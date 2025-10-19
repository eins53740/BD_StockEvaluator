from __future__ import annotations

import os
import types

from bd_stockevaluator.cli import daily_report_cli
from bd_stockevaluator.utils import api_keys_reader as api_keys_reader_module


def test_daily_report_cli_main_sets_utf8(monkeypatch):
    called = {}

    dummy_module = types.SimpleNamespace(main=lambda: called.setdefault("main", True))
    monkeypatch.setattr(
        daily_report_cli, "_load_daily_report_module", lambda: dummy_module
    )

    daily_report_cli.main()

    assert called.get("main") is True
    assert os.environ.get("PYTHONIOENCODING") == "utf-8"


def test_api_keys_reader_parses_basic_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config" / "api_keys.txt"
    config_path.parent.mkdir()
    config_path.write_text(
        "# Comment line\napi_key_demo = value123\nmissing =\n",
        encoding="utf-8",
    )

    keys = api_keys_reader_module.api_keys_reader(str(config_path))

    assert keys["api_key_demo"] == "value123"
    assert "missing" in keys
    assert keys["missing"] == ""
