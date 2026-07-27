#!/usr/bin/env python3
"""Validate software lifecycle agent prompt alignment."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / "prompts" / "software-feature-development-agent.md"


def main() -> int:
    text = PROMPT.read_text(encoding="utf-8").lower()
    assert "lifecycle_mode" in text
    assert "not_applicable" in text
    assert "do not silently skip" in text
    assert "delivery/build profile" in text
    assert "not a separate process" in text
    assert "joomla-plugin-delivery" in text
    assert "evidence" in text
    assert "project-context-check --session-start --json" in text
    print("PASS: software lifecycle prompt alignment smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

