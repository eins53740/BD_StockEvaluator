from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env", override=False)
sys.path.insert(0, str(BASE_DIR))

from core import StockAnalysisService  # noqa: E402  pylint: disable=wrong-import-position


def summarise_analysis(payload: dict) -> dict:
    valuation = payload.get("valuation_scorecard") or {}
    profitability = payload.get("profitability_snapshot") or {}
    growth = payload.get("growth_trends") or {}
    intrinsic = (payload.get("intrinsic_value_models") or {}).get("models", {})

    return {
        "ticker": payload.get("ticker"),
        "result": payload.get("result"),
        "valuation_score": valuation.get("overall_score"),
        "profitability_score": profitability.get("overall_score"),
        "growth_score": growth.get("overall_score"),
        "dcf_value": intrinsic.get("dcf", {}).get("value"),
        "ben_graham": intrinsic.get("ben_graham", {}).get("value"),
        "ddm": intrinsic.get("ddm", {}).get("value"),
    }


def run_smoke_test(tickers: Iterable[str], include_opinion: bool) -> List[dict]:
    service = StockAnalysisService()
    results: List[dict] = []
    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue
        print(f"Analyzing {ticker} …", flush=True)
        analysis = service.analyze(ticker, include_opinion=include_opinion)
        summary = summarise_analysis(analysis)
        results.append(summary)
        print(json.dumps(summary, indent=2))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a live smoke test against the BD_Finance evaluation stack.",
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Ticker symbols to evaluate (default: value in SMOKE_TICKERS env or AAPL,MSFT,TSLA).",
    )
    parser.add_argument(
        "--include-opinion",
        action="store_true",
        help="Include LLM opinion generation (uses Groq/Gemini keys).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = args.tickers or os.environ.get("SMOKE_TICKERS", "AAPL,MSFT,TSLA").split(",")
    run_smoke_test(tickers, include_opinion=args.include_opinion)


if __name__ == "__main__":
    main()
