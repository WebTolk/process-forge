#!/usr/bin/env python3
"""Smoke same platform resolves differently for different specializations."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-same-platform-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a")
        write_specialization(workplace, "fixture.specialization.audit", tool="fixture.tool.b")
        project = write_project(root, workplace)
        dev = resolve_json(project, workplace, "fixture.specialization.dev")
        audit = resolve_json(project, workplace, "fixture.specialization.audit")
        if dev["activated_tools"] == audit["activated_tools"]:
            raise AssertionError("same platform produced identical specialization tool context")
    print("PASS: smoke_specialization_same_platform_different_context")


if __name__ == "__main__":
    main()
