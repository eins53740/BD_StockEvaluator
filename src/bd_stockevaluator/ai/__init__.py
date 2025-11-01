"""
AI & Automation Layer (Epic 8).

This module provides advanced AI-powered features including:
- Financial Summary Agent with 1-10 ratings
- Market Commentary Bot
- Natural-Language Screener
- Optional Predictive Models
"""

from .agents import FinancialSummaryAgent, MarketCommentaryBot
from .screener import NaturalLanguageScreener

__all__ = [
    "FinancialSummaryAgent",
    "MarketCommentaryBot",
    "NaturalLanguageScreener",
]
