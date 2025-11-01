# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

BD_StockEvaluator is a full-stack stock evaluation platform featuring a Python backend with both Flask web UI and FastAPI REST endpoints, plus a native Android client. The system performs comprehensive fundamental and technical stock analysis with AI-powered opinions and dynamic flowchart visualizations.

## Common Development Commands

### Python Backend

**Installation:**
```bash
pip install -r requirements.txt
# or with dev dependencies
pip install -e .[dev]
```

**Run Flask Web UI:**
```bash
python src/bd_stockevaluator/app.py
```

**Run FastAPI REST API:**
```bash
uvicorn src.bd_stockevaluator.api.main:app --reload
```

**Run Tests:**
```bash
# All tests
pytest

# Specific test file
pytest tests/test_service.py

# With coverage
pytest --cov=bd_stockevaluator
```

**Code Quality:**
```bash
# Format with Black
black src/bd_stockevaluator

# Lint with Ruff
ruff check src/bd_stockevaluator
```

**Run Demo:**
```bash
python src/bd_stockevaluator/demo.py
```

**Daily Portfolio Report:**
```bash
python -m bd_stockevaluator.cli.daily_report_cli
```

### Android Client

**Build Debug APK:**
```powershell
cd android-client
./gradlew.bat assembleDebug
```

