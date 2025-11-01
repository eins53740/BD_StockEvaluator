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

**Watchlist alerts**
- Configure automated alerts for the daily portfolio digest by editing `config/watchlist.json`.
- Each entry defines a `ticker`, notification `channels`, and rule set using dot-delimited paths into the analysis payload (see `bd_stockevaluator/core/watchlist.py` for supported operators).
- The daily report picks up this file automatically; leave it untouched if you prefer to disable alert-based messaging.

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

### Docker Deployment (Recommended for Production)

The easiest way to run the backend is using Docker:

**Prerequisites:**
- Docker and Docker Compose installed

**Quick Start with Docker:**
1.  Copy the environment template and configure your API keys:
    ```bash
    cp .env.example .env
    # Edit .env with your API keys
    ```

2.  Build and run with Docker Compose:
    ```bash
    docker-compose up -d
    ```

3.  Access the API at `http://localhost:8000/health`

**Manual Docker Build:**
```bash
# Build the image
docker build -t bd_stockevaluator:latest .

# Run the container
docker run -d \
  --name stock-evaluator \
  -p 8000:8000 \
  -e GROQ_API_KEY=your_key_here \
  -e FRED_API_KEY=your_key_here \
  -v stock-data:/app/data \
  bd_stockevaluator:latest
```

**Features:**
- Multi-stage build for minimal image size
- Non-root user for enhanced security
- Automatic health checks every 30s
- Persistent data storage with Docker volumes
- Production-ready configuration

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
