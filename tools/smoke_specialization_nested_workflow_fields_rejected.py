#!/usr/bin/env python3
"""Smoke specialization schema rejects workflow fields in nested objects."""

from __future__ import annotations

import copy
import importlib.util
import json

from specialization_smoke_helpers import ROOT, specialization_doc


SCHEMA = json.loads((ROOT / "schemas" / "specialization.schema.json").read_text(encoding="utf-8"))
VALIDATOR_PATH = ROOT / "tools" / "validate-process-forge-schemas.py"
SPEC = importlib.util.spec_from_file_location("pf_schema_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("schema validator unavailable")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def expect_invalid(document: dict, label: str) -> None:
    errors = VALIDATOR.validate_instance(document, SCHEMA, SCHEMA, "$")
    if not errors:
        raise AssertionError(f"{label} was accepted")


def main() -> None:
    valid = specialization_doc("fixture.specialization.a", provides_capabilities=["fixture.capability.a"])
    errors = VALIDATOR.validate_instance(valid, SCHEMA, SCHEMA, "$")
    if errors:
        raise AssertionError(errors[0])

    top = copy.deepcopy(valid)
    top["stages"] = [{"id": "bad"}]
    expect_invalid(top, "top-level stages")

    binding = copy.deepcopy(valid)
    binding["platform_bindings"][0]["stages"] = [{"id": "bad"}]
    expect_invalid(binding, "platform binding stages")

    resources = copy.deepcopy(valid)
    resources["resources"]["requires"]["stages"] = [{"id": "bad"}]
    expect_invalid(resources, "resources.requires.stages")
    print("PASS: smoke_specialization_nested_workflow_fields_rejected")


if __name__ == "__main__":
    main()
