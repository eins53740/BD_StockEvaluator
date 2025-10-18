# Android Client

Native Android application for the Stock Evaluator backend. Built with Kotlin, Jetpack Compose, Hilt, Retrofit, and Room.

## Features
- MVVM architecture with Repository abstraction over REST API.
- Retrofit DTOs map `/evaluate` data (verdict, metrics, analysis packs).
- Room cache stores the last 20 evaluations for offline quick access.
- Compose UI renders verdict summary, risk/trend/comparative/dividend sections, and embeds Mermaid flowchart + AI opinion via WebViews.

## Prerequisites
- Android Studio (Giraffe+) with Android SDK Platform 34.
- JDK 17 (`JAVA_HOME` must point to it when building from the command line).
- Backend running locally (`uvicorn api.main:app --reload`) or accessible via network.
- `local.properties` with `sdk.dir=<path-to-android-sdk>` (generated automatically by Android Studio).

## Build
```powershell
cd FlowchartStocks/stock-evaluator/android-client
# Windows example assuming JAVA_HOME and sdk.dir are set
./gradlew.bat assembleDebug
```
APK output: `app/build/outputs/apk/debug/app-debug.apk`.

Install on emulator/device:
```powershell
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Testing
```powershell
# JVM unit tests
./gradlew.bat testDebugUnitTest

# Instrumentation tests (requires emulator/device)
./gradlew.bat connectedDebugAndroidTest
```

## Configuration
- Update the backend base URL via `buildConfigField` in `app/build.gradle.kts`.
- Backend secrets live on the server side; ensure `.env` is configured for FastAPI.

Refer to `../docs/api_reference.md` and `../docs/android_project_plan.md` for broader project context.
