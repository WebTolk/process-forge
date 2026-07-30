#!/usr/bin/env python3
"""Reject example process definitions that shadow official process ids."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def process_definitions(root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in root.glob("**/processes/*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data.get("id"):
            continue
        found.setdefault(str(data["id"]), []).append(path.relative_to(ROOT).as_posix())
    return found


def main() -> None:
    official = process_definitions(ROOT / "packs" / "official")
    examples = process_definitions(ROOT / "examples")
    duplicates = {
        process_id: {"official": official[process_id], "examples": examples[process_id]}
        for process_id in sorted(set(official).intersection(examples))
    }
    assert not duplicates, duplicates
    assert len(official) == sum(len(paths) for paths in official.values()), (
        "duplicate official process ids",
        official,
    )
    print("PASS: smoke_examples_do_not_shadow_official_processes")


if __name__ == "__main__":
    main()
