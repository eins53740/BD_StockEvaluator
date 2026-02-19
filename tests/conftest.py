import os
import sys
from pathlib import Path

# Ensure test-safe defaults for environment variables that gate production checks.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("FLASK_DEBUG", "1")

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

for path in (SRC_DIR, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
