#!/usr/bin/env python3
"""Check the documented Garage opt-in and organized workplace hook setup."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = {
        "docs/concepts/project-init.md": (
            "`organized`",
            "--repair-action install_codex_hooks",
            "Garage workplace the same integration is optional",
        ),
        "docs/concepts/runtime-mcp.md": (
            "default project mode is `organized`",
            "ordinary project agent must not install hooks",
        ),
        "docs/known-limitations.md": ("Garage collection is optional", "`organized`"),
        "docs/guides/forge-init-hooks.md": (
            "`coordination.default_project_mode`",
            "`.codex/hooks.json`",
            "Garage",
        ),
    }
    for rel, markers in checks.items():
        text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
        for marker in markers:
            if marker not in text:
                raise AssertionError(f"{rel} missing: {marker}")
    print("PASS: docs describe optional Garage hooks and organized workplace setup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
