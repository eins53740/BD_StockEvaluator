# Stock Investment Decision Platform - Epics & Tasks

**Project:** Stock Investment Decision Platform (Web UI)
**Based on:** PRD v3.0
**Created:** 2025-10-31
**Status:** Planning Phase

---

## Epic Overview

| Epic ID | Epic Name | Priority | Phase | Effort (SP) | Status |
|---------|-----------|----------|-------|-------------|--------|
| **E1** | Core Evaluation Engine | P0 | Phase 1 | 34 | Not Started |
| **E2** | Interactive Mermaid Flowcharts | P0 | Phase 1 | 21 | Not Started |
| **E3** | LLM Integration & AI Analysis | P0 | Phase 1 | 13 | Not Started |
| **E4** | Web UI Foundation | P0 | Phase 1 | 21 | Not Started |
| **E5** | Intrinsic Valuation Models | P0 | Phase 1 | 13 | Not Started |
| **E6** | Risk Assessment System | P0 | Phase 1 | 13 | Not Started |
| **E7** | Multi-Source Data Pipeline | P0 | Phase 1 | 21 | Not Started |
| **E8** | Technical Analysis Suite | P1 | Phase 2 | 21 | Not Started |
| **E9** | Macro Context Dashboard | P1 | Phase 2 | 13 | Not Started |
| **E10** | Comparative Analysis | P1 | Phase 2 | 13 | Not Started |
| **E11** | Dividend Analysis | P2 | Phase 2 | 8 | Not Started |
| **E12** | User Experience Enhancements | P1 | Phase 2 | 21 | Not Started |
| **E13** | Watchlist & Alerts | P1 | Phase 3 | 21 | Not Started |
| **E14** | Portfolio Tracking | P1 | Phase 3 | 21 | Not Started |
| **E15** | User Authentication & Accounts | P1 | Phase 3 | 13 | Not Started |
| **E16** | Export & Reporting | P1 | Phase 2 | 13 | Not Started |
| **E17** | Deployment & Infrastructure | P0 | Phase 1 | 21 | Not Started |
| **E18** | Testing & Quality Assurance | P0 | All Phases | 34 | Not Started |

**Total Story Points:** 331
**Estimated Timeline:** 12 months (3-person team)

---

## PHASE 1: MVP - Core Evaluation (Months 1-2)

### Epic 1: Core Evaluation Engine (P0 - Must Have)
**Goal:** Implement the 6-stage fundamental analysis decision tree
**Story Points:** 34
**Dependencies:** None

#### Tasks:

**E1-T1: Define Threshold Configuration System** [3 SP]
- Create `thresholds.py` configuration module
- Define THRESHOLDS dictionary with all 7 metrics
- Implement threshold profiles (Conservative, Moderate, Aggressive)
- Add validation for threshold ranges
- Create unit tests for threshold validation
- **Acceptance:** Can load and validate different threshold profiles

**E1-T2: Build Stock Data Extractor** [5 SP]
- Create `data_extractor.py` module
- Implement yfinance integration for basic stock info
- Extract 7 core metrics: rev_growth, PE, ROE, margin, D/E, quick_ratio
- Handle missing/null data gracefully
- Add caching for API responses (4-hour TTL)
- Create mock data fixtures for testing
- **Acceptance:** Can fetch and normalize metrics for any valid ticker

**E1-T3: Implement 6-Stage Evaluation Logic** [8 SP]
- Enhance `evaluator.py` with full decision tree
- Stage 1: Revenue Growth Check (≥10%)
- Stage 2A: P/E Ratio Check (<25)
- Stage 2B: PEG Ratio Fallback (<2.0)
- Stage 3: ROE Check (≥15%)
- Stage 4: Net Margin Check (≥10%)
- Stage 5: Debt/Equity Check (<1.0)
- Stage 6: Quick Ratio Check (≥1.5)
- Generate evaluation path with pass/fail status for each stage
- **Acceptance:** Returns correct verdict for test cases

**E1-T4: Build Verdict Logic** [3 SP]
- Implement verdict determination based on evaluation path
- Return "BUY" if all 6 stages pass
- Return "BUY with CAUTION" if stages 1-5 pass, stage 6 fails
- Return "DO NOT BUY" with specific reason if any stage 1-5 fails
- Include justification text for each verdict
- **Acceptance:** Verdict matches expected outcome for 20 test stocks

**E1-T5: Create Active Path Tracking** [3 SP]
- Track decision path through flowchart (node connections)
- Generate `active_links` array for visualization
- Mark passed nodes vs failed nodes
- Handle fallback path (P/E fail → PEG check)
- **Acceptance:** Active links correctly represent evaluation path

**E1-T6: Implement Close Call Detection** [2 SP]
- Add 10% tolerance for near-miss thresholds
- Mark metrics within tolerance as "CLOSE_CALL"
- Include close call status in evaluation results
- Add visual indicators for marginal metrics
- **Acceptance:** Close calls detected and flagged correctly

**E1-T7: Add Extended Metrics Collection** [5 SP]
- Collect profitability metrics: ROA, ROIC, Operating Margin, Gross Margin
- Collect growth metrics: 5Y Revenue/EPS/FCF CAGR
- Collect valuation metrics: P/B, EV/EBITDA, EV/Sales, FCF Yield
- Collect balance sheet metrics: Current Ratio, Interest Coverage
- Collect shareholder metrics: Dividend Yield, Payout Ratio, Buyback Yield
- Store in extended metrics dictionary
- **Acceptance:** 20+ metrics collected and normalized

**E1-T8: Create Evaluation Service Layer** [5 SP]
- Build `StockAnalysisService` in `core/service.py`
- Orchestrate data fetch → evaluation → feature enrichment
- Handle errors gracefully with fallback responses
- Add logging for debugging
- Implement response caching (TTL: 4 hours)
- **Acceptance:** Service returns complete evaluation payload

---

### Epic 2: Interactive Mermaid Flowcharts (P0 - Must Have)
**Goal:** Generate and render animated decision tree flowcharts
**Story Points:** 21
**Dependencies:** E1 (Evaluation Engine)

#### Tasks:

**E2-T1: Design Flowchart Mermaid Template** [3 SP]
- Create base Mermaid flowchart syntax with all nodes
- Define node IDs: Start, A-F, B2, DNB1-DNB5, CAUTION, BUY
- Add decision diamond nodes
- Define edge connections for all paths
- Add styling classes (passNode, failNode, cautionNode, neutralNode)
- **Acceptance:** Static Mermaid diagram renders correctly

**E2-T2: Build Dynamic Flowchart Generator** [5 SP]
- Create `flowchart_generator.py` module
- Accept evaluation results and generate Mermaid syntax
- Inject actual metric values into node labels
- Apply styling based on pass/fail status
- Handle active path highlighting
- Support variable text wrapping (2-line max)
- **Acceptance:** Generated Mermaid matches evaluation path

**E2-T3: Implement Node Status Coloring** [3 SP]
- Apply green fill to passed nodes
- Apply red fill to failed nodes
- Apply yellow fill to close call nodes
- Apply blue fill to neutral/unevaluated nodes
- Apply bold borders to active path
- Ensure WCAG contrast ratio ≥4.5:1
- **Acceptance:** Colors match status in light/dark mode

**E2-T4: Add Interactive Hover Tooltips** [5 SP]
- Generate tooltip data for each node
- Include: metric name, actual value, threshold, pass/fail, definition
- Add industry benchmark and historical avg in tooltip
- Implement JavaScript tooltip rendering (Tippy.js or native)
- Add keyboard accessibility (focus states)
- **Acceptance:** Tooltips display on hover/focus with full info

