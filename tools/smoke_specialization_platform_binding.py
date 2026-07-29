#!/usr/bin/env python3
"""Smoke platform-specific specialization bindings."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_project, write_specialization, write_workspace


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-spec-binding-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        write_specialization(workplace, "fixture.specialization.dev", tool="fixture.tool.a", package="fixture.docs.child-dev", platform="fixture.platform.child")
        write_specialization(workplace, "fixture.specialization.content", tool="fixture.tool.b", package="fixture.docs.child-content", platform="fixture.platform.child")
        write_specialization(workplace, "fixture.specialization.dev-other", tool="fixture.tool.b", package="fixture.docs.child-content", platform="fixture.platform.test")
        project = write_project(root, workplace)
        dev = resolve_json(project, workplace, "fixture.specialization.dev")
        content = resolve_json(project, workplace, "fixture.specialization.content")
        other = resolve_json(project, workplace, "fixture.specialization.dev-other", platform="fixture.platform.test")
        if "fixture.docs.child-dev" not in dev["activated_knowledge_packages"]:
            raise AssertionError("dev binding did not activate child-dev package")
        if "fixture.docs.child-content" not in content["activated_knowledge_packages"]:
            raise AssertionError("content binding did not activate child-content package")
        if "fixture.docs.child-content" not in other["activated_knowledge_packages"]:
            raise AssertionError("same specialization family did not vary by platform")
    print("PASS: smoke_specialization_platform_binding")


if __name__ == "__main__":
    main()
