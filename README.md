# Stock Evaluator

This project is a full-stack stock evaluation tool with a Python backend and a native Android client.

- **Backend:** A powerful Python application using FastAPI and Flask to provide stock analysis, risk assessment, trend analysis, and more. It features dynamic flowchart visualizations of the evaluation process.
- **Android Client:** A native Android application built with Kotlin, Jetpack Compose, and MVVM architecture to consume the backend API and display stock evaluations on a mobile device.

## Project Structure

- `src/bd_stockevaluator`: The Python backend source code.
- `android-client`: The Android client source code.
- `docs`: Project documentation.

## Getting Started

### Backend (Python)

The backend provides a web UI and a REST API.

**For detailed instructions on setup, usage, and customization, see [QUICK_START.md](QUICK_START.md).**

**Quick steps:**
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the Web UI (Flask):
    ```bash
    python src/bd_stockevaluator/app.py
    ```
3.  Run the REST API (FastAPI):
    ```bash
    uvicorn src.bd_stockevaluator.api.main:app --reload
    ```

### Android Client

The Android client provides a native mobile experience for stock evaluation.

**For detailed instructions on building and testing the Android app, see [android-client/README.md](android-client/README.md).**

**Prerequisites:**
- Android Studio (Giraffe+)
- JDK 17
- Backend running locally.

**Build:**
```powershell
cd android-client
./gradlew.bat assembleDebug
```

## Dependencies

Python dependencies are managed using `pyproject.toml`. For development, install the optional dependencies:
```bash
pip install -e .[dev]
```