**E2-T5: Implement Sequential Animation** [3 SP]
- Add CSS/JS animation for sequential node reveal
- 300ms delay between node appearances
- Fade-in + scale animation
- Highlight active path edges with animation
- Add animation controls (play, pause, reset)
- **Acceptance:** Flowchart animates in evaluation order

**E2-T6: Add Zoom & Export Controls** [2 SP]
- Implement zoom in/out buttons (+/-)
- Add pinch-to-zoom for touch devices
- Add "Download SVG" button
- Add "Download PNG" button (1920x1080)
- Add "Share Link" button (copy to clipboard)
- **Acceptance:** Can zoom and export flowchart

---

### Epic 3: LLM Integration & AI Analysis (P0 - Must Have)
**Goal:** Generate AI-powered investment summaries
**Story Points:** 13
**Dependencies:** E1 (Evaluation Engine)

#### Tasks:

**E3-T1: Set Up LLM Provider Clients** [3 SP]
- Integrate Groq API client (LLaMA 3.3 70B)
- Integrate Google Gemini 1.5 Pro client
- Add API key management (environment variables)
- Implement provider fallback logic (Groq → Gemini → None)
- Add rate limiting (10 requests/min)
- **Acceptance:** Can call both LLM APIs successfully

**E3-T2: Design Structured Prompt Template** [3 SP]
- Create prompt template with placeholders
- Include: ticker, company name, sector, industry
- Include: financial metrics (revenue, P/E, ROE, margin, debt, liquidity)
- Include: intrinsic value estimates
- Include: technical indicators summary
- Include: moat assessment and risk factors
- Define output format requirements (200-300 words, structured)
- **Acceptance:** Prompt generates consistent, high-quality responses

**E3-T3: Implement LLM Opinion Generator** [4 SP]
- Create `llm_opinion.py` module
- Build prompt from evaluation results
- Call LLM API with structured prompt
- Parse response and extract conviction score (1-10)
- Convert markdown to HTML
- Add color coding for conviction score (1-3 red, 4-7 yellow, 8-10 green)
- **Acceptance:** Returns formatted HTML opinion with conviction score

**E3-T4: Add Fallback Rules-Based Summary** [2 SP]
- Create fallback summary generator (no LLM required)
- Generate template-based summary using metrics
- Include verdict justification
- List key strengths and risks
- Match LLM output format
- **Acceptance:** Fallback summary displays if LLM fails

**E3-T5: Implement Error Handling & Retry Logic** [1 SP]
- Add exponential backoff for API failures (3 retries)
- Handle timeout errors (30s timeout)
- Handle rate limit errors (wait and retry)
- Log errors for monitoring
- Return fallback summary on permanent failure
- **Acceptance:** No user-facing errors; always returns summary

---

### Epic 4: Web UI Foundation (P0 - Must Have)
**Goal:** Build responsive HTML/CSS/JS frontend
**Story Points:** 21
**Dependencies:** E1, E2, E3 (Backend ready)

#### Tasks:

**E4-T1: Set Up Frontend Stack** [2 SP]
- Choose CSS framework (Tailwind CSS)
- Choose JS framework (Alpine.js or HTMX)
- Set up build pipeline (optional: Vite)
- Configure asset bundling
- Set up hot-reload for development
- **Acceptance:** Development environment ready

**E4-T2: Design Landing Page Layout** [3 SP]
- Create HTML structure: header, hero, search, footer
- Add logo and branding
- Implement large search bar with auto-focus
- Add "Recent Tickers" section below search
- Add "How It Works" explainer section
- Ensure responsive breakpoints (desktop, tablet, mobile)
- **Acceptance:** Landing page renders on all devices

**E4-T3: Build Search Input Component** [3 SP]
- Create search input with autocomplete
- Implement debounced API calls (300ms delay)
- Display ticker + company name in dropdown
- Handle keyboard navigation (up/down arrows, enter)
- Show loading spinner while searching
- Display "No results found" message
- **Acceptance:** Can search and select tickers

**E4-T4: Create Results Page Layout** [5 SP]
- Design results page structure (see PRD section 6.1)
- Add verdict badge section (large, colored)
- Add price + change ticker
- Add AI summary section
- Add flowchart container (full-width)
- Add key metrics dashboard (6-tile grid)
- Add tabbed sections for details (Technical, Comparative, Macro)
- Add action buttons (Export PDF, Add to Watchlist)
- **Acceptance:** Results page displays all sections

**E4-T5: Implement Loading States** [2 SP]
- Create skeleton screens for each section
- Add progress bar with stages (Fetching → Analyzing → Generating)
- Add estimated time remaining
- Implement smooth transitions (fade-in)
- **Acceptance:** Loading states display during analysis

**E4-T6: Add Error Handling UI** [2 SP]
- Create error message component
- Handle "Ticker not found" errors with suggestions
- Handle API failure errors with retry button
- Handle timeout errors with clear messaging
- Add "Contact Support" link for persistent issues
- **Acceptance:** Errors display friendly messages

**E4-T7: Implement Dark Mode** [2 SP]
- Add dark mode toggle in header
- Define CSS variables for light/dark themes
- Update all components to use CSS variables
- Save preference to localStorage
- Ensure flowchart colors work in both modes
- **Acceptance:** Dark mode toggles without page reload

**E4-T8: Add Responsive Design** [2 SP]
- Define breakpoints: mobile (375px), tablet (768px), desktop (1920px)
- Implement mobile-first CSS
- Adjust flowchart size for mobile (scrollable)
- Stack metric tiles vertically on mobile
- Test on multiple devices/browsers
- **Acceptance:** Works on iPhone, iPad, desktop Chrome/Firefox/Safari

---

### Epic 5: Intrinsic Valuation Models (P0 - Must Have)
**Goal:** Calculate DCF, Graham, and DDM valuations
**Story Points:** 13
**Dependencies:** E1 (Core metrics available)

#### Tasks:

**E5-T1: Implement DCF Model** [5 SP]
- Create `valuation/dcf.py` module
- Fetch historical free cash flow (5 years)
- Project FCF growth (capped at 15% annually)
- Calculate terminal value (2% perpetual growth)
- Apply discount rate (10% ± 2% by risk tier)
- Calculate present value of cash flows
- Apply 25% safety margin
- Return: fair_value, safe_entry_price, margin_of_safety
- **Acceptance:** DCF values match manual calculations

**E5-T2: Implement Benjamin Graham Formula** [3 SP]
- Create `valuation/graham.py` module
- Formula: Intrinsic Value = EPS × (8.5 + 2g)
- Fetch EPS (TTM)
- Calculate growth rate (g) from historical EPS (cap at 15%)
- Use AAA corporate bond yield (default 4%)
- Calculate margin of safety vs current price
- **Acceptance:** Graham values reasonable for test cases

**E5-T3: Implement Dividend Discount Model (DDM)** [3 SP]
- Create `valuation/ddm.py` module
- Check if payout ratio < 80% (required for DDM)
- Fetch dividend history (5 years)
- Calculate dividend CAGR (cap at 8%)
- Apply required return (r = 9-10%)
- Calculate Gordon Growth Model value
- Return value or null with reason
- **Acceptance:** DDM returns value only for dividend stocks

**E5-T4: Create Valuation Dashboard Component** [2 SP]
- Display 3 valuation models side-by-side
- Show current price vs fair value for each model
- Show margin of safety percentage (color-coded)
- Add bar chart comparing valuations
- Add tooltip explaining each model
- Highlight "consensus" if 2+ models agree
- **Acceptance:** Valuation dashboard renders with all models

