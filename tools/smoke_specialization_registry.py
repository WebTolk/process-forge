#!/usr/bin/env python3
"""Smoke specialization registry template."""

from __future__ import annotations

from specialization_smoke_helpers import ROOT, read_yaml


def main() -> None:
    data = read_yaml(ROOT / "templates" / "registries" / "specializations.yaml")
    if data.get("schema_version") != 1 or not isinstance(data.get("specializations"), list):
        raise AssertionError("specialization registry template invalid")
    print("PASS: smoke_specialization_registry")


if __name__ == "__main__":
    main()
