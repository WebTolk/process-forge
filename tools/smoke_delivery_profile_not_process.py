#!/usr/bin/env python3
"""Ensure delivery profiles are modeled as operations, not public core processes."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PROCESS_IDS = {
    "joomla-plugin-delivery",
    "joomla-extension-delivery",
    "component-delivery",
    "plugin-delivery",
}


def main() -> int:
    process_ids: set[str] = set()
    for path in (ROOT / "processes").glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            process_ids.add(str(data["id"]))
    assert not (FORBIDDEN_PROCESS_IDS & process_ids), sorted(FORBIDDEN_PROCESS_IDS & process_ids)
    software_process = (ROOT / "processes" / "software-feature-development.yaml").read_text(encoding="utf-8")
    assert "Joomla" not in software_process
    assert "joomla" not in software_process
    assert "delivery_profile" in software_process
    example = (ROOT / "examples" / "software-project" / "process-forge.yaml").read_text(encoding="utf-8")
    assert "execution_profiles:" in example
    assert "delivery_profiles:" in example
    print("PASS: delivery profile not process smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

