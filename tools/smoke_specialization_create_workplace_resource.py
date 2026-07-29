#!/usr/bin/env python3
"""Smoke specialization-create writes under the workplace."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import require_ok, run_pf, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-create-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        require_ok(run_pf("specialization-create", "--workplace", str(workplace), "--id", "fixture.specialization.dev", "--title", "Fixture Dev", "--apply"))
        expected = workplace / "specializations" / "fixture.specialization.dev.yaml"
        if not expected.is_file():
            raise AssertionError("specialization was not written to workplace specializations/")
        if (root / "specializations").exists():
            raise AssertionError("specialization leaked to distribution-like root")
    print("PASS: smoke_specialization_create_workplace_resource")


if __name__ == "__main__":
    main()
