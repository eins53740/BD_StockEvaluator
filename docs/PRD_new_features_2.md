# BD_Finance Stock Analysis Platform - PRD (Version 2)

**Author:** Bruno Dias (BD)
**Scope:** BD_Finance_android v2 feature roadmap (additions layered on top of the existing APK without removing current functionality).

---

## Product Vision
Deliver a comprehensive, data-driven investment assistant that blends quantitative analysis, qualitative assessment, macro context, and automation across desktop and Android surfaces. Version 2 expands the present APK by widening data sources, deepening analytics, and enriching AI guidance while keeping today’s workflow intact.

---

## Core Philosophy
1. Quality at a discount - continue highlighting fundamentally strong companies trading below intrinsic value.
2. Holistic evaluation - extend beyond fundamentals to cover technicals, macro indicators, and qualitative moats.
3. Automation first - streamline collection, scoring, and reporting so investors focus on decisions, not data wrangling.
4. Transparent metrics - every score, alert, and AI insight must show its underlying data trail.

---

## Epic Overview (New in v2)
> Existing v1 capabilities (ticker intake, evaluation engine, Mermaid flow, LLM second opinion) must remain untouched. New features should integrate with, not replace, the current codebase.

### Epic 1 - Multi-Source Data Collection & Normalisation\n_Status: Completed in BD_Finance_py_v2 (multi-provider pipeline, SQLite normalisation, scheduler hooks implemented)_
**Goal:** Enrich the Android client's data via a unifying service that consolidates Yahoo, Alpha Vantage, Finnhub/FMP, and optional CSV imports.
- [x] F1.1 Data Connectors - Add modular adapters with secure API key management.
- [x] F1.2 Normalisation Layer - Standardise ratios (EPS, PE, PEG, EV/EBIT, P/B, FCF yield) into a shared schema stored in SQLite/on-device cache. Use tables: `fundamentals_snapshot`, `fundamentals_history`, `prices_daily`, `providers_meta`. Persist original currency; normalise to EUR and USD.
- [x] F1.3 Scheduler Hooks - Support automated refresh jobs (WorkManager on Android; optional cron for desktop backend) feeding the APK through a sync API.
  - Provider precedence: Prices → yfinance → FMP → Alpha Vantage; Fundamentals → FMP → Finnhub → Alpha Vantage → yfinance; Dividends → yfinance → FMP; Sector/industry → FMP → yfinance.

### Epic 2 - Fundamental Analysis Extensions
_Status: Completed in BD_Finance_py_v2 (advanced analytics surfaced in the Flask web app)_
**Goal:** Expand valuation, profitability, and growth scoring while keeping the existing verdict logic.
- [x] F2.1 Enhanced Valuation Scoring - Weighted scores comparing ratios to sector medians and 10-year averages.
- [x] F2.2 Profitability & Stability - Add ROE, ROA, margin consistency, leverage metrics.
- [x] F2.3 Growth Trends - Render 5Y/10Y CAGR for revenue, EPS, FCF with acceleration/decay indicators.
- [x] F2.4 Intrinsic Value Models - Implement DCF, Ben Graham, and DDM calculators surfaced alongside the current decision verdict. Defaults: DCF 5Y horizon, terminal growth 2.0%, discount 10% (+/- 2 pp by risk bucket), FCF growth capped at 15%, safety margin 25%. Graham: EPS x (8.5 + 2g) with g capped at 15%, AAA yield 4%. DDM only if payout_ratio < 0.8; dividend CAGR cap 8%, r = 9-10%.
- [x] F2.5 Historical Context - Show deviations from historical averages (e.g., current P/E vs decade mean).

### Epic 3 - Technical & Momentum Toolkit
**Goal:** Provide entry/exit timing insight to complement fundamentals.
- [x] F3.1 Indicator Suite - Compute MACD(12,26,9), RSI(14), ADX(14), Bollinger(20,2), SMA(20/50/200) with Compose/Flask chart tabs.
- [x] F3.2 Pattern Detection - Identify support/resistance, Fibonacci levels, trendlines.
- [x] F3.3 Signal Generator - Combine technical signals with the verdict to produce Buy/Hold/Sell cues. Scoring: Trend (0-5) + Momentum (0-5) → 0-10; 0-3 Sell, 4-6 Hold, 7-10 Buy (with hysteresis).
- [x] F3.4 Performance Metrics - Add drawdown, Sharpe, and Calmar ratios per ticker.
  - Flask charting: Plotly-generated PNGs under `static/charts/<ticker>.png` for fast loads; retain JSON for interactive drilldown.

