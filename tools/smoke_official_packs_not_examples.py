#!/usr/bin/env python3
"""Assert production process packs are canonical official distribution data."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "software-development": {"software-feature-development", "bug-fix"},
    "content-workflow": {"content-production", "documentation-mirror-import"},
    "verification": {"testing"},
}


def process_id(path: Path) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return str(data.get("id", "")) if isinstance(data, dict) else ""


def main() -> None:
    official_ids: set[str] = set()
    for pack_name, expected_ids in EXPECTED.items():
        pack_root = ROOT / "packs" / "official" / pack_name
        manifest = yaml.safe_load((pack_root / "package.yaml").read_text(encoding="utf-8"))
        assert manifest["origin"] == "official", manifest
        assert manifest["production_ready"] is True, manifest
        actual_ids = {process_id(path) for path in (pack_root / "processes").glob("*.yaml")}
        assert expected_ids == actual_ids, (pack_name, expected_ids, actual_ids)
        official_ids.update(actual_ids)

    example_ids = {
        process_id(path)
        for path in (ROOT / "examples").glob("**/processes/*.yaml")
        if path.is_file()
    }
    duplicates = sorted((example_ids - {""}).intersection(official_ids))
    assert not duplicates, f"official process ids remain canonical under examples: {duplicates}"
    print("PASS: smoke_official_packs_not_examples")


if __name__ == "__main__":
    main()
