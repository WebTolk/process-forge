#!/usr/bin/env python3
"""Guard Garage-first agent instructions against manual infrastructure work."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    files = [
        ROOT / "templates" / "project-agents-template.md",
        ROOT / "templates" / "global-agents-processforge-section.md",
        ROOT / ".pf" / "AGENTS.md",
        ROOT / "tools" / "processforge.py",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for marker in ["pf.context", "pf.search", "pf.resolve", "pf.work.start"]:
            if marker not in text:
                raise AssertionError(f"{path.relative_to(ROOT)} missing {marker}")
        if "do not install" not in text.lower():
            raise AssertionError(f"{path.relative_to(ROOT)} lacks the infrastructure boundary")
    print("PASS: agent instructions use the high-level Garage path and prohibit manual infrastructure repair")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
