#!/usr/bin/env python3
"""Smoke specialization tools do not leak across roles."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-tools-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a")
        write_specialization(workplace, "fixture.specialization.content", package="fixture.docs.child-content")
        write_specialization(workplace, "fixture.specialization.audit", tool="fixture.tool.b")
        project = write_project(root, workplace)
        dev = resolve_json(project, workplace, "fixture.specialization.dev")
        content = resolve_json(project, workplace, "fixture.specialization.content")
        audit = resolve_json(project, workplace, "fixture.specialization.audit")
        if "fixture.tool.a" in content["activated_tools"]:
            raise AssertionError("content specialization leaked fixture.tool.a")
        if "fixture.tool.b" in dev["activated_tools"]:
            raise AssertionError("dev specialization leaked fixture.tool.b")
        if "fixture.tool.b" not in audit["activated_tools"]:
            raise AssertionError("audit specialization did not activate fixture.tool.b")
    print("PASS: smoke_specialization_no_tool_leakage")


if __name__ == "__main__":
    main()
