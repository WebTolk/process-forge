#!/usr/bin/env python3
"""Smoke explicit context-resolve specialization output."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-context-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a", package="fixture.docs.child-dev")
        project = write_project(root, workplace)
        resolved = resolve_json(project, workplace, "fixture.specialization.dev")
        if resolved["process"]:
            raise AssertionError("resource-profile-only context should not imply a process")
        if "fixture.tool.a" not in resolved["activated_tools"]:
            raise AssertionError("specialization tool not activated")
        if resolved["conflicts"]:
            raise AssertionError(resolved["conflicts"])
    print("PASS: smoke_specialization_context_resolution")


if __name__ == "__main__":
    main()
