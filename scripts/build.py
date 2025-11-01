import PyInstaller.__main__
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PY = PROJECT_ROOT / "src" / "bd_stockevaluator" / "app.py"
DIST_PATH = PROJECT_ROOT / "dist"
BUILD_PATH = PROJECT_ROOT / "build"
APP_NAME = "StockEvaluator"


def main():
    """Runs PyInstaller to build the executable."""

    pyinstaller_args = [
        str(APP_PY),
        f"--name={APP_NAME}",
        "--onefile",
        "--windowed",
        f"--distpath={DIST_PATH}",
        f"--workpath={BUILD_PATH}",
        # Add any other necessary PyInstaller options here
    ]

    print(f"Running PyInstaller with args: {' '.join(pyinstaller_args)}")

    PyInstaller.__main__.run(pyinstaller_args)


if __name__ == "__main__":
    main()
