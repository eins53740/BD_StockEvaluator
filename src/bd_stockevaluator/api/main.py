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

from ..core import StockAnalysisService

app = FastAPI(
    title="Stock Evaluator API",
    version="0.1.0",
    description="REST API exposing stock evaluation, AI opinion, and feature analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class FeatureResponse(BaseModel):
    ticker: str
    generated_at: str
    risk_assessment: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    comparative_analysis: Dict[str, Any]
    dividend_analysis: Dict[str, Any]


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
        analysis = analysis_service.analyze(ticker, include_opinion=request.include_opinion)
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
