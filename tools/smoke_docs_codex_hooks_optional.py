#!/usr/bin/env python3
"""Guard documentation and behavior that keep Codex hooks optional."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = {
        "docs/concepts/project-init.md": ["Codex hooks are an optional", "does not install Codex hooks"],
        "docs/concepts/runtime-mcp.md": ["Codex hook telemetry is an optional", "ordinary project agent must not install hooks"],
        "docs/known-limitations.md": ["Codex hooks are optional"],
    }
    for rel, markers in checks.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                raise AssertionError(f"{rel} missing: {marker}")
    print("PASS: docs consistently treat Codex hooks as optional host telemetry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
