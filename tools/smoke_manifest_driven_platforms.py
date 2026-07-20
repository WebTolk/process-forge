#!/usr/bin/env python3
"""Smoke checks for manifest-driven platform resolution."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - release-test environment requires PyYAML.
    yaml = None

from processforge_subprocess import CommandResult, diagnostic_text, format_command, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
DEFAULT_TIMEOUT = 30


def run_cmd(args: list[str], cwd: Path = ROOT, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    command = [sys.executable, str(CLI), *args]
    result = run_processforge_command(command, cwd=cwd, timeout=timeout)
    if result.timed_out:
        print("TIMEOUT: command exceeded timeout")
        print(diagnostic_text(result))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(args)}")
    if result.returncode != expect:
        print("FAIL: unexpected command exit")
        print(f"CMD: {format_command(command)}")
        print(f"EXPECTED_EXIT: {expect}")
        print(diagnostic_text(result))
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(args)}")
    return result


def run(*args: str, cwd: Path = ROOT, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    return run_cmd(list(args), cwd=cwd, expect=expect, timeout=timeout)


def write_yaml(path: Path, data: dict) -> None:
    if yaml is None:
        raise AssertionError("PyYAML is required for smoke_manifest_driven_platforms")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise AssertionError("PyYAML is required for smoke_manifest_driven_platforms")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def bootstrap_workplace(root: Path) -> Path:
    workplace = root / "workplace"
    run("workplace-init", "--workplace", str(workplace), "--apply")
    return workplace


def write_package(workplace: Path, package_id: str, dependencies: list[str] | None = None) -> None:
    package_dir = workplace / "packages" / package_id
    manifest = {
        "schema_version": 1,
        "id": package_id,
        "name": package_id,
        "version": "0.1.0",
        "kind": "documentation",
        "scope": "workplace",
        "dependencies": dependencies or [],
        "resources": [],
    }
    write_yaml(package_dir / "package.yaml", manifest)
    write_yaml(package_dir / "indexes" / "resource-index.yaml", {"schema_version": 1, "package": package_id, "resources": []})


def register_platform(workplace: Path, platform_id: str, contract: dict) -> None:
    path = workplace / "platform-contracts" / platform_id / "platform-contract.yaml"
    write_yaml(path, contract)
    registry = workplace / "registries" / "platforms.yaml"
    data = load_yaml(registry)
    entries = data.get("platforms") if isinstance(data.get("platforms"), list) else []
    entries = [item for item in entries if isinstance(item, dict) and str(item.get("package_id") or item.get("id")) != platform_id]
    entries.append({"id": platform_id.removeprefix("platform."), "package_id": platform_id, "path": f"platform-contracts/{platform_id}/platform-contract.yaml", "status": "available"})
    write_yaml(registry, {"schema_version": 1, "platforms": entries})


def test_manifest_parent_child(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    write_package(workplace, "docs.test-parent")
    write_package(workplace, "docs.test-child", dependencies=["docs.test-parent"])
    register_platform(
        workplace,
        "platform.test-parent",
        {
            "schema_version": 1,
            "id": "platform.test-parent",
            "title": "Test Parent",
            "type": "platform_contract",
            "version": "0.1.0",
            "project_type_hints": ["test-parent-project"],
            "requires": {"knowledge_packages": ["docs.test-parent"]},
            "includes": {"knowledge_packages": [{"id": "docs.test-parent", "required": True, "load_policy": "on_demand"}]},
        },
    )
    register_platform(
        workplace,
        "platform.test-child",
        {
            "schema_version": 1,
            "id": "platform.test-child",
            "title": "Test Child",
            "type": "platform_contract",
            "version": "0.1.0",
            "extends": [{"id": "platform.test-parent", "required": True}],
            "requires": {"platforms": [{"id": "platform.test-parent", "required": True}], "knowledge_packages": ["docs.test-child"]},
            "project_type_hints": ["test-child-project"],
            "includes": {"knowledge_packages": [{"id": "docs.test-child", "required": True, "load_policy": "on_demand"}]},
        },
    )
    run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.test-child")
    project = root / "child-project"
    project.mkdir()
    (project / "README.md").write_text("# Test Child\n", encoding="utf-8")
    run("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "test-child-project", "--apply")
    snapshot = load_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
    stack = [item.get("id") for item in snapshot.get("platform_stack", []) if isinstance(item, dict)]
    if stack != ["platform.test-parent", "platform.test-child"]:
        raise AssertionError(f"unexpected manifest-driven platform_stack: {stack}")
    knowledge = [item.get("id") for item in snapshot.get("knowledge_stack", []) if isinstance(item, dict)]
    for package_id in ["docs.test-parent", "docs.test-child"]:
        if package_id not in knowledge:
            raise AssertionError(f"missing inherited package in knowledge_stack: {package_id}")


def test_manifest_file_detection(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    write_package(workplace, "docs.test-file-detection")
    register_platform(
        workplace,
        "platform.test-file-detection",
        {
            "schema_version": 1,
            "id": "platform.test-file-detection",
            "title": "Test File Detection",
            "type": "platform_contract",
            "version": "0.1.0",
            "project_type_hints": ["test-file-detection-project"],
            "detection": {"files": {"any": ["processforge-test.project"]}},
            "requires": {"knowledge_packages": ["docs.test-file-detection"]},
            "includes": {"knowledge_packages": [{"id": "docs.test-file-detection", "required": True, "load_policy": "on_demand"}]},
        },
    )
    project = root / "file-detection-project"
    project.mkdir()
    (project / "processforge-test.project").write_text("manifest-driven detection fixture\n", encoding="utf-8")
    run("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    snapshot = load_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
    stack = [item.get("id") for item in snapshot.get("platform_stack", []) if isinstance(item, dict)]
    if "platform.test-file-detection" not in stack:
        raise AssertionError(f"test platform was not detected from manifest rules: {stack}")
    knowledge = [item.get("id") for item in snapshot.get("knowledge_stack", []) if isinstance(item, dict)]
    if "docs.test-file-detection" not in knowledge:
        raise AssertionError(f"test knowledge package missing from knowledge_stack: {knowledge}")


def main() -> int:
    tests = [test_manifest_parent_child, test_manifest_file_detection]
    failures: list[str] = []
    for test in tests:
        print(f"RUN: {test.__name__}")
        with tempfile.TemporaryDirectory(prefix=f"pf-{test.__name__}-") as tmp:
            try:
                test(Path(tmp))
                print(f"PASS: {test.__name__}")
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL: {test.__name__}: {exc}")
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