---

### Epic 6: Risk Assessment System (P0 - Must Have)
**Goal:** Calculate composite risk score (0-100)
**Story Points:** 13
**Dependencies:** E1 (Extended metrics available)

#### Tasks:

**E6-T1: Implement Risk Factor Calculators** [5 SP]
- Create `risk/assessment.py` module
- Calculate Valuation Risk (20% weight): P/E vs sector, historical avg
- Calculate Leverage Risk (20% weight): D/E + interest coverage
- Calculate Profitability Risk (15% weight): ROE trend, margin consistency
- Calculate Liquidity Risk (15% weight): Quick ratio + OCF/Debt
- Calculate Growth Risk (15% weight): Revenue CAGR volatility
- Calculate Market Risk (10% weight): Beta, correlation to SPY
- Calculate Size Risk (5% weight): Market cap category
- **Acceptance:** Each factor returns 0-100 score

**E6-T2: Build Composite Risk Score** [2 SP]
- Aggregate 7 risk factors with weights
- Calculate overall risk score (0-100)
- Determine risk level: Low (0-25), Moderate (26-50), High (51-75), Very High (76-100)
- Generate risk level badge with color
- **Acceptance:** Composite score matches manual calculation

**E6-T3: Generate Risk Recommendations** [3 SP]
- Create recommendation engine based on risk factors
- Generate 3-5 actionable recommendations
- Example: "Monitor valuation - P/E in 73rd percentile"
- Example: "Strong balance sheet provides downside protection"
- Prioritize recommendations by impact
- **Acceptance:** Recommendations relevant to risk factors

**E6-T4: Create Risk Dashboard Visualization** [3 SP]
- Build radar chart for 7 risk dimensions
- Add risk score gauge (0-100 with color zones)
- Display risk level badge prominently
- Add expandable sections for each risk factor
- Add historical risk trend chart (if re-analyzed)
- **Acceptance:** Risk dashboard renders with chart

---

### Epic 7: Multi-Source Data Pipeline (P0 - Must Have)
**Goal:** Implement redundant data fetching with caching
**Story Points:** 21
**Dependencies:** None

#### Tasks:

**E7-T1: Set Up SQLite Database** [3 SP]
- Create database schema in `data/stocks.db`
- Tables: fundamentals_snapshot, prices_daily, macro_series, providers_meta
- Add indexes for ticker and timestamp
- Implement connection pooling
- Add migration scripts
- **Acceptance:** Database created with all tables

**E7-T2: Implement Data Store Layer** [3 SP]
- Create `core/data_store.py` with SQLiteDataStore class
- Methods: save_fundamentals(), get_fundamentals(), save_prices(), get_prices()
- Add TTL checking (4 hours for prices, 24 hours for fundamentals)
- Handle concurrent access safely
- **Acceptance:** Can read/write from database

**E7-T3: Integrate yfinance Provider** [3 SP]
- Create `providers/yfinance_provider.py`
- Fetch ticker info (all metrics)
- Fetch historical prices (OHLCV)
- Handle errors gracefully (ticker not found, API timeout)
- Normalize to standard schema
- **Acceptance:** Can fetch data from yfinance

**E7-T4: Integrate FMP Provider** [3 SP]
- Create `providers/fmp_provider.py`
- Require API key (stored in environment variables)
- Fetch fundamentals (income statement, balance sheet, cash flow)
- Fetch real-time quote
- Normalize to standard schema
- **Acceptance:** Can fetch data from FMP

**E7-T5: Integrate Alpha Vantage Provider** [2 SP]
- Create `providers/alphavantage_provider.py`
- Require API key
- Fetch fundamentals (annual/quarterly reports)
- Handle rate limits (5 calls/min)
- Normalize to standard schema
- **Acceptance:** Can fetch data from Alpha Vantage

**E7-T6: Build Multi-Source Data Client** [4 SP]
- Create `core/data_pipeline.py` with MultiSourceDataClient
- Implement provider prioritization:
  - Prices: yfinance → FMP → Alpha Vantage
  - Fundamentals: FMP → Alpha Vantage → yfinance
- Cache all fetched data in SQLite
- Log provider used and fallback events
- **Acceptance:** Data fetched with automatic fallback

**E7-T7: Implement Currency Conversion** [3 SP]
- Create `core/currency_converter.py`
- Fetch real-time FX rates (USD, EUR, GBP, JPY, CAD)
- Store FX snapshot with timestamp
- Normalize all prices to USD
- Support display in multiple currencies
- **Acceptance:** Prices converted correctly

---

### Epic 17: Deployment & Infrastructure (P0 - Must Have)
**Goal:** Deploy to production with CI/CD
**Story Points:** 21
**Dependencies:** E1-E7 (MVP features complete)

#### Tasks:

**E17-T1: Containerize Application** [3 SP]
- Create multi-stage Dockerfile (Python 3.12-slim base)
- Copy requirements and install dependencies
- Copy source code
- Expose port 8000
- Add healthcheck endpoint
- Build and test locally
- **Acceptance:** Docker image builds and runs

**E17-T2: Create Docker Compose for Local Dev** [2 SP]
- Create `docker-compose.yml`
- Define FastAPI service
- Mount volumes for hot-reload
- Add environment variables
- Add health checks
- **Acceptance:** `docker-compose up` starts app

**E17-T3: Set Up AWS Infrastructure** [5 SP]
- Create AWS account / use existing
- Set up ECR repository for Docker images
- Create ECS cluster (Fargate)
- Configure Application Load Balancer
- Set up CloudWatch logging
- Configure AWS Secrets Manager for API keys
- **Acceptance:** Infrastructure provisioned

**E17-T4: Configure CI/CD Pipeline** [5 SP]
- Create GitHub Actions workflow (`.github/workflows/deploy.yml`)
- Trigger on push to `main` branch
- Steps: lint → test → build → push to ECR → deploy to ECS
- Add manual approval for production deploy
- Configure secrets in GitHub
- **Acceptance:** Pipeline deploys successfully

**E17-T5: Set Up Domain & SSL** [2 SP]
- Register domain (e.g., stockevaluator.com)
- Configure Route 53 DNS
- Create ACM SSL certificate
- Configure ALB with HTTPS listener
- Redirect HTTP to HTTPS
- **Acceptance:** Site accessible via HTTPS

**E17-T6: Implement Monitoring & Alerts** [3 SP]
- Set up CloudWatch dashboards
- Create alarms: 5XX rate > 5%, P95 latency > 10s, CPU > 70%
- Integrate with PagerDuty or SNS for alerts
- Add structured logging (JSON format)
- **Acceptance:** Alerts trigger on issues

**E17-T7: Add API Rate Limiting** [1 SP]
- Implement rate limiting middleware (10 requests/min per IP)
- Return 429 Too Many Requests with Retry-After header
- Whitelist internal IPs
- **Acceptance:** Rate limits enforced

---

### Epic 18: Testing & Quality Assurance (P0 - Must Have)
**Goal:** Comprehensive test coverage
**Story Points:** 34
**Dependencies:** All features

#### Tasks:

**E18-T1: Set Up Testing Framework** [2 SP]
- Configure pytest with coverage plugin
- Set up test directory structure
- Add pytest fixtures for mock data
- Configure test database (SQLite in-memory)
- Add test commands to Makefile
- **Acceptance:** `pytest` command runs tests

