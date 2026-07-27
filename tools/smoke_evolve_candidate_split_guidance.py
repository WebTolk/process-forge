#!/usr/bin/env python3
"""Check evolve authoring carries split guidance for mixed observations."""

from __future__ import annotations

from evolve_smoke_helpers import ROOT


def main() -> int:
    files = [
        ROOT / "docs" / "concepts" / "evolve-mechanism.md",
        ROOT / "docs" / "concepts" / "knowledge-candidates.md",
        ROOT / "docs" / "authoring" / "process-authoring.md",
        ROOT / "prompts" / "process-authoring-agent.md",
        ROOT / "templates" / "process-authoring-answers.yaml",
        ROOT / "templates" / "process.yaml",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for needle in ["Split candidates", "narrowest safe scope", "target layer", "process improvement", "delivery-profile"]:
        if needle not in text:
            raise AssertionError(f"missing split guidance: {needle}")

    print("PASS: evolve candidate split guidance smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