**Install on Device:**
```powershell
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**Run Unit Tests:**
```powershell
./gradlew.bat testDebugUnitTest
```

**Run Instrumentation Tests:**
```powershell
./gradlew.bat connectedDebugAndroidTest
```

## Architecture

### Core Service Layer (`src/bd_stockevaluator/core/`)

The heart of the application is `StockAnalysisService` in `core/service.py`, which orchestrates all analysis components. This service is shared between Flask, FastAPI, and any future clients.

**Key Components:**
- `service.py`: Main `StockAnalysisService` facade providing `analyze()`, `evaluate_watchlist()`, and `build_sync_payload()` methods
- `data_pipeline.py`: Multi-source data aggregation with `SQLiteDataStore`, `MultiSourceDataClient`, and `CurrencyConverter`
- `macro.py`: `MacroContextService` for FRED-powered macroeconomic indicators
- `watchlist.py`: `WatchlistAlertEngine` for portfolio monitoring with dot-path rule evaluation
- `portfolio.py` & `portfolio_performance.py`: Portfolio tracking and performance metrics
- `benchmarks.py`: Industry benchmark comparisons
- `keys.py`: API key management

### Analysis Modules (`src/bd_stockevaluator/analysis/`)

- `epic2.py`: `Epic2Analyzer` for advanced valuation, profitability, growth trends, and intrinsic value models
- `epic3.py`: `Epic3TechnicalAnalyzer` for technical indicators (RSI, MACD, Bollinger Bands), pattern detection, and chart generation
- `epic4_macro.py`: Macro backdrop analysis integration
- `epic5_qualitative.py`: Moat assessment (`MoatScorecardBuilder`), ownership trends (`OwnershipTrendAnalyzer`), and management quality (`ManagementQualityAnalyzer`)

### Core Logic

- `evaluator.py`: `StockEvaluator` class that implements the decision flowchart with configurable thresholds for revenue growth, P/E, ROE, margins, debt/equity, and quick ratio
- `features.py`: `StockAnalysisFeatures` providing risk assessment, trend analysis, comparative analysis, and dividend analysis

### Web Interfaces

- `app.py`: Flask application serving the web UI with Mermaid flowchart rendering
- `api/main.py`: FastAPI service with `/health`, `/evaluate`, `/features/{ticker}`, and `/sync/{ticker}` endpoints
- `ux/dashboard.py`: Streamlit dashboard (alternative UI)
- `ux/chart_explorer.py`: Interactive chart exploration interface

### Reports (`src/bd_stockevaluator/reports/`)

- `daily_report.py`: Automated daily portfolio digest
- `my_holdings.py`: Personal portfolio tracking
- `per_ticker.py`: Individual stock report generation
- `portfolio_automation.py`: Scheduled portfolio tasks

### Android Client (`android-client/`)

MVVM architecture with:
- **Data Layer**: `StockRepository`, `StockApi` (Retrofit), `EvaluationDao` (Room cache)
- **Domain Models**: `EvaluationSummary`, `EvaluationDetail`
- **UI Layer**: `HomeScreen` (Compose), `HomeViewModel`
- **DI**: Hilt modules in `di/`

The Android app consumes the FastAPI endpoints and stores the last 20 evaluations locally for offline access.

## Configuration

### API Keys

API keys are managed via:
1. `config/api_keys.txt` file (key=value format)
2. `.env` file in project root
3. Environment variables

Required keys:
- `api_key_groq` or `api_key_gemini`: For AI opinion generation
- `FRED_API_KEY`: For macroeconomic data
- Optional: `api_key_aistudio_google` for additional AI features

### Watchlist Configuration

Edit `config/watchlist.json` to configure automated alerts:
```json
[
  {
    "ticker": "AAPL",
    "channels": ["console", "email"],
    "rules": [
      {"path": "risk_assessment.risk_score", "operator": ">=", "value": 60}
    ]
  }
]
```

Rules use dot-delimited paths into the analysis payload. See `bd_stockevaluator/core/watchlist.py` for supported operators: `>=`, `>`, `<=`, `<`, `==`, `!=`.

## Important Patterns

### Data Flow

1. **Fetching**: `get_stock_data(ticker)` → `MultiSourceDataClient.sync_ticker()` → cached in `SQLiteDataStore`
2. **Analysis**: `StockAnalysisService.analyze(ticker)` → orchestrates all analyzers → returns comprehensive payload
3. **Rendering**: Flask/FastAPI serialize the payload → frontend displays flowchart, metrics, and AI opinion

### Caching Strategy

- `get_stock_data()` uses `@cached(TTLCache(maxsize=100, ttl=600))` for 10-minute cache
- `SQLiteDataStore` persists fundamentals and price history in `data/stocks.db`
- Macro indicators cached in `data/macro/` directory
- Android Room DB caches last 20 evaluations

### AI Opinion Generation

Attempts Groq first (faster, configurable via `GROQ_API_BASE` and `GROQ_MODEL`), then falls back to Gemini (configured via `GEMINI_MODEL`). Uses markdown formatting, converted to HTML for display.

### Flowchart Generation

`generate_flowchart_definition()` in `service.py` produces Mermaid syntax with:
- Status-based node coloring (green=PASS, red=FAIL, yellow=CLOSE_FAIL)
- Active link highlighting based on the evaluation path
- Sequenced rendering for animated UI experience

## Testing Strategy

Tests are organized by epic/feature:
- `test_service.py`: Core service layer
- `test_epic2_analyzer.py`: Advanced fundamental analysis
- `test_epic3_technical.py`: Technical indicators and charts
- `test_epic4_macro.py`: Macro context integration
- `test_epic5_qualitative.py`: Moat and management quality
- `test_epic6_watchlist.py` & `test_epic6_portfolio.py`: Portfolio features
- `test_api.py`: FastAPI endpoints
- `test_integration.py` & `test_final_validation.py`: End-to-end workflows
- `conftest.py`: Shared fixtures

Run individual test suites when working on specific features.

## Package Structure

The package uses `pyproject.toml` with source layout (`src/bd_stockevaluator/`). Static assets (templates, CSS, charts) are included via `MANIFEST.in` and package data configuration.

Templates live in `src/bd_stockevaluator/templates/`, static files in `src/bd_stockevaluator/static/`.

## Mobile Development

The Android client requires:
- Backend running locally or on accessible network
- Update `buildConfigField` in `app/build.gradle.kts` to point to backend URL
- JDK 17 and Android SDK Platform 34
- Room database schema at `app/src/main/java/com/bdfinance/stockevaluator/data/local/`

WebView components render Mermaid flowcharts and HTML opinions from the API.

## Background Scheduler

Flask app (`app.py`) supports background refresh of tickers via `SCHEDULER_HOOKS.client.sync_ticker()`. The scheduler runs in a separate thread and can be configured for interval-based updates.

## New Features (Epics 8, 9, 10, & 11)

### Epic 8: AI & Automation Layer

**Financial Summary Agent (F8.1):**
- Located in `src/bd_stockevaluator/ai/agents.py`
- Generates structured 1-10 ratings for stocks:
  - Overall score
  - Buy rating
  - Quality rating
  - Value rating
  - Growth rating
  - Financial health rating
- Provides strengths, weaknesses, recommendation, and detailed rationale
- API endpoint: `POST /ai/rating/{ticker}`
- Uses Groq (primary) → Gemini (fallback) for AI generation

**Market Commentary Bot (F8.2):**
- Located in `src/bd_stockevaluator/ai/agents.py`
- Generates daily/weekly market summaries
- Analyzes macro context and provides sentiment (Bullish/Neutral/Bearish)
- Identifies key risks and opportunities
- API endpoint: `GET /ai/market-commentary?period=daily`

**Natural-Language Screener (F8.3):**
- Located in `src/bd_stockevaluator/ai/screener.py`
- Parses queries like "find cheap tech stocks with ROE > 15% and low debt"
- Extracts structured criteria (sectors, metrics, valuations)
- Screens stock universe based on parsed criteria
- API endpoint: `POST /ai/screen`
- Example usage:
```python
from bd_stockevaluator.ai import NaturalLanguageScreener
screener = NaturalLanguageScreener()
criteria = screener.parse_query("cheap tech stocks with ROE > 15%")
```

### Epic 9: API Gateway & Rate Limiting

**Rate Limiting Middleware (F9.3):**
- Located in `src/bd_stockevaluator/api/middleware.py`
- In-memory sliding window rate limiter
- Configurable via `RATE_LIMIT_PER_MINUTE` environment variable (default: 60)
- Per-client tracking (by API key or IP address)
- Standard HTTP 429 responses with Retry-After headers
- Rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- Exempt paths: `/health`, `/docs`, `/openapi.json`, `/redoc`

**API Key Authentication:**
- Optional authentication (disabled by default)
- Enable with `REQUIRE_API_KEY=true`
- Multiple API keys supported (comma-separated in `VALID_API_KEYS`)
- Standard HTTP 401 responses for unauthorized requests
- X-API-Key header authentication

**Request Logging:**
- All API requests logged with timestamp, method, path, status code, and duration
- Structured logging format for production monitoring
- Automatic request/response tracking

**Configuration:**
```env
RATE_LIMIT_PER_MINUTE=60
REQUIRE_API_KEY=false
VALID_API_KEYS=sk_key1,sk_key2
DEFAULT_API_KEY=dev-key-123
```

**Usage:**
```bash
# Without API key (default)
curl http://localhost:8000/ai/rating/MSFT

