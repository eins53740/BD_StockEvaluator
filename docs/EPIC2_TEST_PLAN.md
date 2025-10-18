# Epic 2 – Test Checklist

Use this checklist before opening a pull request that touches the Epic 2 analytics.

## 1. Live Smoke Run

```bash
cd FlowchartStocks/stock-evaluator
python scripts/smoke_live.py --include-opinion AAPL MSFT
```

*Requires*: valid `API_KEY_FMP`, `API_KEY_FINNHUB`, and `API_KEY_ALPHAVANTAGE` (plus optional Groq/Gemini keys) defined in `.env`. The script prints the verdict, composite scores, and intrinsic value estimates so you can spot obvious regressions.

## 2. Automated Tests

```bash
cd FlowchartStocks/stock-evaluator
pytest tests/test_epic2_analyzer.py
pytest tests/test_service.py
```

The first test covers the valuation/profitability/growth engines, while the service test ensures Epic 2 payloads flow through to the Flask layer.

## 3. Background Scheduler (Optional)

If `ENABLE_BACKGROUND_REFRESH=true` in `.env`, start the Flask app and confirm that the log reports background refresh activity for the tickers in `REFRESH_TICKERS`. Disable the flag if you do not need the scheduler during development.
