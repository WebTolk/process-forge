#!/usr/bin/env python3
"""Smoke specialization schema and template."""

from __future__ import annotations

from specialization_smoke_helpers import ROOT, require_ok, run_pf


def main() -> None:
    for path in ["schemas/specialization.schema.json", "templates/specialization.yaml"]:
        if not (ROOT / path).is_file():
            raise AssertionError(f"missing {path}")
    require_ok(run_pf("release-test", "--root", str(ROOT), "--only", "schema validation", "--no-clean"))
    print("PASS: smoke_specialization_schema")


if __name__ == "__main__":
    main()
