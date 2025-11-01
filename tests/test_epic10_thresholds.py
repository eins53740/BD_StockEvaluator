from __future__ import annotations

import json

from bd_stockevaluator.core.service import StockAnalysisService


def test_load_thresholds(tmp_path):
    thresholds = {
        "rev_growth": 0.20,
        "pe": 20,
        "peg": 1.5,
        "roe": 0.20,
        "margin": 0.15,
        "de": 0.5,
        "qr": 2.0,
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    thresholds_path = config_dir / "thresholds.json"
    with open(thresholds_path, "w") as f:
        json.dump(thresholds, f)

    # Temporarily point the PROJECT_ROOT to the temp path
    import bd_stockevaluator.core.service as service

    original_project_root = service.PROJECT_ROOT
    service.PROJECT_ROOT = tmp_path

    try:
        service = StockAnalysisService()
        assert service.thresholds == thresholds
    finally:
        # Restore the original PROJECT_ROOT
        service.PROJECT_ROOT = original_project_root
