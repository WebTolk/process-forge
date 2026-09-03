#!/usr/bin/env python3
"""Guard the host-owned stdio MCP lifecycle contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for rel in ["docs/concepts/runtime-mcp.md", "docs/ru/concepts/runtime-mcp.md"]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for marker in ["stdio", "host-owned" if "/ru/" not in rel else "владеет host", "not registered as a Windows scheduled task" if "/ru/" not in rel else "не регистрируется как Windows scheduled task"]:
            if marker not in text:
                raise AssertionError(f"{rel} missing MCP lifecycle marker: {marker}")
    print("PASS: docs describe MCP as a host-owned stdio process")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
