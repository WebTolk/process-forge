"""The fixed, trusted workload used only by the disposable upgrade broker."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    report = Path(sys.argv[1])
    if not report.is_absolute() or not report.is_relative_to(Path.cwd()):
        return 2
    if report.relative_to(Path.cwd()).as_posix() not in {
        ".pf/artifacts/controlled/report.md",
        ".pf/artifacts/controlled-old/report.md",
    }:
        return 2
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("Controlled worker completed.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
