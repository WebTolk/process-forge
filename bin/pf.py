#!/usr/bin/env python3
"""Cross-platform ProcessForge launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    cli = root / "tools" / "processforge.py"
    if not cli.is_file():
        print(f"FAIL: ProcessForge CLI not found: {cli}", file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, str(cli), *argv])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
