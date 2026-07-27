#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

import yaml  # type: ignore

from context_lock_smoke_helpers import make_assignment, make_project, refresh, require_ok, run_pf, snapshot, write_package


def read_capsule(project: Path, name: str) -> dict:
    return yaml.safe_load((project / ".pf" / "contexts" / "assignment-capsules" / f"{name}.capsule.yaml").read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-capsule-pins-") as raw:
        project = make_project(Path(raw))
        refresh(project)
        snapshot_a = snapshot(project)["snapshot"]["id"]
        assignment_a = make_assignment(project, "task-a")
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(assignment_a)))
        capsule_a = read_capsule(project, "task-a")
        write_package(project, core_versions=["5.4.5", "6.1.2"], articles_generation="A")
        refresh(project)
        snapshot_b = snapshot(project)["snapshot"]["id"]
        assert snapshot_a != snapshot_b
        assert read_capsule(project, "task-a")["context_snapshot"]["id"] == snapshot_a
        assignment_b = make_assignment(project, "task-b")
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(assignment_b)))
        assert read_capsule(project, "task-b")["context_snapshot"]["id"] == snapshot_b
        require_ok(run_pf("capsule-doctor", "--project-root", str(project), "--capsule", str(project / ".pf" / "contexts" / "assignment-capsules" / "task-a.capsule.yaml")))
    print("PASS: capsule pins context snapshot smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
