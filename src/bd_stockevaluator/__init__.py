"""
Public package interface for the Stock Evaluator project.

This module re-exports the primary entry points that external callers expect
while keeping the internal package layout flexible.
"""

from .core import (
    StockAnalysisService,
    generate_stock_opinion,
    generate_flowchart_definition,
    get_stock_data,
    refresh_macro_snapshot,
    get_macro_context,
)

__all__ = [
    "StockAnalysisService",
    "generate_stock_opinion",
    "generate_flowchart_definition",
    "get_stock_data",
    "refresh_macro_snapshot",
    "get_macro_context",
]
