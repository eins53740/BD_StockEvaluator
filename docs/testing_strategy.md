# Testing Strategy Snapshot

## Current Coverage
- `python -m compileall FlowchartStocks/stock-evaluator` (syntax smoke test).
- Manual verification through Flask UI and FastAPI endpoints.
- Existing demo script (`demo.py`) provides quick sanity checks using sample tickers.

## Near-Term Additions (Sprint 1-2)
- **Unit Tests** (pytest):
  - `core.service.StockAnalysisService` happy-path and error-path cases with yfinance mocked.
  - Flowchart serialization logic (active link ordering, node states).
- **API Contract Tests**:
  - Use `httpx.AsyncClient` to hit `api.main.app` in-memory.
  - Snapshot responses for `/evaluate` and `/features/{ticker}` with mocked data providers.
- **Data Layer Mocks**:
  - Fixture to emulate yfinance responses to avoid network dependency.
  - Stub AI opinion generator to cover both success and fallback behaviours.

## Pre-Launch Validation (Sprint 5-6)
- Load testing with Locust (baseline 50 RPS sustained on `/evaluate`).
- End-to-end test matrix covering:
  - Offline cache behaviour (Room + WorkManager) on Android client.
  - Dark/light mode rendering for flowchart WebView.
- Crash monitoring enabled via Firebase Crashlytics on Android beta builds.

## Tooling & Automation
- Introduce `tox` configuration to run `pytest`, `ruff` linting, and type checks (`mypy`) once refactor stabilises.
- Add GitHub Actions workflow:
  - Backend: format, lint, pytest, docker build.
  - Android: gradle lint, unit tests, instrumentation tests (Firebase Test Lab).

## Reporting
- Store aggregated test reports under `docs/test-reports/` per sprint.
- Track coverage improvements in weekly status updates (see project plan).
