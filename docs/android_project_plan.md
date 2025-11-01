# Android Project Plan & Runbook

## 1. Workstreams
- **Backend Enablement** – Extract Python business logic, build REST API, deploy infrastructure.
- **Android Client** – Kotlin app development, UI/UX, offline cache, integrations.
- **AI & Data Services** – Groq/Gemini orchestration, yfinance rate management, caching strategy.
- **Quality & Compliance** – Testing, observability, legal, release management.

## 2. Implementation Roadmap (12 Weeks)
| Sprint | Duration | Objectives | Key Deliverables |
| --- | --- | --- | --- |
| 0 – Discovery | 1.5 wks | Architecture spike, stack selection, data contract draft | Proof-of-concept Compose UI with mocked data, API contract docs |
| 1 – Backend Foundations | 2 wks | Refactor Flask logic, FastAPI skeleton, auth token service | `/evaluate` + `/features` endpoints, Dockerfile, CI pipeline draft |
| 2 – Android Foundations | 2 wks | App shell, navigation, dependency injection, basic UI | Compose screens (Home, Detail skeleton), Retrofit/Room scaffolding |
| 3 – Data Integration | 2 wks | Connect to backend, implement repositories, caching | Functional evaluation flow end-to-end, cached history list |
| 4 – Advanced Features | 2 wks | Flowchart rendering, AI opinion viewer, settings | Flowchart WebView, AI markdown rendering, preferences screen |
| 5 – Polish & Offline | 1.5 wks | Offline mode, error states, accessibility, analytics | WorkManager refresh, Crashlytics, instrumentation tests |
| 6 – Beta & Launch | 1 wk | QA, beta rollout, release assets | Internal test on Play Console, privacy policy, release checklist |

## 3. Backlog Breakdown
- **Backend (Priority)**
  - Package `stock_evaluator` with pure business logic.
  - Implement FastAPI endpoints + Pydantic schemas.
  - Integrate caching, rate limiting, logging, OpenAPI docs.
  - Deploy staging environment, set up CI/CD.
- **Android**
  - Project bootstrap (Gradle, Hilt, Retrofit, Room modules).
  - Compose UI for each screen; responsive design guidelines.
  - Repository and use case layers with unit coverage.
  - Offline cache policies, WorkManager background sync.
  - Flowchart WebView module with secure local HTML loading.
- **Observability & Ops**
  - Implement Firebase Crashlytics, analytics events.
  - Backend monitoring dashboards, alerting thresholds.
  - Release checklist, runbooks for incident handling.

## 4. Environments & Tooling
- **Backend** – Dev (local Docker), Staging (cloud), Prod (cloud).
- **Mobile Builds** – Dev (debug), QA (internal testing), Beta (closed testing), Prod (play store).
- **Toolchain** – Android Studio Giraffe+, Python 3.11, Poetry/pip-tools, GitHub Actions, Docker, Postman, Firebase.

## 5. Testing Strategy (Extended)
- **Backend**
  - Unit tests for evaluation logic and feature modules.
  - Contract tests validating JSON schema compatibility with mobile clients.
  - Integration tests with yfinance mock/stub to avoid live calls.
  - Load testing (baseline 50 RPS) pre-launch.
- **Android**
  - Unit tests (JUnit, Mockito, Turbine) for ViewModels and repositories.
  - UI tests (Compose Test) for primary screens and dark mode.
  - End-to-end tests using MockWebServer & Espresso for critical flows.
  - Beta telemetry monitoring for crash-free sessions.
- **Acceptance Criteria**
  - All critical test suites automated in CI; minimum 80% coverage on domain modules.
  - Manual exploratory testing across form factors (phone + tablet, light/dark).

## 6. Risk Register (Expanded)
- **R1 – Backend latency** → Mitigation: async I/O, caching, prefetch trending tickers.
- **R2 – App store rejection (financial advice)** → Mitigation: clear disclaimers, legal review, region-restricted rollout if needed.
- **R3 – Mermaid rendering in WebView** → Mitigation: pre-render sanitized HTML on backend; fallback static image.
- **R4 – API downtime** → Mitigation: health checks, auto-restart policies, status page, offline cache messaging.
- **R5 – Timeline slippage** → Mitigation: weekly burndown reviews, cross-functional standups, adjustable scope for Phase 1.

## 7. Documentation & Communication
- Maintain central Confluence/Notion space linking PRD, Solution Design, API schemas, test reports.
- Weekly status reports summarising progress, blockers, risks.
- Runbook updates for deployment, incident response, API key rotation.

## 8. Next Step Checklist
1. Approve PRD and Solution Design (stakeholder sign-off).
2. Decide backend hosting platform and budget.
3. Create backlog tickets aligned with sprint plan.
4. Stand up repo structure (Android + backend) and CI skeleton.
5. Schedule design reviews for mobile UX mockups.
