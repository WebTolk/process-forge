#!/usr/bin/env python3
"""Focused smoke tests for multiagent assignment scope contracts."""

from __future__ import annotations

import tempfile
from pathlib import Path

import processforge


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(processforge.ensure_trailing_newline(processforge.dump_yaml(data)), encoding="utf-8")


def assert_status(label: str, result: dict, expected: str) -> None:
    actual = result.get("status")
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}: {result}")


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="pf-multiagent-smoke-"))
    (root / ".pf" / "assignments").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "schemas").mkdir()
    (root / ".pf" / "artifacts").mkdir(parents=True)
    (root / "tools" / "processforge.py").write_text("# fixture\n", encoding="utf-8")
    (root / "schemas" / "assignment.schema.json").write_text("{}\n", encoding="utf-8")
    (root / ".pf" / "artifacts" / "shared.md").write_text("# shared\n", encoding="utf-8")
    return root


def smoke_exact_overlap() -> None:
    root = make_root()
    write_yaml(
        root / ".pf" / "assignments" / "task-a.yaml",
        {
            "id": "task-a",
            "title": "Task A",
            "process": "software-feature-development",
            "status": "in_progress",
            "allowed_files": ["Tools/ProcessForge.py"],
            "ownership": {"owner_id": "task-a", "writer": True, "owned_files": ["Tools/ProcessForge.py"], "owned_globs": []},
        },
    )
    result = processforge.validate_assignment_scope_overlaps(root, {"id": "task-b", "allowed_files": ["tools/processforge.py"]})
    assert_status("exact overlap", result, "fail")


def smoke_glob_overlap() -> None:
    root = make_root()
    write_yaml(
        root / ".pf" / "assignments" / "task-a.yaml",
        {
            "id": "task-a",
            "title": "Task A",
            "process": "software-feature-development",
            "status": "in_progress",
            "ownership": {"owner_id": "task-a", "writer": True, "owned_files": [], "owned_globs": ["schemas/*"]},
        },
    )
    result = processforge.validate_assignment_scope_overlaps(root, {"id": "task-b", "allowed_files": ["schemas/assignment.schema.json"]})
    assert_status("glob overlap", result, "fail")


def smoke_shared_read_context_passes() -> None:
    root = make_root()
    write_yaml(
        root / ".pf" / "assignments" / "task-a.yaml",
        {
            "id": "task-a",
            "title": "Task A",
            "process": "software-feature-development",
            "status": "in_progress",
            "context_artifacts": [".pf/artifacts/shared.md"],
            "allowed_read_files": [".pf/artifacts/shared.md"],
        },
    )
    result = processforge.validate_assignment_scope_overlaps(
        root,
        {"id": "task-b", "context_artifacts": [".pf/artifacts/shared.md"], "allowed_read_files": [".pf/artifacts/shared.md"]},
    )
    assert_status("shared read context", result, "pass")


def smoke_forbidden_wins() -> None:
    root = make_root()
    result = processforge.validate_assignment_scope_overlaps(
        root,
        {"id": "task-a", "allowed_files": ["tools/processforge.py"], "forbidden_files": ["tools/*"]},
    )
    assert_status("forbidden wins", result, "fail")
    if not any(str(item.get("reason", "")).startswith("assignment_forbidden_wins") for item in result.get("conflicts", [])):
        raise AssertionError(f"forbidden conflict reason missing: {result}")


def smoke_normalization() -> None:
    root = make_root()
    assignment = root / ".pf" / "assignments" / "task-a.yaml"
    write_yaml(
        assignment,
        {
            "id": "task-a",
            "title": "Task A",
            "process": "software-feature-development",
            "status": "in_progress",
            "context_artifacts": [".pf\\artifacts\\shared.md"],
            "required_outputs": ["changed_files"],
        },
    )
    contract = processforge.normalized_assignment_contract(root, assignment, processforge.load_yaml_document(assignment))
    artifact = contract["context"]["context_artifacts"][0]
    output = contract["outputs"]["required_outputs"][0]
    if artifact["path"] != ".pf/artifacts/shared.md":
        raise AssertionError(f"context artifact did not normalize: {artifact}")
    if output != {"id": "changed_files", "type": "unspecified", "required": True}:
        raise AssertionError(f"required output did not normalize: {output}")


def main() -> int:
    smoke_exact_overlap()
    smoke_glob_overlap()
    smoke_shared_read_context_passes()
    smoke_forbidden_wins()
    smoke_normalization()
    print("PASS: multiagent assignment contract smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
