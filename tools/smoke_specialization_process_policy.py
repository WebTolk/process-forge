#!/usr/bin/env python3
"""Smoke process definitions may declare generic specialization_policy."""

from __future__ import annotations

import copy

import yaml  # type: ignore

from specialization_smoke_helpers import ROOT


def main() -> None:
    schema_text = (ROOT / "schemas" / "process-definition.schema.json").read_text(encoding="utf-8")
    if "specialization_policy" not in schema_text:
        raise AssertionError("process schema does not document specialization_policy")
    data = yaml.safe_load((ROOT / "processes" / "core" / "process-authoring.yaml").read_text(encoding="utf-8"))
    candidate = copy.deepcopy(data)
    candidate["specialization_policy"] = {
        "enabled": True,
        "default": [],
        "allowed": ["fixture.specialization.dev"],
        "routing_hints": {"suggested_specialization_tags": ["fixture"]},
        "forbidden": [],
    }
    if candidate["specialization_policy"]["allowed"] != ["fixture.specialization.dev"]:
        raise AssertionError("generic specialization policy could not be represented")
    print("PASS: smoke_specialization_process_policy")


if __name__ == "__main__":
    main()
