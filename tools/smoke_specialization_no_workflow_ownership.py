#!/usr/bin/env python3
"""Smoke specialization schema rejects workflow ownership fields."""

from __future__ import annotations

from specialization_smoke_helpers import ROOT, specialization_doc


def main() -> None:
    schema_text = (ROOT / "schemas" / "specialization.schema.json").read_text(encoding="utf-8")
    valid = specialization_doc("fixture.specialization.content", provides_capabilities=["fixture.capability.a"])
    for field in ["stages", "gates", "acceptance", "required_evidence", "artifact_definitions"]:
        if f'"{field}"' in str(valid):
            raise AssertionError(f"specialization fixture owns workflow field: {field}")
        if f'"required": ["{field}"]' not in schema_text:
            raise AssertionError(f"specialization schema does not reject workflow field: {field}")
    template_text = (ROOT / "templates" / "specialization.yaml").read_text(encoding="utf-8")
    for field in ["stages:", "gates:", "acceptance:", "required_evidence:", "artifact_definitions:"]:
        if field in template_text:
            raise AssertionError(f"specialization template includes workflow field: {field}")
    print("PASS: smoke_specialization_no_workflow_ownership")


if __name__ == "__main__":
    main()
