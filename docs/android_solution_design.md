# Android Solution Design

## 1. Architectural Overview
- **Tiered Architecture**
  - **Presentation Layer (Android)** – Native Kotlin app using Jetpack Compose, Material 3, MVVM.
  - **Domain Layer** – Use cases coordinating evaluation, caching, analytics, notification scheduling.
  - **Data Layer** – Retrofit-based API client, Room persistence, DataStore for configuration.
  - **Backend Services** – Existing Flask app refactored into REST/JSON endpoints hosted on Azure App Service or AWS Elastic Beanstalk. Background workers handle yfinance requests and AI report generation.
- **API Strategy** – Expose endpoints:
  - `POST /evaluate` → wraps `StockEvaluator.evaluate()` returning verdict, metrics, flowchart data.
  - `GET /features/{ticker}` → returns risk, trend, comparative, dividend analysis.
  - `POST /opinion` → generates AI markdown and returns rendered HTML.
  - `GET /health` → monitoring endpoint.
- **Security & Keys**
  - Backend stores Groq/Gemini API keys; mobile app never embeds them.
  - Requests authenticated via short-lived JWT issued from backend (no user accounts initially; device-level token seeded on first launch).
  - HTTPS enforcement with HSTS and certificate pinning in app.

## 2. Mobile App Modules
- **Core UI Screens**
  - `HomeScreen` – ticker input, quick verdict summary, recent history carousel.
  - `DetailScreen` – tabbed layout (Overview, Flowchart, Metrics, AI Report).
  - `SettingsScreen` – data refresh rules, theme, cache management, legal copy.
  - `SavedTickersScreen` (Phase 2) – manage watchlist and alerts.
- **State Management**
  - Kotlin coroutines with Flow; ViewModels scoped per screen.
  - UI state sealed classes to drive loading/error/success visuals.
- **Navigation**
  - Jetpack Navigation Compose for type-safe routes; arguments for tickers.

## 3. Data Handling
- **Network**
  - Retrofit + OkHttp + Kotlinx Serialization.
  - Interceptors for auth token, connectivity status, logging (debug builds only).
  - Exponential backoff retry for transient 429/5xx responses.
- **Caching**
  - Room database storing Ticker entity, EvaluationResult, AIReport (HTML), timestamp.
  - Repository surfaces `Flow<Resource<T>>` merging local cache with network updates.
  - Offline mode: last known evaluation served immediately; background refresh when connectivity returns (WorkManager).
- **Flowchart Rendering**
  - Backend returns Mermaid definition and derived JSON graph.
  - Android renders via lightweight WebView with pre-bundled Mermaid.js or Compose Canvas fallback (Phase 2).
  - Snapshot HTML cached alongside evaluation for offline display.

## 4. Backend Adaptation Plan
- **Code Refactor**
  - Extract business logic from `app.py`, `evaluator.py`, `features.py` into package `stock_evaluator`.
  - Introduce FastAPI layer (`api.py`) exposing JSON endpoints; reuse cache (TTLCache) to guard yfinance quotas.
  - Add async tasks using Celery/Redis (optional) for AI opinion generation if slow.
- **Deployment**
  - Containerise (Docker) with Gunicorn + Uvicorn workers; host on Azure/AWS.
  - Configure environment secrets (GROQ_API_KEY, GEMINI_API_KEY, SECRET_KEY).
  - Set up monitoring (Prometheus/Grafana or CloudWatch) and log aggregation.

## 5. Offline & Sync Strategy
- **Cold Start**
  - App ships with quickstart banner explaining first load requires internet.
- **Refresh Policy**
  - Default: re-fetch if cached data older than 12 hours (user-adjustable).
  - Manual refresh gesture triggers immediate API calls.
- **Conflict Handling**
  - No user-generated content; latest server response overwrites cache.
- **Push Notifications (Phase 2)**
  - Firebase Cloud Messaging; backend tracks saved tickers and pushes when metrics cross thresholds.

## 6. Observability
- **Mobile**
  - Firebase Crashlytics, Performance Monitoring, custom analytics events: `ticker_search`, `view_flowchart`, `share_report`.
  - Logging via Timber; disable verbose logs in production.
- **Backend**
  - Structured JSON logs, request tracing, rate-limit metrics, AI latency metrics.

## 7. Compliance & DevOps
- **CI/CD**
  - GitHub Actions: Android pipeline (lint, unit tests, instrumentation tests on Firebase Test Lab), backend pipeline (pytest, mypy, docker build).
  - Automated Play Store upload using Gradle Play Publisher to Internal testing track.
- **Privacy & Legal**
  - Present investment disclaimer on first launch + settings.
  - Collect minimal telemetry; honour GDPR, provide privacy policy link.
- **Testing Strategy**
  - Unit tests for ViewModels, repositories, domain use cases.
  - Instrumented UI tests (Compose testing) for critical flows.
  - Contract tests between Android client and backend (MockWebServer).
  - Load testing for backend evaluation endpoint (Locust/Gatling).

## 8. Technology Stack Summary
- **Mobile** – Kotlin, Jetpack Compose, Retrofit/OkHttp, Room, DataStore, Hilt DI.
- **Backend** – Python 3.11, FastAPI, Uvicorn/Gunicorn, yfinance, Celery (optional), Redis (optional), PostgreSQL (for audit logs if needed).
- **Infrastructure** – Docker, Terraform scripts (future) for IaC, Azure App Service or AWS ECS Fargate, CloudFront CDN for static assets, Firebase for push.

## 9. Risks & Mitigations
- **yfinance rate limits** – Backend caching, exponential backoff, consider paid market data APIs for scale.
- **AI provider availability** – Implement provider prioritisation (Groq primary, Gemini fallback) and graceful degradation message.
- **Flowchart rendering performance** – Pre-render HTML on backend, lazy load within Compose to keep frames smooth.
- **Key exposure** – All API keys remain server-side; device tokens only identify installations.

