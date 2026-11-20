"""Resolve source packages for independently collected native scan tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for package_root in (ROOT / "src", ROOT / "tools"):
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