**E18-T2: Write Unit Tests for Evaluation Engine** [5 SP]
- Test each stage of decision tree (6 stages)
- Test verdict logic (BUY, BUY with CAUTION, DO NOT BUY)
- Test close call detection
- Test edge cases (missing data, negative values)
- Aim for 90% code coverage in evaluator.py
- **Acceptance:** 20+ unit tests pass

**E18-T3: Write Unit Tests for Valuation Models** [3 SP]
- Test DCF calculation with known inputs
- Test Graham formula accuracy
- Test DDM with dividend stocks
- Test null handling (no dividends, no FCF)
- **Acceptance:** Valuation tests pass

**E18-T4: Write Unit Tests for Risk Assessment** [3 SP]
- Test each risk factor calculation
- Test composite score aggregation
- Test risk level determination
- Test recommendation generation
- **Acceptance:** Risk tests pass

**E18-T5: Write Integration Tests for API** [5 SP]
- Test `/health` endpoint (200 response)
- Test `/evaluate` endpoint with valid ticker (200 response)
- Test `/evaluate` with invalid ticker (400 response)
- Test API timeout handling
- Test rate limiting (429 response)
- Use `httpx.AsyncClient` for in-memory testing
- **Acceptance:** API integration tests pass

**E18-T6: Write Data Pipeline Tests** [4 SP]
- Test provider fallback logic (mock API failures)
- Test caching behavior (TTL expiration)
- Test currency conversion accuracy
- Test database read/write operations
- **Acceptance:** Data pipeline tests pass

**E18-T7: Create End-to-End Tests** [5 SP]
- Use Playwright or Selenium for browser automation
- Test: Search ticker → View results → Export PDF
- Test: Dark mode toggle
- Test: Flowchart rendering
- Test: Responsive design (mobile viewport)
- **Acceptance:** E2E tests pass on Chrome, Firefox, Safari

**E18-T8: Implement Visual Regression Testing** [3 SP]
- Use Percy or BackstopJS for screenshot comparison
- Capture screenshots of: landing page, results page, flowchart
- Test in light and dark modes
- Test at 3 viewport sizes
- **Acceptance:** Visual regressions caught

**E18-T9: Perform Load Testing** [2 SP]
- Use Locust to simulate 50 concurrent users
- Test sustained load: 10 req/sec for 5 minutes
- Measure P95 latency (target: <10s)
- Identify bottlenecks (database, API calls, LLM)
- **Acceptance:** System handles target load

**E18-T10: Manual UAT Testing** [2 SP]
- Create UAT test plan with 20 test cases
- Recruit 3-5 beta testers
- Gather feedback on usability
- Log bugs in issue tracker
- Prioritize fixes
- **Acceptance:** UAT feedback documented

---

## PHASE 2: Enhanced Analysis (Months 3-4)

### Epic 8: Technical Analysis Suite (P1 - Should Have)
**Goal:** Add technical indicators and charts
**Story Points:** 21
**Dependencies:** E7 (Data pipeline with prices)

#### Tasks:

**E8-T1: Implement Moving Averages** [2 SP]
- Calculate SMA(20, 50, 200)
- Detect Golden Cross (50 > 200) and Death Cross (50 < 200)
- Store in database
- **Acceptance:** MAs calculated correctly

**E8-T2: Implement RSI Indicator** [2 SP]
- Calculate RSI(14) from daily prices
- Identify overbought (>70) and oversold (<30) conditions
- **Acceptance:** RSI matches TradingView values

**E8-T3: Implement MACD Indicator** [2 SP]
- Calculate MACD(12, 26, 9)
- Detect bullish/bearish crossovers
- Calculate histogram
- **Acceptance:** MACD matches TradingView

**E8-T4: Implement Bollinger Bands** [2 SP]
- Calculate 20-period Bollinger Bands (2σ)
- Detect squeeze (low volatility) and expansion
- **Acceptance:** Bands match TradingView

**E8-T5: Implement ADX Indicator** [2 SP]
- Calculate ADX(14) for trend strength
- Identify strong trends (ADX > 25)
- **Acceptance:** ADX matches TradingView

**E8-T6: Calculate Technical Score** [3 SP]
- Aggregate indicators into 0-10 score
- Trend component (0-5): MA alignment, ADX
- Momentum component (0-5): RSI, MACD
- Determine signal: Sell (0-3), Hold (4-6), Buy (7-10)
- **Acceptance:** Technical score calculated

**E8-T7: Build Interactive Price Chart** [5 SP]
- Integrate Plotly.js for candlestick charts
- Add volume bars below price
- Overlay indicators (toggle on/off)
- Add crosshair with OHLC values
- Add zoom and pan controls
- Compare to S&P 500 (normalized returns)
- **Acceptance:** Interactive chart renders

**E8-T8: Create Technical Analysis UI Section** [3 SP]
- Add "Technical Analysis" tab to results page
- Display technical score prominently
- Show indicator values in table
- Display interactive chart
- Add signal badge (Buy/Hold/Sell)
- **Acceptance:** Technical section complete

---

### Epic 9: Macro Context Dashboard (P1 - Should Have)
**Goal:** Display economic indicators and recession signals
**Story Points:** 13
**Dependencies:** None

#### Tasks:

**E9-T1: Integrate FRED API** [3 SP]
- Install `fredapi` library
- Obtain FRED API key (free)
- Fetch GDP growth (quarterly)
- Fetch CPI inflation (monthly)
- Fetch unemployment rate (monthly)
- Fetch Fed funds rate (daily)
- Fetch 10Y-2Y Treasury spread (daily)
- Cache data in database (refresh cadence varies)
- **Acceptance:** Can fetch all macro indicators

**E9-T2: Implement Recession Signal Calculators** [4 SP]
- Sahm Rule: 3-month MA unemployment ≥ 0.5pp above 12-month low
- Yield Curve Inversion: 10Y-2Y negative for 30+ days
- Leading Economic Index (LEI): 3 consecutive monthly declines
- Buffett Indicator: Total Market Cap / GDP > 150%
- Calculate recession probability (0-100%)
- **Acceptance:** Recession signals accurate

**E9-T3: Build Macro Dashboard UI Component** [3 SP]
- Create card-based layout for macro indicators
- Display: GDP growth, CPI, unemployment, Fed rate, yield spread, VIX
- Color-code values (green/yellow/red based on thresholds)
- Show trend arrows (up/down/flat)
- **Acceptance:** Macro dashboard renders

**E9-T4: Add Recession Alert Banner** [2 SP]
- Display warning banner if recession signals triggered
- List active recession signals
- Add "Learn More" link to explanation page
- Make banner dismissible (localStorage)
- **Acceptance:** Banner shows when appropriate

**E9-T5: Integrate VIX (Fear Index)** [1 SP]
- Fetch VIX from yfinance (^VIX)
- Display in macro dashboard
- Color-code: <20 green, 20-30 yellow, >30 red
- **Acceptance:** VIX displayed correctly

---

### Epic 10: Comparative Analysis (P1 - Should Have)
**Goal:** Benchmark against peers and sector
**Story Points:** 13
**Dependencies:** E1, E7 (Core metrics + data pipeline)

#### Tasks:

**E10-T1: Build Peer Identification Algorithm** [3 SP]
- Fetch sector and industry from stock info
- Query for companies in same GICS sector + industry
- Filter by market cap (within 50% range)
- Filter by exchange (same as target)
- Return 3-5 comparable peers
- **Acceptance:** Peer list makes sense for test stocks

