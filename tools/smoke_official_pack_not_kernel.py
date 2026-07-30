#!/usr/bin/env python3
"""Assert official domain process ids are outside the kernel catalog."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_IDS = {
    "software-feature-development",
    "bug-fix",
    "testing",
    "content-production",
    "documentation-mirror-import",
}


def ids_under(root: Path) -> set[str]:
    result: set[str] = set()
    for path in root.glob("**/*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            result.add(str(data["id"]))
    return result


def main() -> None:
    core_ids = ids_under(ROOT / "processes" / "core")
    official_ids = ids_under(ROOT / "packs" / "official")
    assert not core_ids.intersection(OFFICIAL_IDS), sorted(core_ids.intersection(OFFICIAL_IDS))
    assert OFFICIAL_IDS.issubset(official_ids), sorted(OFFICIAL_IDS - official_ids)
    print("PASS: smoke_official_pack_not_kernel")


if __name__ == "__main__":
    main()
