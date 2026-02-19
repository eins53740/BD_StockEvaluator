"""
FastAPI surface for the Stock Evaluator logic.

This service will back the Android client (and other integrations) with JSON endpoints.
Run locally with:

    uvicorn bd_stockevaluator.api.main:app --reload
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..core import StockAnalysisService
from .user_features import router as user_features_router

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Z0-9.\-^]{1,12}$")

app = FastAPI(
    title="Stock Evaluator API",
    version="0.1.0",
    description="REST API exposing stock evaluation, AI opinion, and feature analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_features_router, prefix="/user", tags=["User Features"])

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
    if not _TICKER_RE.fullmatch(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol format.")
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
        logger.exception("Analysis failed for %s", ticker)
        raise HTTPException(status_code=502, detail="Analysis failed. Please try again later.") from exc

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
        logger.exception("Feature fetch failed for %s", normalised)
        raise HTTPException(status_code=502, detail="Analysis failed. Please try again later.") from exc

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
        logger.exception("Sync payload failed for %s", normalised)
        raise HTTPException(status_code=502, detail="Sync failed. Please try again later.") from exc
    return jsonable_encoder(payload)


# ---------------------------------------------------------------------------
# Mount Flask UI as a WSGI sub-application (catch-all fallback).
# This allows a single uvicorn/gunicorn process to serve both the
# FastAPI JSON API and the Flask HTML UI on the same port.
# ---------------------------------------------------------------------------
from starlette.middleware.wsgi import WSGIMiddleware  # noqa: E402

from ..app import app as _flask_app  # noqa: E402

app.mount("/", WSGIMiddleware(_flask_app))