**E10-T2: Fetch Peer Metrics** [3 SP]
- For each peer, fetch core metrics (P/E, ROE, D/E, margin, growth)
- Cache peer data to reduce API calls
- Handle missing peer data gracefully
- **Acceptance:** Peer metrics fetched

**E10-T3: Calculate Sector Medians** [2 SP]
- Calculate median P/E, ROE, D/E, margin for sector
- Calculate percentile rank for target stock
- Determine valuation assessment (Undervalued/Fairly Valued/Overvalued)
- **Acceptance:** Sector statistics accurate

**E10-T4: Build Comparison Table Component** [3 SP]
- Create HTML table: Target | Peer 1-3 | Sector Median
- Metrics: P/E, ROE, D/E, Net Margin, Rev Growth
- Color-code cells (green if target > median, red if <)
- Add trophy icon for best-in-group
- **Acceptance:** Comparison table renders

**E10-T5: Add Historical Valuation Context** [2 SP]
- Fetch historical P/E ratios (5 years) for target
- Calculate min, max, mean, current
- Display chart showing current vs historical range
- Add percentile rank (e.g., "73rd percentile - Expensive")
- **Acceptance:** Historical context displayed

---

### Epic 11: Dividend Analysis (P2 - Nice to Have)
**Goal:** Assess dividend quality and sustainability
**Story Points:** 8
**Dependencies:** E1 (Core metrics)

#### Tasks:

**E11-T1: Fetch Dividend Data** [2 SP]
- Get dividend history (5 years) from yfinance
- Calculate current annual dividend
- Calculate dividend yield
- Calculate payout ratio
- **Acceptance:** Dividend data fetched

**E11-T2: Calculate Dividend Growth Rate** [2 SP]
- Calculate 5-year dividend CAGR
- Count consecutive years of increases
- Identify dividend aristocrats (10+ years growth)
- **Acceptance:** Growth rate calculated

**E11-T3: Assess Dividend Sustainability** [2 SP]
- Calculate FCF coverage (Dividend / FCF per share)
- Evaluate payout ratio (<60% safe, >80% risk)
- Calculate sustainability score (0-10)
- Determine level: Very Sustainable / Moderately Sustainable / At Risk
- **Acceptance:** Sustainability score accurate

**E11-T4: Build Dividend Dashboard Component** [2 SP]
- Display dividend yield prominently
- Show sustainability badge with color
- Display metrics: payout ratio, growth rate, years of growth
- Add forecast: next 12-month estimated dividend
- Show yield-on-cost for various entry prices
- **Acceptance:** Dividend section complete

---

### Epic 12: User Experience Enhancements (P1 - Should Have)
**Goal:** Polish UI/UX with animations and accessibility
**Story Points:** 21
**Dependencies:** E4 (Web UI foundation)

#### Tasks:

**E12-T1: Implement Smooth Scroll Navigation** [1 SP]
- Add smooth scrolling between sections
- Add "Back to Top" button
- Add section anchor links in header
- **Acceptance:** Smooth scroll works

**E12-T2: Add Micro-Interactions** [3 SP]
- Hover effects on buttons (scale, shadow)
- Click feedback (ripple effect)
- Success animations (checkmark after adding to watchlist)
- Loading spinners with brand colors
- **Acceptance:** Interactions feel polished

**E12-T3: Implement Skeleton Screens** [3 SP]
- Create skeleton for each section (pulsing gray boxes)
- Show skeletons during loading
- Fade-in content when ready
- **Acceptance:** No blank white screens during load

**E12-T4: Add Keyboard Shortcuts** [2 SP]
- `/` to focus search
- `Esc` to clear search
- Arrow keys to navigate flowchart
- `D` to toggle dark mode
- Display shortcuts modal (`?` key)
- **Acceptance:** Keyboard shortcuts work

**E12-T5: Improve Accessibility (WCAG 2.1 AA)** [5 SP]
- Add ARIA labels to all interactive elements
- Ensure keyboard navigation works everywhere
- Test with screen reader (NVDA or JAWS)
- Add skip-to-content link
- Ensure focus indicators visible
- Fix any contrast issues (WCAG checker tool)
- **Acceptance:** Passes WAVE accessibility checker

**E12-T6: Add Tooltips to All Metrics** [3 SP]
- Write clear explanations for each metric (glossary)
- Add info icon next to metric names
- Implement tooltip component (Tippy.js)
- Include formula and interpretation
- **Acceptance:** All metrics have tooltips

**E12-T7: Optimize Performance** [2 SP]
- Minify CSS and JS
- Lazy-load images and charts
- Use CDN for static assets
- Enable gzip compression
- Measure Lighthouse score (target: 90+)
- **Acceptance:** Page load <2s on 4G

**E12-T8: Add Favicon and PWA Manifest** [2 SP]
- Design favicon (16x16, 32x32, 180x180)
- Create PWA manifest.json
- Add service worker for offline caching
- Add "Add to Home Screen" prompt
- **Acceptance:** PWA installable on mobile

---

### Epic 16: Export & Reporting (P1 - Should Have)
**Goal:** Generate PDF reports and shareable links
**Story Points:** 13
**Dependencies:** E1-E12 (All analysis features)

#### Tasks:

**E16-T1: Implement PDF Generation** [5 SP]
- Install WeasyPrint or pdfkit library
- Create HTML template for PDF report
- Page 1: Executive Summary (verdict, AI summary, key metrics, risk gauge)
- Page 2: Flowchart (high-res PNG embed)
- Page 3: Valuation Analysis (intrinsic values, charts)
- Page 4: Technical & Comparative (price chart, peer table)
- Page 5: Risk & Macro (risk breakdown, macro dashboard)
- Add footer with disclaimer and generation date
- **Acceptance:** PDF exports with all sections

**E16-T2: Add PDF Download Button** [1 SP]
- Add "Export PDF" button to results page
- Trigger PDF generation on click
- Show progress indicator (generating...)
- Download file: `{TICKER}_Analysis_{DATE}.pdf`
- **Acceptance:** PDF downloads correctly

**E16-T3: Implement Shareable Links** [3 SP]
- Generate unique link for each analysis
- Store analysis results in database with expiry (30 days)
- Create share endpoint: `/share/{analysis_id}`
- Display analysis from stored data (no re-fetch)
- Add "Copy Link" button
- **Acceptance:** Shared links work

**E16-T4: Add Social Media Sharing** [2 SP]
- Add "Share on Twitter" button
- Add "Share on LinkedIn" button
- Pre-fill text: "Check out my analysis of {TICKER}: {VERDICT}"
- Include link to shared analysis
- **Acceptance:** Social sharing works

**E16-T5: Implement Email Report** [2 SP]
- Add "Email This Report" button
- Send PDF via email using SendGrid or AWS SES
- Include summary in email body
- Attach PDF
- **Acceptance:** Email sends with PDF

---

## PHASE 3: User Features (Months 5-6)

### Epic 13: Watchlist & Alerts (P1 - Should Have)
**Goal:** Track favorite stocks and get notifications
**Story Points:** 21
**Dependencies:** E15 (User accounts)

#### Tasks:

**E13-T1: Design Watchlist Data Model** [2 SP]
- Create `watchlist` table: user_id, ticker, added_at
- Create `alerts` table: user_id, ticker, alert_type, threshold, active
- Add indexes for fast queries
- **Acceptance:** Database schema created

**E13-T2: Implement Watchlist CRUD API** [3 SP]
- POST /watchlist - Add ticker
- GET /watchlist - List all tickers
- DELETE /watchlist/{ticker} - Remove ticker
- PUT /watchlist/{ticker} - Update notes
- Limit: 50 tickers per user
- **Acceptance:** API endpoints work

