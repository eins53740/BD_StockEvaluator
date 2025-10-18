"""
Core services for Stock Evaluator logic shared between web and mobile backends.
"""

from .service import (
    StockAnalysisService,
    generate_stock_opinion,
    generate_flowchart_definition,
    get_stock_data,
    refresh_macro_snapshot,
    get_macro_context,
)
from .keys import get_api_key
from .data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
    SchedulerHooks,
    SQLiteDataStore,
)
from .macro import MacroContextService

__all__ = [
    "StockAnalysisService",
    "generate_stock_opinion",
    "generate_flowchart_definition",
    "get_stock_data",
    "refresh_macro_snapshot",
    "get_macro_context",
    "get_api_key",
    "CurrencyConverter",
    "MultiSourceDataClient",
    "SchedulerHooks",
    "SQLiteDataStore",
    "MacroContextService",
]
