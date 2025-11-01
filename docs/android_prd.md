# Android Stock Evaluator PRD

## 1. Vision
- Deliver a native-quality Android experience for the existing Stock Evaluator web app.
- Empower retail and professional investors to perform rapid, data-driven buy/hold/sell assessments from mobile devices.
- Preserve AI-assisted insights and flowchart visualisation while optimising for mobile usage patterns and offline resilience.

## 2. Target Users & Personas
- **Active Retail Investor** – monitors watchlists daily, wants quick verdicts and risk signals during commutes.
- **Financial Advisor** – uses the tool in client meetings to justify recommendations with clear visuals.
- **Beginner Investor** – explores fundamentals, relies on guidance and educational copy to understand metrics.

## 3. Problem Statement
The current Windows-hosted Flask app is optimised for desktop browsing. Android users lack a tailored experience with native navigation, offline handling, and push-driven re-engagement. Without a mobile channel, adoption and retention remain limited.

## 4. Goals
- Ship an Android app (API 24+) with feature parity for core evaluation, risk and AI opinion modules.
- Ensure sub-4 second perceived load time for ticker evaluations on typical 4G connections.
- Provide offline caching for the most recent 10 tickers and AI reports.
- Integrate secure API key management and user-level configuration.
- Enable push notifications for saved ticker updates (Phase 2).

## 5. Scope (Initial Release)
- Authentication-free single-user experience reusing existing backend logic via hosted API or embedded Python runtime.
- UI screens:
  - Ticker search & evaluation dashboard.
  - Flowchart verdict view with interactive legend.
  - Detailed tabs for metrics, risk assessment, trend, comparative and dividend analysis.
  - AI opinion report viewer with Markdown rendering.
  - Settings (API key entry, data refresh policy, theme, cache reset).
- Local caching of last results, charts and AI narratives.
- Optional dark mode aligned with system theme.
- Error handling for missing metrics, API outages, and AI provider limits.

## 6. Out of Scope (Phase 1)
- User authentication or multi-tenant accounts.
- Portfolio tracking beyond saved tickers list.
- Advanced charting beyond existing flowchart and summary tables.
- In-app purchases or subscription monetisation (evaluate later).
- Real-time streaming data (stick with current snapshot sources).

## 7. Success Metrics
- ≥80% of critical user flows (load ticker, view verdict, open AI report) complete within 5 seconds P95.
- Crash-free sessions ≥ 99.5% during first month.
- ≥60% of beta users rate the app ≥4/5 for usability.
- 1,000+ monthly active users within three months of launch (with marketing support).
- Push opt-in rate ≥40% once notifications ship in Phase 2.

## 8. Dependencies & Assumptions
- Existing Flask logic will be exposed through a REST layer or converted to a Python package consumable via Chaquopy/Beeware/Python-for-Android, subject to feasibility assessment.
- Continued availability of yfinance data endpoints and AI providers (Groq, Gemini) under current rate limits.
- Android team can access Groq/Gemini API keys through secure configuration.
- Design resources available for mobile UX polish and iconography.

## 9. Constraints
- Must comply with Play Store policies for financial apps (disclaimers, data privacy).
- Offline storage limited to ≤25 MB to respect lower-tier devices.
- Data refresh throttled to avoid yfinance rate limiting.
- App must support Android 7.0+ (API level 24) and scale to tablets.

## 10. Release Milestones
- **M0 – Discovery (1.5 wks):** Feasibility spike on Python logic reuse, choose mobile stack, confirm API hosting.
- **M1 – Prototype (3 wks):** Implement core evaluation screen with mocked data, offline cache skeleton, theme baseline.
- **M2 – Feature Complete (4 wks):** Integrate real data, AI opinion fetch, flowchart rendering, settings and error handling.
- **M3 – Beta (2 wks):** QA, instrumentation, beta distribution via Play Console internal testing.
- **Launch:** Play Store production release with marketing assets and support documentation.

## 11. Open Questions
- Should AI opinion generation run client-side via cloud API, or proxied through backend to hide keys?
- Do we ship as a fully native Kotlin app, Flutter app, or hybrid wrapper around enhanced PWA? (Decision captured in solution design.)
- How do we guarantee data compliance across jurisdictions (e.g., EU/UK financial advice disclaimers)?
