#!/usr/bin/env python3
"""Smoke checks for platform inheritance and provider-scoped knowledge packages."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - release-test environment requires PyYAML.
    yaml = None

ROOT = Path(os.environ.get("PF_REPO_ROOT", Path(__file__).resolve().parents[4])).resolve()
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from processforge_subprocess import CommandResult, diagnostic_text, format_command, run_command as run_processforge_command

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


def command_output(result: CommandResult) -> str:
    return result.stdout + result.stderr


def write_yaml(path: Path, data: dict) -> None:
    if yaml is None:
        raise AssertionError("PyYAML is required for smoke_platform_inheritance")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise AssertionError("PyYAML is required for smoke_platform_inheritance")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def bootstrap_workplace(root: Path) -> Path:
    workplace = root / "workplace"
    run("workplace-init", "--workplace", str(workplace), "--apply")
    local_docs = workplace / "local-docs"
    local_docs.mkdir()
    write_yaml(
        workplace / "registries" / "knowledge-roots.yaml",
        {
            "schema_version": 1,
            "knowledge_roots": [
                {"id": "local-docs", "label": "Local documentation root", "path": "local-docs"},
            ],
        },
    )
    return workplace


def write_package(workplace: Path, package_id: str, resources: list[dict] | None = None, dependencies: list[str] | None = None, navigation: dict | None = None) -> None:
    package_dir = workplace / "packages" / package_id
    manifest = {
        "schema_version": 1,
        "id": package_id,
        "name": package_id,
        "version": "0.1.0",
        "kind": "documentation",
        "scope": "workplace",
        "dependencies": dependencies or [],
        "navigation": navigation or {"documentation": {"resource": package_id.replace(".", "-")}},
        "resources": resources
        or [
            {
                "id": package_id.replace(".", "-"),
                "kind": "documentation",
                "title": package_id,
                "path_ref": {"registry": "knowledge_roots", "id": "local-docs", "relative_path": package_id.replace(".", "/")},
                "load_policy": "on_demand",
            }
        ],
    }
    write_yaml(package_dir / "package.yaml", manifest)
    write_yaml(package_dir / "indexes" / "resource-index.yaml", {"schema_version": 1, "package": package_id, "resources": manifest["resources"]})


def register_platform(workplace: Path, platform_id: str, contract: dict) -> None:
    path = workplace / "platform-contracts" / platform_id / "platform-contract.yaml"
    write_yaml(path, contract)
    registry = workplace / "registries" / "platforms.yaml"
    data = load_yaml(registry)
    entries = data.get("platforms") if isinstance(data.get("platforms"), list) else []
    entries = [item for item in entries if isinstance(item, dict) and str(item.get("id")) != platform_id.removeprefix("platform.")]
    entries.append({"id": platform_id.removeprefix("platform."), "package_id": platform_id, "path": f"platform-contracts/{platform_id}/platform-contract.yaml", "status": "available"})
    write_yaml(registry, {"schema_version": 1, "platforms": entries})


def create_platforms(workplace: Path) -> None:
    register_platform(
        workplace,
        "platform.example-parent",
        {
            "schema_version": 1,
            "id": "platform.example-parent",
            "title": "Example Parent Platform",
            "type": "platform_contract",
            "version": "0.1.0",
            "project_type_hints": ["example-parent-project"],
            "capabilities": ["php", "html", "css", "javascript", "web.accessibility", "web.performance", "filesystem.read", "filesystem.write"],
            "requires": {"capabilities": ["filesystem.read"], "knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
            "includes": {
                "knowledge_packages": [
                    {"id": "docs.php", "required": True, "load_policy": "on_demand"},
                    {"id": "docs.web.html", "required": True, "load_policy": "on_demand"},
                    {"id": "docs.web.css", "required": False, "load_policy": "on_demand"},
                    {"id": "docs.web.javascript", "required": False, "load_policy": "on_demand"},
                    {"id": "docs.web.accessibility", "required": False, "load_policy": "on_demand"},
                    {"id": "docs.web.performance", "required": False, "load_policy": "on_demand"},
                    {"id": "docs.example-parent", "required": True, "load_policy": "on_demand"},
                ],
                "templates": [],
                "tools": [],
                "mcp": [],
                "processes": [],
            },
        },
    )
    register_platform(
        workplace,
        "platform.example-child",
        {
            "schema_version": 1,
            "id": "platform.example-child",
            "title": "Example Child Platform",
            "type": "platform_contract",
            "version": "0.1.0",
            "extends": [{"id": "platform.example-parent", "required": True}],
            "project_type_hints": ["example-child-project"],
            "requires": {"platforms": [{"id": "platform.example-parent", "required": True}], "capabilities": ["filesystem.read"], "knowledge_packages": ["docs.example-child"], "tools": [], "mcp": [], "templates": []},
            "includes": {"knowledge_packages": [], "templates": [], "tools": [], "mcp": [], "processes": []},
        },
    )


def assert_no_private_paths(paths: list[Path]) -> None:
    for path in paths:
        if ":\\" in path.read_text(encoding="utf-8", errors="replace"):
            raise AssertionError(f"private Windows path leaked into public YAML: {path}")


def test_positive_inheritance(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    for package_id in [
        "docs.php",
        "docs.web.html",
        "docs.web.css",
        "docs.web.javascript",
        "docs.web.accessibility",
        "docs.web.performance",
    ]:
        write_package(workplace, package_id)
    write_package(workplace, "docs.example-parent")
    write_package(workplace, "docs.example-child", dependencies=["docs.example-parent"])
    create_platforms(workplace)
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.php")
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.web.html")
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.example-parent")
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.example-child")
    doctor = run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.example-child")
    if "resolved platform stack written" not in command_output(doctor):
        raise AssertionError("platform-contract-doctor did not write stack report")
    project = root / "child-project"
    project.mkdir()
    (project / "README.md").write_text("# Child Project\n", encoding="utf-8")
    run("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "example-child-project", "--apply")
    snapshot = load_yaml(project / ".pf" / "contexts" / "project-context.snapshot.yaml")
    stack = [item["id"] for item in snapshot.get("platform_stack", [])]
    if stack != ["platform.example-parent", "platform.example-child"]:
        raise AssertionError(f"unexpected platform_stack: {stack}")
    knowledge = {item["id"] for item in snapshot.get("knowledge_stack", []) if isinstance(item, dict)}
    expected_knowledge = {
        "docs.php",
        "docs.web.html",
        "docs.web.css",
        "docs.web.javascript",
        "docs.web.accessibility",
        "docs.web.performance",
        "docs.example-parent",
        "docs.example-child",
    }
    if not expected_knowledge.issubset(knowledge):
        raise AssertionError(f"inherited knowledge packages missing: {knowledge}")
    public_paths = [
        workplace / "packages" / "docs.example-parent" / "package.yaml",
        workplace / "packages" / "docs.example-parent" / "indexes" / "resource-index.yaml",
        workplace / "packages" / "docs.php" / "package.yaml",
        workplace / "packages" / "docs.web.html" / "package.yaml",
        workplace / "packages" / "docs.example-child" / "package.yaml",
        workplace / "packages" / "docs.example-child" / "indexes" / "resource-index.yaml",
        workplace / "platform-contracts" / "platform.example-parent" / "platform-contract.yaml",
        workplace / "platform-contracts" / "platform.example-child" / "platform-contract.yaml",
        project / ".pf" / "process-forge.yaml",
        project / ".pf" / "contexts" / "project-context.snapshot.yaml",
    ]
    assert_no_private_paths(public_paths)


def test_missing_parent_fails(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    write_package(workplace, "docs.child")
    register_platform(
        workplace,
        "platform.child",
        {
            "schema_version": 1,
            "id": "platform.child",
            "type": "platform_contract",
            "version": "0.1.0",
            "extends": [{"id": "platform.missing", "required": True}],
            "requires": {"knowledge_packages": ["docs.child"]},
            "includes": {},
        },
    )
    result = run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.child", expect=1)
    if "required platform available: platform.missing" not in command_output(result):
        raise AssertionError("missing parent platform did not fail")


def test_circular_extends_fails(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    write_package(workplace, "docs.a")
    register_platform(workplace, "platform.a", {"schema_version": 1, "id": "platform.a", "type": "platform_contract", "version": "0.1.0", "extends": ["platform.b"], "requires": {"knowledge_packages": ["docs.a"]}, "includes": {}})
    register_platform(workplace, "platform.b", {"schema_version": 1, "id": "platform.b", "type": "platform_contract", "version": "0.1.0", "extends": ["platform.a"], "requires": {"knowledge_packages": []}, "includes": {}})
    result = run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.a", expect=1)
    if "circular platform inheritance detected" not in command_output(result):
        raise AssertionError("circular extends did not fail")


def test_missing_required_package_dependency_fails(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    write_package(workplace, "docs.child", dependencies=["docs.missing-parent"])
    register_platform(
        workplace,
        "platform.child",
        {
            "schema_version": 1,
            "id": "platform.child",
            "type": "platform_contract",
            "version": "0.1.0",
            "requires": {"knowledge_packages": ["docs.child"]},
            "includes": {},
        },
    )
    result = run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.child", expect=1)
    if "required knowledge_package available through resolved platform stack: docs.missing-parent" not in command_output(result):
        raise AssertionError("missing package dependency did not fail")


def test_no_builtin_platform_registry(root: Path) -> None:
    text = (ROOT / "tools" / "processforge.py").read_text(encoding="utf-8", errors="replace")
    if "BUILTIN_PLATFORM_CONTRACTS" in text or "BASE_TECHNOLOGY_PLATFORM_IDS" in text:
        raise AssertionError("platform hardcode constants remain in core")


def test_private_path_and_api_naming_fail(root: Path) -> None:
    workplace = bootstrap_workplace(root)
    private_path = "D:" + "\\private\\docs"
    write_package(workplace, "private.docs", resources=[{"id": "bad", "kind": "documentation", "title": "Bad", "path": private_path, "load_policy": "on_demand"}])
    result = run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "private.docs", expect=1)
    if "has no private absolute paths" not in command_output(result):
        raise AssertionError("private absolute path did not fail")
    write_package(workplace, "docs.api")
    api_result = run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.api", expect=1)
    if "API package uses provider-specific id" not in command_output(api_result):
        raise AssertionError("generic docs.api did not fail")
    write_package(workplace, "docs.api.example-provider")
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.api.example-provider")


def main() -> int:
    tests = [
        test_positive_inheritance,
        test_missing_parent_fails,
        test_circular_extends_fails,
        test_missing_required_package_dependency_fails,
        test_no_builtin_platform_registry,
        test_private_path_and_api_naming_fail,
    ]
    failures: list[str] = []
    for test in tests:
        with tempfile.TemporaryDirectory(prefix=f"pf-{test.__name__}-") as temp:
            print(f"RUN: {test.__name__}")
            try:
                test(Path(temp))
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL: {test.__name__}: {exc}")
            else:
                print(f"PASS: {test.__name__}")
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
