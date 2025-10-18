"""
Lightweight parser for API key configuration files.

The historical project shipped a ``Daily Report.py`` script that expected an
``api_keys.txt`` text file with ``key=value`` lines.  The original helper lived
at the project root; the split into a dedicated repository lost that module.
This reimplementation keeps the behaviour relied upon by the existing tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def api_keys_reader(path: str | Path) -> Dict[str, str]:
    """
    Parse ``key=value`` pairs from ``api_keys.txt`` style files.

    Comments (``# ...``) and blank lines are ignored.  Keys that appear without
    a value still get an entry with an empty string so callers can detect the
    presence of a configuration knob.
    """

    file_path = Path(path)
    contents = file_path.read_text(encoding="utf-8")

    keys: Dict[str, str] = {}
    for raw_line in contents.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if not key:
            continue
        keys[key.strip()] = value.strip()

    return keys
