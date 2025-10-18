# Python to Android Conversion Notes

## Overview
- Core business logic (stock evaluation, AI opinions, flowchart generation) extracted into `core/service.py`.
- FastAPI layer (`api/main.py`) delivers JSON contracts consumed by the Android app.
- Android client uses Kotlin, Jetpack Compose, Retrofit, Room, and Hilt.
- Shared data contracts mirror API responses; Room caches evaluations for offline access.

## Key Steps
1. **Refactor Backend**
   - Modularised Python services for reuse outside Flask.
   - Implemented `/evaluate` and `/features/{ticker}` endpoints.
   - Added containerisation, testing, and CI pipelines.
2. **Mobile Architecture**
   - Created Android module with MVVM + Repository pattern.
   - Retrofit DTOs map to backend responses, converters build domain models.
   - Compose UI renders verdicts, metrics, flowcharts (WebView) and AI reports.
3. **Build & Tooling**
   - Added Gradle wrapper, dependencies, and instructions for local builds.
   - Documented secrets (.env, GitHub) and deployment workflows.

## Build Checklist (Manual)
1. Install Android Studio + SDK command-line tools.
2. Set `JAVA_HOME` (JDK 17+) and ensure `ANDROID_HOME`/`sdk.dir` in `local.properties`.
3. Start backend (`uvicorn api.main:app --reload`) or deploy to staging.
4. From `android-client`, run `./gradlew assembleDebug`.
5. Install APK: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.

## Testing
- Python: `pytest FlowchartStocks/stock-evaluator/tests`.
- Android:
  - `./gradlew testDebugUnitTest` for JVM tests (to add).
  - `./gradlew connectedDebugAndroidTest` (requires emulator/device).

## Deployment Notes
- Backend: push Docker image to AWS ECR via GitHub Actions; deploy on ECS Fargate.
- Android: configure signing + `./gradlew assembleRelease` for Play Store builds.