### Epic 4 - Macro & Market Context
**Goal:** Incorporate macro indicators into decision-making.
- [x] F4.1 Macro Dashboard - Pull GDP growth, CPI, unemployment, Fed funds rate, 10Y-2Y spread (provider: FRED via `fredapi`; CSV fallback offline).
- [x] F4.2 Recession Signals - Track Sahm Rule, yield curve inversion, Buffett indicator with alert badges.
- [x] F4.3 Sentiment Tracking - Monitor global valuations and institutional flows.
- [x] F4.4 Forecast Alignment - Correlate macro shifts (rates, EPS trends) with target tickers.
  - Refresh cadence: daily (yields/spreads), monthly (CPI/unemployment/LEI), quarterly (GDP). Store raw in `macro_series`, derive `macro_snapshot` for UI and email.

### Epic 5 - Qualitative & Moat Evaluation
**Goal:** Layer qualitative moat scoring into reports.
- [x] F5.1 Moat Framework - Score switching costs, network effects, intangible assets, cost advantage, efficient scale (manual inputs plus AI summaries).
- [x] F5.2 Ownership Trends - Display institutional and insider ownership charts (Alpha Vantage/FMP).
- [x] F5.3 Management Quality - Extract KPIs from 10-Ks/annual letters via text mining.

### Epic 6 - Portfolio & Reporting Automation
**Goal:** Move beyond single-ticker analysis.
- [x] F6.1 Holdings Import - Accept CSV/Excel holdings, calculate sector exposure and position weights.
- [x] F6.2 Performance Analytics - Compute CAGR, alpha vs S&P500, beta-adjusted returns.
- [x] F6.3 Automated Reports - Generate daily PDFs/emails summarising portfolio changes, valuation alerts, macro context.
- [x] F6.4 Watchlist Alerts - Notify when fundamentals or technicals hit custom thresholds.

### Epic 7 - UX & Platform Integration
**Goal:** Deliver a cohesive cross-platform experience.
- [x] F7.1 Desktop Overview - Streamlit dashboard combining fundamentals, technicals, macro (first iteration). Flask single-ticker route remains.
- [x] F7.2 Per-Ticker Report - Printable one-page analysis integrating new metrics and the existing Mermaid flow.
- [x] F7.3 Chart Explorer - Interactive ratio history and TA charts.
- [x] F7.4 Sync Layer - Share SQLite/REST payloads so desktop and Android remain aligned.
  - [x] Printable reports: HTML→PDF via WeasyPrint (fallback `pdfkit`), embedding Plotly static charts and intrinsic value summary.

### Epic 8 - AI & Automation Layer (v2 Enhancements)
**Goal:** Upgrade AI capabilities beyond the current second opinion.
- F8.1 Financial Summary Agent - Use Groq/Gemini to summarise the expanded metrics with a 1-10 rating rationale.
- F8.2 Market Commentary Bot - Generate daily/weekly macro and sentiment summaries.
- F8.3 Natural-Language Screener - Handle queries like "find cheap tech stocks with ROE > 15% and low debt."
- F8.4 Optional Predictive Models - Integrate ML for sentiment scoring or short-term momentum forecasts.

### Epic 9 - Architecture & Infrastructure
**Goal:** Keep the platform modular and maintainable.
- F9.1 Core Python Modules - `bd_finance_core` (analysis engine) and `bd_finance_report` (outputs) reusable by desktop and Android backends.
- F9.2 Storage Options - SQLite for local, optional PostgreSQL/cloud sync.
- F9.3 API Gateway - Unified access to external providers with rate-limit handling.
- F9.4 Deployment Tooling - PyInstaller/CI scripts for packaging dashboards and services.

