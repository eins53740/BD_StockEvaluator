import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

for path in (SRC_DIR, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
