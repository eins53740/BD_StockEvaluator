# Stock Evaluator API Reference

## Overview
- **Base URL (local)**: `http://localhost:8000`
- **Run locally**: `uvicorn api.main:app --reload`
- All responses are JSON; errors use standard FastAPI problem responses.
- The API is stateless and does not require authentication yet. Production deployment should add an auth layer before exposing publicly.

## Health Check
- **Endpoint**: `GET /health`
- **Response**:
  ```json
  {
    "status": "ok",
    "timestamp": "2025-10-10T15:12:00.000123Z"
  }
  ```

## Evaluate Ticker
- **Endpoint**: `POST /evaluate`
- **Description**: Runs the full evaluation workflow (fundamental checks, flowchart, AI opinion, feature packs).
- **Request Body**:
  ```json
  {
    "ticker": "MSFT",
    "include_opinion": true
  }
  ```
- **Response** (partial):
  ```json
  {
    "ticker": "MSFT",
    "company_name": "Microsoft Corporation",
    "result": "BUY",
    "generated_at": "2025-10-10T15:12:05.331902Z",
    "metrics": {
      "rev_growth": 0.16,
      "pe": 29.1,
      "roe": 0.28,
      "margin": 0.33,
      "de": 0.46,
      "qr": 1.77
    },
    "path": [
      {"metric": "Revenue Growth (TTM)", "value": 0.16, "threshold": 0.1, "status": "PASS"},
      {"metric": "P/E Ratio", "value": 29.1, "threshold": "< 25", "status": "FAIL"},
      {"metric": "PEG Ratio", "value": 1.82, "threshold": "< 2", "status": "PASS"},
      {"metric": "Return on Equity", "value": 0.28, "threshold": 0.15, "status": "PASS"},
      ...
    ],
    "active_links": [["A", "B"], ["B", "C"], ["C", "F"], ["F", "E"], ["E", "G"], ["G", "H"], ["H", "I"], ["I", "J"]],
    "flowchart_definition": "flowchart TD\n  ...",
    "opinion_report": "<h3>Business Quality</h3> ...",
    "risk_assessment": {...},
    "trend_analysis": {...},
    "comparative_analysis": {...},
    "dividend_analysis": {...}
  }
  ```
- **Errors**:
  - `400`: missing ticker symbol.
  - `502`: upstream failure (yfinance, AI provider, etc.).

## Feature Snapshot
- **Endpoint**: `GET /features/{ticker}`
- **Description**: Returns only the enriched feature packs without flowchart/opinion overhead.
- **Response**:
  ```json
  {
    "ticker": "MSFT",
    "generated_at": "2025-10-10T15:12:05.331902Z",
    "risk_assessment": {...},
    "trend_analysis": {...},
    "comparative_analysis": {...},
    "dividend_analysis": {...}
  }
  ```

## Data Contracts
- Evaluation steps always contain `metric`, `value`, `threshold`, `status`.
- `active_links` is ordered array of `[from, to]` pairs for the flowchart.
- Timestamps use UTC ISO 8601 with `Z` suffix.

## Running Tests
- Lint and compile check: `python -m compileall FlowchartStocks/stock-evaluator`
- Planned additions (see project roadmap):
  - pytest suite covering service layer and API contract.
  - Contract tests using MockWebServer for Android client.

## Deployment Notes
- Recommended to run behind a reverse proxy with HTTPS.
- Configure environment variables for AI providers (`GROQ_API_KEY`, `GEMINI_API_KEY`) on the server.
- Add authentication (JWT or API key) before exposing beyond trusted networks.