### Epic 10 - Foreigner stocks and UI - UX improvement
**Goal:** Extend ticker range tfrom usa to world. Improve UX.
 - F10.1 Multi-exchange equity support: Implement full international ticker handling using yfinance suffixes (e.g., TSCO.L, B3SA3.SA, DAI.DE, 7203.T) mapped to canonical exchange, country, and currency, storing these fields in persistence and exposing them via API. Fetch quotes and historical OHLC in native currency, then normalise to EUR and USD using a single timestamped FX snapshot per response for consistency (apply conversions before computing returns to keep % moves identical across currencies). Use a provider chain where Yahoo Finance is primary and FMP is an automatic fallback; surface data_provider and provider_fallback=true when triggered, with structured logging for fallbacks and FX snapshot IDs. Ensure exchange-timezone correctness for market open/close and include both asof_utc and asof_exchange_tz. Deliver a suffix→metadata registry, backfill missing metadata on first read of stored tickers, and add tests for ticker parsing, FX maths, provider failover, and snapshot equivalence of returns; update docs (supported suffixes, fields, flags) and dashboards for error/fallback rates.
 - F10.2 Flowchart text visibility (2-line labels & legibility): Add an automatic label-wrapping routine that measures text and splits at word boundaries into at most two lines, applying an ellipsis on the second line when overflow occurs. Vertically centre text within the shape, increase node height responsively to avoid clipping, and enforce minimum dimensions and padding so two lines remain readable at 75–150% zoom. Use theme-aware colours with a WCAG contrast ratio ≥ 4.5:1, consistent font size/line-height, and render via SVG <tspan> offsets or canvas equivalents. Provide a hover tooltip (and aria-label/title) that reveals the full, untruncated label for accessibility; include keyboard focus styles. Add visual regression tests for short/long labels, light/dark themes, and zoom scales, plus snapshot tests for the wrapping algorithm’s boundary cases.
 
 - F10.3 Evaluate and optimize the decision flow thresholds.


### Epic 11 - Contaierisation
**Goal:** Use the package in a containerised environment.
 - F11.1 Containerise Python package & local test (real/mocked Docker): Produce a production-ready multi-stage Dockerfile (Python 3.12-slim, pinned dependencies, non-root user, healthcheck) and optional docker-compose.yml for one-command local bring-up. The container must start via python -m app, expose and probe a /health endpoint, and build cleanly with docker build -t app:local .. Introduce DOCKER_RUNTIME=real|mock to switch between the Docker SDK and a lightweight fake client, allowing CI to run fast without host Docker while retaining an opt-in job that exercises a real engine (e.g., nightly). Provide pytest examples that parametrise both modes, guard real-Docker tests behind DOCKER_AVAILABLE=1, and document local commands for build/run. Ensure CI uses mock by default, publishes an image on main, and includes README updates on build, run, environment variables, and test strategy.

---

## Tech Stack Summary
| Layer          | Technologies                                                   |
|---------------|----------------------------------------------------------------|
| Backend        | Python (pandas, numpy, SQLAlchemy, yfinance, FMP, Alpha Vantage) |
| Automation     | Cron/WorkManager, SMTP, PyInstaller                            |
| AI Integration | Groq LLaMA 3, Gemini 1.5, OpenAI-compatible APIs               |
| Storage        | SQLite (device), CSV, optional PostgreSQL                      |
| Frontend       | Android (Kotlin/Compose), Streamlit/React dashboard            |

---

## Success Metrics (v2 Targets)
- >= 95% automated daily refresh success rate.
- Portfolio + intrinsic value computation < 10 seconds per run.
- 100% coverage of primary valuation and technical metrics for tracked tickers.
- AI rating alignment with deterministic scoring >= 80%.
- Positive user feedback on expanded insights and transparency.

---

## Decisions Finalised (v2)
- Normalised schema and provider precedence (Epic 1) locked as above.
- Intrinsic models defaults (Epic 2): DCF 5Y, 2% terminal, 10% discount ±2 pp by risk, 25% safety margin; Graham capped; DDM gated by payout and conservative caps.
- Technical aggregation (Epic 3): 0–10 trend+momentum; Plotly charts rendered to PNG in Flask.
- Macro (Epic 4): FRED provider, series list and cadence defined; `macro_series` and `macro_snapshot` tables.
- UX/Reports (Epic 7): Streamlit chosen; HTML→PDF one-pagers with embedded charts.

A versao 2 da BD_Finance evolui a aplicacao com conectores multi-fontes, analises fundamentais, tecnicas e macroeconomicas mais profundas, avaliacao qualitativa de vantagens competitivas, relatorios automatizados e integracao de IA mais robusta. Mantemos a filosofia de "qualidade a bom preco", garantindo transparencia e automacao, enquanto sincronizamos dashboards desktop e app Android.