**E13-T3: Build Watchlist UI** [3 SP]
- Add "Watchlist" page in header navigation
- Display tickers in card/table layout
- Show: ticker, company name, current price, change %, last analyzed date
- Add "Analyze All" button (batch analysis)
- Add "Remove" button per ticker
- **Acceptance:** Watchlist UI functional

**E13-T4: Implement Price Alerts** [5 SP]
- Alert types: Price Above, Price Below
- Create alert configuration modal
- Add alert to database
- Create background job to check alerts (every 15 min)
- Send email notification when triggered
- Mark alert as triggered (don't re-notify)
- **Acceptance:** Price alerts trigger correctly

**E13-T5: Implement Fundamental Alerts** [5 SP]
- Alert types: P/E Below, ROE Above, Debt/Equity Below, Dividend Yield Above
- Create alert configuration modal
- Check alerts during nightly batch refresh
- Send email notification when triggered
- **Acceptance:** Fundamental alerts work

**E13-T6: Add Alert Management UI** [3 SP]
- Add "Alerts" tab to watchlist page
- Display active alerts in table
- Show: ticker, alert type, threshold, created date
- Add "Edit" and "Delete" buttons
- Add "Create New Alert" button
- **Acceptance:** Can manage alerts via UI

---

### Epic 14: Portfolio Tracking (P1 - Should Have)
**Goal:** Track holdings and portfolio performance
**Story Points:** 21
**Dependencies:** E15 (User accounts)

#### Tasks:

**E14-T1: Design Portfolio Data Model** [2 SP]
- Create `portfolio` table: user_id, ticker, shares, avg_cost, date_acquired
- Add indexes
- **Acceptance:** Database schema created

**E14-T2: Implement CSV Import** [3 SP]
- Accept CSV file: Ticker, Shares, Avg Cost, Date
- Validate CSV format
- Parse and insert into database
- Handle errors (invalid tickers, negative shares)
- **Acceptance:** CSV import works

**E14-T3: Build Portfolio API** [3 SP]
- POST /portfolio/import - Import CSV
- GET /portfolio - List all holdings
- POST /portfolio - Add holding manually
- PUT /portfolio/{id} - Update holding
- DELETE /portfolio/{id} - Remove holding
- **Acceptance:** API endpoints work

**E14-T4: Calculate Portfolio Metrics** [5 SP]
- Total invested value
- Current market value
- Total return ($ and %)
- Unrealized gain/loss per holding
- Sector allocation (pie chart data)
- Top 5 holdings by weight
- **Acceptance:** Metrics calculated correctly

**E14-T5: Calculate Risk-Adjusted Returns** [3 SP]
- Fetch historical returns for portfolio
- Calculate portfolio beta (vs S&P 500)
- Calculate Sharpe ratio (using risk-free rate)
- Calculate alpha (excess return vs benchmark)
- **Acceptance:** Risk metrics accurate

**E14-T6: Build Portfolio Dashboard UI** [3 SP]
- Add "Portfolio" page in navigation
- Display total value, return, gain/loss prominently
- Show holdings table with per-stock returns
- Display sector allocation pie chart
- Display performance chart (vs S&P 500)
- **Acceptance:** Portfolio dashboard complete

**E14-T7: Add Rebalancing Suggestions** [2 SP]
- Analyze current sector allocation
- Compare to target allocation (equal-weight or custom)
- Suggest buys/sells to rebalance
- Calculate number of shares to trade
- **Acceptance:** Rebalancing suggestions displayed

---

### Epic 15: User Authentication & Accounts (P1 - Should Have)
**Goal:** Allow users to create accounts and login
**Story Points:** 13
**Dependencies:** None (enables E13, E14)

#### Tasks:

**E15-T1: Design User Data Model** [2 SP]
- Create `users` table: id, email, password_hash, created_at, last_login
- Add unique index on email
- **Acceptance:** Database schema created

**E15-T2: Implement Registration** [3 SP]
- POST /auth/register - Create account
- Validate email format
- Hash password with bcrypt
- Send confirmation email (optional)
- Return JWT token
- **Acceptance:** Can create account

**E15-T3: Implement Login** [2 SP]
- POST /auth/login - Authenticate user
- Verify email and password
- Return JWT token (expires in 7 days)
- Update last_login timestamp
- **Acceptance:** Can login and receive token

**E15-T4: Implement JWT Middleware** [2 SP]
- Verify JWT token in Authorization header
- Extract user_id from token
- Add to request context
- Return 401 if invalid/expired token
- **Acceptance:** Protected routes require valid token

**E15-T5: Build Registration/Login UI** [3 SP]
- Create registration form (email, password, confirm password)
- Create login form (email, password)
- Add "Forgot Password" link (future feature)
- Store JWT in localStorage
- Redirect to dashboard after login
- **Acceptance:** Can register and login via UI

**E15-T6: Implement Logout** [1 SP]
- Clear JWT from localStorage
- Redirect to landing page
- Add "Logout" button in header
- **Acceptance:** Can logout

---

## PHASE 4: Advanced Intelligence (Months 7-9)

### Epic 19: Natural Language Screener (P2 - Nice to Have)
**Goal:** Query stocks using natural language
**Story Points:** 21

#### Tasks:

**E19-T1: Implement Query Parser** [5 SP]
- Use LLM to parse natural language query
- Extract: sector filter, metric thresholds, sorting
- Example: "tech stocks with ROE > 20% and P/E < 25"
- Convert to structured query
- **Acceptance:** Parses 10 example queries correctly

**E19-T2: Build Stock Screener Engine** [8 SP]
- Query database for stocks matching criteria
- Support filters: sector, market cap, metrics
- Support sorting by any metric
- Return top 20 results
- **Acceptance:** Screener returns relevant stocks

**E19-T3: Create Screener UI** [5 SP]
- Add natural language search box
- Display results in table (ticker, name, key metrics)
- Add "Analyze" button per result
- Add filter chips (Applied Filters)
- **Acceptance:** Screener UI functional

**E19-T4: Add Saved Screeners** [3 SP]
- Allow users to save screener queries
- Store in database (user_id, name, query)
- Add "Saved Screeners" dropdown
- **Acceptance:** Can save and load screeners

---

### Epic 20: Automated Reports (P2 - Nice to Have)
**Goal:** Daily/weekly email digests
**Story Points:** 13

#### Tasks:

**E20-T1: Implement Daily Watchlist Report** [5 SP]
- Schedule daily job (9 AM user timezone)
- Fetch watchlist tickers
- Re-analyze each ticker
- Detect changes (verdict, risk score, price)
- Generate HTML email with summary
- Send via SendGrid/AWS SES
- **Acceptance:** Daily email sends

**E20-T2: Implement Weekly Portfolio Report** [5 SP]
- Schedule weekly job (Monday 9 AM)
- Calculate portfolio performance (week over week)
- List top gainers/losers
- Show sector allocation changes
- Include market commentary (macro context)
- **Acceptance:** Weekly email sends

**E20-T3: Add Email Preferences** [3 SP]
- Add settings page for email preferences
- Toggle: daily watchlist report, weekly portfolio report
- Set timezone
- **Acceptance:** Can control email frequency

---

### Epic 21: Sentiment Analysis (P2 - Nice to Have)
**Goal:** Track social and news sentiment
**Story Points:** 21

#### Tasks:

**E21-T1: Integrate News API** [5 SP]
- Use News API or Alpha Vantage News
- Fetch recent news articles for ticker
- Extract headline and sentiment (positive/negative/neutral)
- Store in database
- **Acceptance:** Can fetch news for any ticker

**E21-T2: Implement Sentiment Scoring** [5 SP]
- Use LLM to analyze news sentiment
- Aggregate to overall sentiment score (0-100)
- Determine sentiment level: Bullish / Neutral / Bearish
- **Acceptance:** Sentiment score calculated

**E21-T3: Add Insider Trading Tracker** [5 SP]
- Fetch insider transactions from SEC or data provider
- Identify significant buys/sells
- Display in timeline
- Flag unusual activity
- **Acceptance:** Insider trades displayed

**E21-T4: Build Sentiment Dashboard** [3 SP]
- Add "Sentiment" tab to results page
- Display sentiment gauge
- List recent news articles with sentiment
- Display insider trades
- **Acceptance:** Sentiment dashboard complete

**E21-T5: Add Social Media Sentiment (Future)** [3 SP]
- Integrate with Twitter API or Reddit API
- Track mentions of $TICKER
- Analyze sentiment of posts
- Display sentiment trend
- **Acceptance:** Social sentiment tracked

---

### Epic 22: Pattern Recognition (P2 - Nice to Have)
**Goal:** Identify chart patterns
**Story Points:** 13

#### Tasks:

**E22-T1: Implement Support/Resistance Detection** [5 SP]
- Analyze 52-week price history
- Identify significant support levels (price floors)
- Identify significant resistance levels (price ceilings)
- Display on chart
- **Acceptance:** Levels detected accurately

**E22-T2: Implement Fibonacci Retracement** [3 SP]
- Calculate Fibonacci levels (23.6%, 38.2%, 50%, 61.8%)
- Display on chart
- **Acceptance:** Fibonacci levels correct

**E22-T3: Implement Pattern Detection** [5 SP]
- Detect: Head & Shoulders, Double Top/Bottom, Triangles
- Use rule-based algorithm or ML model
- Display pattern label on chart
- Add pattern description
- **Acceptance:** Patterns detected (70% accuracy)

---

### Epic 23: Backtesting Tool (P2 - Nice to Have)
**Goal:** Test historical performance of strategy
**Story Points:** 21

#### Tasks:

**E23-T1: Design Backtest Framework** [5 SP]
- Define backtest parameters: start date, end date, initial capital
- Simulate buying stocks that pass evaluation criteria
- Track portfolio value over time
- **Acceptance:** Framework designed

**E23-T2: Implement Backtesting Engine** [8 SP]
- Fetch historical fundamentals for stocks
- Run evaluation for each day
- Simulate buy/sell decisions
- Track portfolio performance
- Calculate: total return, CAGR, max drawdown, Sharpe ratio
- **Acceptance:** Backtest runs for S&P 500 stocks (2015-2025)

**E23-T3: Build Backtest UI** [5 SP]
- Add "Backtest" page
- Configure backtest parameters (date range, universe, thresholds)
- Run backtest button
- Display results: performance chart, metrics, trade log
- **Acceptance:** Backtest UI functional

**E23-T4: Compare to Benchmark** [3 SP]
- Compare backtest results to S&P 500 buy-and-hold
- Calculate alpha and beta
- Display comparison chart
- **Acceptance:** Benchmark comparison displayed

---

## PHASE 5: Scale & Monetization (Months 10-12)

### Epic 24: Freemium Model (P1 - Should Have)
**Goal:** Implement usage limits and subscriptions
**Story Points:** 21

#### Tasks:

**E24-T1: Implement Usage Tracking** [3 SP]
- Track analyses per user per month
- Store in database: user_id, month, count
- **Acceptance:** Usage tracked

**E24-T2: Add Usage Limits** [3 SP]
- Free tier: 5 analyses/month
- Pro tier: unlimited analyses
- Check limit before evaluation
- Return 403 if limit exceeded
- **Acceptance:** Limits enforced

**E24-T3: Integrate Stripe for Subscriptions** [5 SP]
- Set up Stripe account
- Create product: Pro plan ($9.99/month)
- Implement Stripe Checkout
- Handle webhook for successful payment
- Update user tier in database
- **Acceptance:** Can subscribe via Stripe

**E24-T4: Build Pricing Page** [3 SP]
- Display Free vs Pro comparison table
- Add "Upgrade to Pro" button
- Redirect to Stripe Checkout
- **Acceptance:** Pricing page complete

**E24-T5: Add Subscription Management** [3 SP]
- Create "Account" page
- Display current plan and usage
- Add "Manage Subscription" button (Stripe portal)
- Allow cancellation
- **Acceptance:** Can manage subscription

**E24-T6: Show Upgrade Prompts** [2 SP]
- Display upgrade prompt when limit reached
- Show "X of 5 analyses used this month" in header
- Add CTA: "Upgrade for unlimited"
- **Acceptance:** Upgrade prompts displayed

**E24-T7: Implement Referral Program** [2 SP]
- Generate unique referral link per user
- Give 1 free month to referrer when referee subscribes
- Track referrals in database
- **Acceptance:** Referral program works

---

### Epic 25: API Access for Developers (P2 - Nice to Have)
**Goal:** Offer paid API for external developers
**Story Points:** 13

#### Tasks:

**E25-T1: Create API Key System** [3 SP]
- Generate API keys for users
- Store in database with usage limits
- Add API key authentication middleware
- **Acceptance:** API keys authenticate requests

**E25-T2: Implement API Usage Tracking** [3 SP]
- Track API calls per key per month
- Store in database
- Return 429 if limit exceeded
- **Acceptance:** API usage tracked

**E25-T3: Create Developer Portal** [5 SP]
- Add "API" page with documentation
- Display API key (generate if missing)
- Show usage stats
- Provide code examples (Python, JavaScript, cURL)
- **Acceptance:** Developer portal complete

**E25-T4: Add API Pricing Tier** [2 SP]
- API Starter: $49/month for 1000 calls
- API Pro: $199/month for 10,000 calls
- Integrate with Stripe
- **Acceptance:** Can subscribe to API plan

---

### Epic 26: International Stock Support (P2 - Nice to Have)
**Goal:** Support non-US exchanges
**Story Points:** 21

#### Tasks:

**E26-T1: Implement Exchange Suffix Parsing** [3 SP]
- Support suffixes: .L (London), .DE (Germany), .T (Tokyo), .TO (Toronto), .AX (Australia)
- Parse ticker to extract symbol and exchange
- Store exchange in database
- **Acceptance:** Can parse international tickers

**E26-T2: Fetch International Stock Data** [5 SP]
- Update yfinance calls to use full ticker with suffix
- Fetch fundamentals in native currency
- Fetch prices in native currency
- **Acceptance:** Can fetch data for international stocks

**E26-T3: Implement Multi-Currency Normalization** [5 SP]
- Fetch real-time FX rates for all currencies
- Normalize prices to USD for comparison
- Display prices in native currency and USD
- **Acceptance:** Multi-currency display works

**E26-T4: Adjust Thresholds by Region** [3 SP]
- Research regional benchmark differences (e.g., Japan P/E averages lower)
- Allow threshold adjustments by exchange
- Apply regional thresholds in evaluation
- **Acceptance:** Regional thresholds applied

**E26-T5: Add Exchange Filter to Screener** [2 SP]
- Add exchange dropdown to screener
- Filter results by exchange
- **Acceptance:** Can filter by exchange

**E26-T6: Test with International Stocks** [3 SP]
- Test with 10 stocks from each exchange
- Verify data accuracy
- Fix any issues
- **Acceptance:** International stocks work

---

### Epic 27: Mobile Native Apps (P2 - Nice to Have)
**Goal:** Build iOS and Android apps
**Story Points:** 55 (Large effort, separate project)

_Tasks omitted for brevity - would include: React Native setup, mobile UI components, app store submission, push notifications, etc._

---

### Epic 28: White-Label Solution (P2 - Nice to Have)
**Goal:** Offer platform to financial advisors
**Story Points:** 34

_Tasks omitted for brevity - would include: Multi-tenancy, custom branding, client management, billing per advisor, etc._

---

## Sprint Planning Guidelines

### Sprint Duration: 2 weeks

### Velocity Estimation:
- Junior Developer: 8 SP/sprint
- Mid-level Developer: 13 SP/sprint
- Senior Developer: 21 SP/sprint

### Team Composition (Recommended):
- 1 Senior Full-Stack Developer (Backend/Frontend)
- 1 Mid-level Frontend Developer (UI/UX)
- 1 Mid-level Backend Developer (Data/ML)
- 1 QA Engineer (part-time)

**Team Velocity:** ~42 SP/sprint

---

## Phase 1 Sprint Breakdown (MVP)

### Sprint 1 (Weeks 1-2): Foundation
- E7-T1 to E7-T3: Database + yfinance integration [9 SP]
- E1-T1 to E1-T2: Threshold system + data extractor [8 SP]
- E4-T1: Frontend setup [2 SP]
- E18-T1: Testing framework [2 SP]
- **Total: 21 SP**

### Sprint 2 (Weeks 3-4): Core Evaluation
- E1-T3 to E1-T5: Evaluation logic [14 SP]
- E7-T4 to E7-T5: FMP + Alpha Vantage integration [5 SP]
- E18-T2: Unit tests for evaluator [5 SP]
- **Total: 24 SP**

### Sprint 3 (Weeks 5-6): Flowcharts + UI
- E2-T1 to E2-T3: Flowchart generation + coloring [11 SP]
- E4-T2 to E4-T4: Landing page + search + results layout [11 SP]
- E18-T5: API integration tests [5 SP]
- **Total: 27 SP**

### Sprint 4 (Weeks 7-8): AI + Valuation
- E3-T1 to E3-T5: LLM integration [13 SP]
- E5-T1 to E5-T3: Intrinsic valuation models [11 SP]
- E2-T4 to E2-T5: Flowchart interactivity [8 SP]
- E18-T3: Valuation tests [3 SP]
- **Total: 35 SP** (High sprint - prioritize)

### Sprint 5 (Weeks 9-10): Risk + Data Pipeline
- E6-T1 to E6-T4: Risk assessment system [13 SP]
- E7-T6 to E7-T7: Multi-source client + currency conversion [7 SP]
- E1-T6 to E1-T8: Extended metrics + service layer [12 SP]
- E18-T4: Risk tests [3 SP]
- **Total: 35 SP**

### Sprint 6 (Weeks 11-12): Polish + Deploy
- E4-T5 to E4-T8: Loading states + errors + dark mode + responsive [8 SP]
- E17-T1 to E17-T3: Docker + AWS infrastructure [10 SP]
- E18-T6 to E18-T9: Data tests + E2E tests + load tests [14 SP]
- E2-T6: Flowchart export [2 SP]
- **Total: 34 SP**

### Sprint 7 (Week 13-14): CI/CD + Launch
- E17-T4 to E17-T7: CI/CD + domain + monitoring + rate limiting [11 SP]
- E18-T10: UAT testing [2 SP]
- Bug fixes from UAT [13 SP estimated]
- Production launch preparation
- **Total: 26 SP + launch activities**

**Phase 1 Total: 7 sprints (14 weeks / ~3.5 months)**

---

## Success Criteria

### MVP Launch Criteria (End of Phase 1):
- ✅ User can search any US stock ticker
- ✅ System returns BUY/DO NOT BUY/BUY with CAUTION verdict in <10s
- ✅ Interactive Mermaid flowchart displays decision path
- ✅ AI-generated summary with conviction score
- ✅ 3 intrinsic valuation models displayed
- ✅ Risk assessment score (0-100) with breakdown
- ✅ 90% uptime on production
- ✅ 90% code coverage on core evaluation engine
- ✅ Responsive design works on mobile/desktop
- ✅ Dark mode functional
- ✅ Legal disclaimers prominent

### Phase 2 Success Criteria:
- ✅ Technical analysis with 5 indicators + interactive charts
- ✅ Macro dashboard with recession signals
- ✅ Comparative analysis with 3-5 peers
- ✅ PDF export functional
- ✅ Lighthouse score > 90

### Phase 3 Success Criteria:
- ✅ User accounts with email/password auth
- ✅ Watchlist with 50-ticker limit
- ✅ Portfolio tracking with performance metrics
- ✅ Price + fundamental alerts working
- ✅ 1000+ registered users

### Phase 4 Success Criteria:
- ✅ Natural language screener functional
- ✅ Automated daily/weekly reports
- ✅ Sentiment analysis integrated
- ✅ Pattern recognition with 70% accuracy

### Phase 5 Success Criteria:
- ✅ Freemium model with Stripe integration
- ✅ 10% conversion rate (free to paid)
- ✅ API access for developers
- ✅ International stock support (5+ exchanges)
- ✅ 10,000+ MAU (monthly active users)
- ✅ Profitable (revenue > costs)

---

## Risk Management

| Risk | Mitigation | Owner |
|------|-----------|-------|
| **API rate limits (yfinance, LLM)** | Multi-source fallback; aggressive caching | Backend Lead |
| **Scope creep** | Strict sprint planning; defer to future phases | PM |
| **Data quality issues** | Validation layer; outlier detection | Data Engineer |
| **Poor user adoption** | User research; beta testing; iterate on feedback | PM + UX |
| **Performance bottlenecks** | Load testing early; optimize queries; use CDN | Backend Lead |
| **Security vulnerabilities** | Code reviews; dependency scanning; penetration test | Security Lead |
| **Budget overrun (LLM costs)** | Rate limiting; cache aggressively; monitor spend | PM |

---

## Appendix: Task Estimation Guide

| Complexity | Story Points | Estimated Hours | Examples |
|------------|--------------|-----------------|----------|
| **Trivial** | 1 SP | 1-2 hours | Add button, update text, simple config |
| **Small** | 2 SP | 2-4 hours | Simple API endpoint, basic UI component |
| **Medium** | 3 SP | 4-8 hours | Complex API logic, database schema |
| **Large** | 5 SP | 1-2 days | Algorithm implementation, integration |
| **X-Large** | 8 SP | 2-3 days | Full feature module, complex integration |
| **XX-Large** | 13 SP | 1 week | Major subsystem, multi-component feature |
| **XXX-Large** | 21 SP | 2 weeks | Epic-level work, requires breakdown |

---

## Next Steps

1. **Review & Approve Epics** - Stakeholder sign-off on scope
2. **Refine Sprint 1 Tasks** - Break down into subtasks with acceptance criteria
3. **Set Up Project Board** - Create Jira/GitHub Projects board with epics and tasks
4. **Assign Team Members** - Allocate tasks based on expertise
5. **Kick Off Sprint 1** - Daily standups, sprint review/retro cadence
6. **Track Progress** - Update task status daily; adjust sprint scope as needed

---

**Document Status:** Ready for Review
**Next Review Date:** 2025-11-07
**Owner:** Bruno Dias (Product Owner)
