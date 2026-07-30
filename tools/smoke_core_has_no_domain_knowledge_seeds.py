#!/usr/bin/env python3
"""Smoke that core knowledge seeds are fixture-only and domain-neutral."""

from pathlib import Path

from smoke_domain_neutral_core_helpers import ROOT


def main() -> None:
    seed_root = ROOT / "seeds" / "knowledge-packages"
    forbidden = {
        "docs.php.yaml",
        "docs.web.html.yaml",
        "docs.web.css.yaml",
        "docs.web.javascript.yaml",
        "docs.web.performance.yaml",
        "docs.web.accessibility.yaml",
    }
    present = {path.name for path in seed_root.glob("*.yaml")}
    if present.intersection(forbidden):
        raise AssertionError(f"domain seeds remain in core: {sorted(present.intersection(forbidden))}")
    moved_root = ROOT / "packs" / "official" / "software-development" / "knowledge-packages"
    missing = [name for name in forbidden if not (moved_root / name).is_file()]
    if missing:
        raise AssertionError(f"official pack knowledge declarations missing: {sorted(missing)}")
    for path in seed_root.glob("*.yaml"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "id: docs.example-" not in text:
            raise AssertionError(f"non-fixture core seed: {path.relative_to(ROOT)}")
    print("PASS: smoke_core_has_no_domain_knowledge_seeds")


if __name__ == "__main__":
    main()
