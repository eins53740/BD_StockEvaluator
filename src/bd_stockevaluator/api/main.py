"""
FastAPI surface for the Stock Evaluator logic.

This service will back the Android client (and other integrations) with JSON endpoints.
Run locally with:

    uvicorn bd_stockevaluator.api.main:app --reload
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..core import StockAnalysisService, get_macro_context
from ..ai import FinancialSummaryAgent, MarketCommentaryBot, NaturalLanguageScreener
from .middleware import RateLimitMiddleware, RequestLoggingMiddleware

app = FastAPI(
    title="Stock Evaluator API",
    version="0.2.0",
    description="REST API exposing stock evaluation, AI agents, and advanced features.",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware (Epic 9 F9.3)
# Configure rate limit via environment variable (default: 60 requests/minute)
import os
rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)

# Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

analysis_service = StockAnalysisService()


class EvaluateRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol to evaluate.")
    include_opinion: bool = Field(
        True, description="If true, generates an AI opinion report (slower)."
    )


class EvaluationStep(BaseModel):
    metric: str
    value: Any
    threshold: Any
    status: str


class EvaluationResponse(BaseModel):
    ticker: str
    company_name: str
    result: str
    generated_at: str
    metrics: Dict[str, Any]
    flowchart_definition: str
    opinion_report: Any
    path: List[EvaluationStep]
    active_links: List[List[str]]
    risk_assessment: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    comparative_analysis: Dict[str, Any]
    dividend_analysis: Dict[str, Any]
    qualitative_moat: Dict[str, Any] | None = None
    ownership_trends: Dict[str, Any] | None = None
    management_quality: Dict[str, Any] | None = None


class FeatureResponse(BaseModel):
    ticker: str
    generated_at: str
    risk_assessment: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    comparative_analysis: Dict[str, Any]
    dividend_analysis: Dict[str, Any]


class SyncResponse(BaseModel):
    ticker: str
    version: str
    data_providers: Dict[str, Any]
    fundamentals: Dict[str, Any]
    price_history: List[Dict[str, Any]]
    technical_chart: Dict[str, Any]
    macro_snapshot: Dict[str, Any]


def _normalise_ticker(raw: str) -> str:
    ticker = (raw or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker symbol is required.")
    return ticker


def _serialize_path(path: List[Any]) -> List[EvaluationStep]:
    steps = []
    for metric, value, threshold, status in path:
        steps.append(
            EvaluationStep(
                metric=metric,
                value=value,
                threshold=threshold,
                status=status,
            )
        )
    return steps


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest) -> Dict[str, Any]:
    ticker = _normalise_ticker(request.ticker)
    try:
        analysis = analysis_service.analyze(
            ticker, include_opinion=request.include_opinion
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    path = _serialize_path(analysis.get("path", []))
    payload = {
        **analysis,
        "ticker": ticker,
        "path": path,
    }
    return jsonable_encoder(payload)


@app.get("/features/{ticker}", response_model=FeatureResponse)
def get_features(ticker: str) -> Dict[str, Any]:
    normalised = _normalise_ticker(ticker)
    try:
        analysis = analysis_service.analyze(normalised, include_opinion=False)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    subset = {
        "ticker": normalised,
        "generated_at": analysis["generated_at"],
        "risk_assessment": analysis["risk_assessment"],
        "trend_analysis": analysis["trend_analysis"],
        "comparative_analysis": analysis["comparative_analysis"],
        "dividend_analysis": analysis["dividend_analysis"],
    }
    return jsonable_encoder(subset)


@app.get("/sync/{ticker}", response_model=SyncResponse)
def get_sync_payload(ticker: str) -> Dict[str, Any]:
    normalised = _normalise_ticker(ticker)
    try:
        payload = analysis_service.build_sync_payload(normalised)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return jsonable_encoder(payload)


# ============================================================================
# Epic 8: AI & Automation Layer Endpoints
# ============================================================================

# Instantiate AI agents
financial_agent = FinancialSummaryAgent()
commentary_bot = MarketCommentaryBot()
nl_screener = NaturalLanguageScreener()


class FinancialRatingResponse(BaseModel):
    """Response model for financial rating."""

    ticker: str
    company_name: str
    overall_score: float
    buy_rating: float
    quality_rating: float
    value_rating: float
    growth_rating: float
    financial_health_rating: float
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    confidence: str
    rationale: str
    generated_at: str


class MarketCommentaryResponse(BaseModel):
    """Response model for market commentary."""

    title: str
    summary: str
    macro_outlook: str
    sentiment: str
    key_risks: List[str]
    opportunities: List[str]
    generated_at: str


class ScreenerQueryRequest(BaseModel):
    """Request model for natural language screener."""

    query: str = Field(..., description="Natural language screening query")
    tickers: List[str] = Field(
        default=[],
        description="List of tickers to screen (empty = use all available)",
    )


class ScreenerResponse(BaseModel):
    """Response model for screener results."""

    query: str
    criteria: Dict[str, Any]
    matches: List[Dict[str, Any]]
    total_matches: int


@app.post("/ai/rating/{ticker}", response_model=FinancialRatingResponse)
def get_financial_rating(ticker: str) -> Dict[str, Any]:
    """
    F8.1: Generate AI-powered financial rating with 1-10 scores.

    Returns structured rating including:
    - Overall score (1-10)
    - Individual ratings (buy, quality, value, growth, financial health)
    - Strengths and weaknesses
    - Recommendation and confidence level
    """
    normalised = _normalise_ticker(ticker)

    try:
        # Get full analysis
        analysis = analysis_service.analyze(normalised, include_opinion=False)
        company_name = analysis.get("company_name", normalised)

        # Generate rating
        rating = financial_agent.generate_rating(normalised, company_name, analysis)

        if not rating:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate rating. AI service may be unavailable.",
            )

        response = {
            "ticker": normalised,
            "company_name": company_name,
            "overall_score": rating.overall_score,
            "buy_rating": rating.buy_rating,
            "quality_rating": rating.quality_rating,
            "value_rating": rating.value_rating,
            "growth_rating": rating.growth_rating,
            "financial_health_rating": rating.financial_health_rating,
            "summary": rating.summary,
            "strengths": rating.strengths,
            "weaknesses": rating.weaknesses,
            "recommendation": rating.recommendation,
            "confidence": rating.confidence,
            "rationale": rating.rationale,
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/ai/market-commentary", response_model=MarketCommentaryResponse)
def get_market_commentary(period: str = "daily") -> Dict[str, Any]:
    """
    F8.2: Generate AI-powered market commentary.

    Args:
        period: "daily" or "weekly"

    Returns market analysis including:
    - Macro outlook
    - Sentiment assessment
    - Key risks and opportunities
    """
    if period not in ["daily", "weekly"]:
        raise HTTPException(
            status_code=400, detail="Period must be 'daily' or 'weekly'"
        )

    try:
        # Get macro context
        macro_context = get_macro_context()

        # Generate commentary
        commentary = commentary_bot.generate_commentary(macro_context, period)

        if not commentary:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate commentary. AI service may be unavailable.",
            )

        response = {
            "title": commentary.title,
            "summary": commentary.summary,
            "macro_outlook": commentary.macro_outlook,
            "sentiment": commentary.sentiment,
            "key_risks": commentary.key_risks,
            "opportunities": commentary.opportunities,
            "generated_at": commentary.generated_at,
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/ai/screen", response_model=ScreenerResponse)
def screen_stocks(request: ScreenerQueryRequest) -> Dict[str, Any]:
    """
    F8.3: Natural language stock screener.

    Examples:
    - "find cheap tech stocks with ROE > 15% and low debt"
    - "show me large-cap healthcare companies with high dividends"
    - "quality growth stocks under $50"

    Args:
        query: Natural language screening query
        tickers: Optional list of tickers to screen (if empty, provide universe)

    Returns:
        - Parsed criteria
        - Matching stocks with scores
    """
    try:
        # Parse natural language query
        criteria = nl_screener.parse_query(request.query)

        if not criteria:
            raise HTTPException(
                status_code=400,
                detail="Failed to parse query. Please rephrase your screening criteria.",
            )

        # Build stock universe
        stock_universe = []
        if request.tickers:
            for ticker in request.tickers[:50]:  # Limit to 50 tickers max
                try:
                    analysis = analysis_service.analyze(ticker, include_opinion=False)
                    stock_universe.append(analysis)
                except Exception:
                    continue  # Skip failed analyses

        # Screen stocks
        matches = nl_screener.screen_stocks(criteria, stock_universe)

        # Build response
        criteria_dict = {
            "sectors": criteria.sectors,
            "min_roe": criteria.min_roe,
            "max_pe": criteria.max_pe,
            "min_revenue_growth": criteria.min_revenue_growth,
            "max_debt_to_equity": criteria.max_debt_to_equity,
            "min_market_cap": criteria.min_market_cap,
            "max_market_cap": criteria.max_market_cap,
            "min_dividend_yield": criteria.min_dividend_yield,
            "valuation": criteria.valuation,
            "growth_profile": criteria.growth_profile,
            "quality": criteria.quality,
        }

        # Simplify matches for response
        simplified_matches = [
            {
                "ticker": m.get("ticker"),
                "company_name": m.get("company_name"),
                "result": m.get("result"),
                "risk_score": m.get("risk_assessment", {}).get("risk_score"),
                "valuation_assessment": m.get("comparative_analysis", {}).get(
                    "valuation_assessment"
                ),
                "growth_profile": m.get("comparative_analysis", {}).get(
                    "growth_profile"
                ),
            }
            for m in matches
        ]

        response = {
            "query": request.query,
            "criteria": criteria_dict,
            "matches": simplified_matches,
            "total_matches": len(simplified_matches),
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
