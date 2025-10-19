"""
Analytical helpers for advanced stock evaluation features.
"""

from importlib import import_module
from typing import Any

__all__ = [
    "Epic2Analyzer",
    "Epic3TechnicalAnalyzer",
    "MacroSnapshotBuilder",
    "MacroDataPoint",
    "MacroSeries",
    "RecessionSignalCalculator",
    "SentimentTracker",
    "ForecastAlignmentEngine",
    "MoatScorecardBuilder",
    "MoatAssessmentInput",
    "OwnershipTrendAnalyzer",
    "ManagementQualityAnalyzer",
]


def __getattr__(name: str) -> Any:
    mapping = {
        "Epic2Analyzer": (".epic2", "Epic2Analyzer"),
        "Epic3TechnicalAnalyzer": (".epic3", "Epic3TechnicalAnalyzer"),
        "MacroSnapshotBuilder": (".epic4_macro", "MacroSnapshotBuilder"),
        "MacroDataPoint": (".epic4_macro", "MacroDataPoint"),
        "MacroSeries": (".epic4_macro", "MacroSeries"),
        "RecessionSignalCalculator": (".epic4_macro", "RecessionSignalCalculator"),
        "SentimentTracker": (".epic4_macro", "SentimentTracker"),
        "ForecastAlignmentEngine": (".epic4_macro", "ForecastAlignmentEngine"),
        "MoatScorecardBuilder": (".epic5_qualitative", "MoatScorecardBuilder"),
        "MoatAssessmentInput": (".epic5_qualitative", "MoatAssessmentInput"),
        "OwnershipTrendAnalyzer": (".epic5_qualitative", "OwnershipTrendAnalyzer"),
        "ManagementQualityAnalyzer": (
            ".epic5_qualitative",
            "ManagementQualityAnalyzer",
        ),
    }
    if name in mapping:
        module_name, attr = mapping[name]
        module = import_module(module_name, package=__name__)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