# With API key (if authentication enabled)
curl -H "X-API-Key: sk_your_key" http://localhost:8000/ai/rating/MSFT
```

### Epic 10: UX Improvements

**Flowchart Text Visibility (F10.2):**
- Located in `src/bd_stockevaluator/static/flowchart.js`
- Automatic label wrapping for better readability:
  - Labels longer than 30 characters are wrapped at word boundaries
  - Maximum 2 lines per label (25 characters per line)
  - Ellipsis (...) added if text exceeds 2 lines
- Dynamic node height adjustment:
  - Nodes automatically expand to accommodate 2-line labels
  - Text remains vertically centered
  - 20px padding around text for breathing room
- Accessibility features:
  - Full text available in SVG `<title>` element on hover
  - `aria-label` attribute with complete text
  - Keyboard-accessible tooltips
- Multi-shape support:
  - Works with rectangles, circles, and polygons
  - Intelligent center position calculation

**Visual Example:**
```
Before: [Revenue Growth (TTM) >= 10%?]

After:  [Revenue Growth (TTM) ]
        [>= 10%?             ]
```

### Epic 11: Production-Ready Docker Containerization

**Multi-Stage Dockerfile (F11.1):**
- Builder stage: Compiles dependencies and creates wheels
- Runtime stage: Minimal Python 3.12-slim image
- Non-root user (appuser:1000) for security
- Automatic health checks every 30s
- Persistent volume support for SQLite data
- Environment variable configuration
- Build: `docker build -t bd_stockevaluator:latest .`
- Run: `docker-compose up -d`

**Docker Testing Infrastructure:**
- Mock Docker client for fast CI testing
- Real Docker integration tests (opt-in)
- Environment flags: `DOCKER_RUNTIME=mock|real`, `DOCKER_AVAILABLE=0|1`
- Test file: `tests/test_docker.py`
- Run mock tests: `pytest tests/test_docker.py`
- Run real tests: `DOCKER_AVAILABLE=1 DOCKER_RUNTIME=real pytest tests/test_docker.py`

**Docker Compose Configuration:**
- Includes all necessary environment variables
- Volume mounts for persistent data (`stock-data`)
- Configurable ports via `API_PORT` env var
- Automatic restart policy
- Logging with rotation (10MB max, 3 files)

## API Endpoints Reference

### Core Endpoints
- `GET /health` - Health check
- `POST /evaluate` - Full stock evaluation
- `GET /features/{ticker}` - Feature analysis only
- `GET /sync/{ticker}` - Sync payload for mobile clients

### AI Endpoints (Epic 8)
- `POST /ai/rating/{ticker}` - AI-powered 1-10 rating with rationale
- `GET /ai/market-commentary` - Daily/weekly market commentary
- `POST /ai/screen` - Natural language stock screener

## Development Workflow

### Testing Epic 8 AI Features

**Financial Summary Agent:**
```bash
# Start API
uvicorn src.bd_stockevaluator.api.main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/ai/rating/MSFT
```

**Market Commentary Bot:**
```bash
curl http://localhost:8000/ai/market-commentary?period=daily
```

**Natural Language Screener:**
```bash
curl -X POST http://localhost:8000/ai/screen \
  -H "Content-Type: application/json" \
  -d '{"query": "cheap tech stocks with high ROE", "tickers": ["MSFT", "AAPL", "GOOGL"]}'
```

### Docker Development

**Local Build and Test:**
```bash
# Build image
docker build -t bd_stockevaluator:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop and cleanup
docker-compose down -v
```

**Testing with Mock Docker:**
```bash
# Fast CI tests without Docker daemon
DOCKER_RUNTIME=mock pytest tests/test_docker.py
```

**Testing with Real Docker:**
```bash
# Integration tests with actual Docker
DOCKER_AVAILABLE=1 DOCKER_RUNTIME=real pytest tests/test_docker.py
```
