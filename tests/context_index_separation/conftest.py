"""Make source and CLI packages importable for registered pytest collection."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for source_directory in (PROJECT_ROOT / "tools", PROJECT_ROOT / "src"):
    source_path = str(source_directory)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
