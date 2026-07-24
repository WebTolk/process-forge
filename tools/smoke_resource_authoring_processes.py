#!/usr/bin/env python3
"""Smoke checks for ProcessForge resource authoring processes."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, format_command, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"
DEFAULT_TIMEOUT = 30


def run_cmd(args: list[str], cwd: Path = ROOT, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    command = [sys.executable, str(CLI), *args]
    started = time.perf_counter()
    print(f"  RUN CMD: {format_command(command)}", flush=True)
    result = run_processforge_command(command, cwd=cwd, timeout=timeout)
    elapsed = time.perf_counter() - started
    print(f"  END CMD: exit={result.returncode} elapsed={elapsed:.2f}s timeout={timeout}s", flush=True)
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


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, *markers: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        if marker not in text:
            raise AssertionError(f"missing marker {marker!r} in {path}")


def assert_no_ps1(root: Path) -> None:
    forbidden_suffix = "." + "ps1"
    matches = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == forbidden_suffix]
    if matches:
        raise AssertionError("unexpected ps1 file: " + str(matches[0]))


def run(*args: str, cwd: Path = ROOT, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    return run_cmd(list(args), cwd=cwd, expect=expect, timeout=timeout)


def command_output(result: CommandResult) -> str:
    return result.stdout + result.stderr


def create_workplace_with_template_and_package(root: Path) -> tuple[Path, Path]:
    workplace = root / "workplace"
    run("workplace-init", "--workplace", str(workplace), "--apply")
    run(
        "template-create",
        "--workplace",
        str(workplace),
        "--id",
        "report.audit.basic",
        "--title",
        "Basic Audit Report",
        "--apply",
    )
    run("template-doctor", "--workplace", str(workplace), "--template", "report.audit.basic")
    run(
        "knowledge-package-create",
        "--workplace",
        str(workplace),
        "--id",
        "docs.example",
        "--title",
        "Example Documentation",
        "--package-root",
        "global",
        "--apply",
    )
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.example", "--package-root", "global")
    return root, workplace


def test_full_chain(root: Path) -> None:
    _root, workplace = create_workplace_with_template_and_package(root)
    project = root / "example-project"
    project.mkdir()
    (project / "README.md").write_text("# Example Project Smoke\n", encoding="utf-8")

    run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "platform.example",
        "--title",
        "Example Platform",
        "--project-type",
        "example-project",
        "--knowledge-package",
        "docs.example",
        "--template",
        "report.audit.basic",
        "--apply",
    )
    run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.example")
    run(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "example-project",
        "--apply",
    )
    run("project-context-refresh", "--project-root", str(project))
    snapshot = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
    assert_file(snapshot)
    assert_contains(snapshot, "platform.example", "docs.example", "report.audit.basic")

    run("hooks-dispatch", "--project-root", str(project), "--event-type", "template.authoring.completed", "--outbox")
    outbox = project / ".pf" / "runtime" / "hooks" / "outbox"
    if not any(outbox.rglob("*.json")):
        raise AssertionError("hooks-dispatch did not write an authoring outbox payload")

    events = workplace / "runtime" / "events" / "events.ndjson"
    assert_contains(
        events,
        "template.authoring.started",
        "template.created",
        "knowledge_package.created",
        "platform.contract.created",
        "platform.contract.linked",
        "platform.authoring.completed",
    )
    for path in [
        workplace / "reusable-templates" / "report.audit.basic" / "template.yaml",
        workplace / "packages" / "docs.example" / "package.yaml",
        workplace / "platform-contracts" / "platform.example" / "platform-contract.yaml",
    ]:
        assert_file(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        if ":\\\\" in text:
            raise AssertionError(f"public authoring artifact contains Windows absolute path marker: {path}")
    assert_no_ps1(workplace)
    assert_no_ps1(project)


def test_negative_duplicate_template(root: Path) -> None:
    _root, workplace = create_workplace_with_template_and_package(root)
    run(
        "template-create",
        "--workplace",
        str(workplace),
        "--id",
        "report.audit.basic",
        "--title",
        "Duplicate Audit Report",
        "--apply",
        expect=1,
    )


def test_negative_missing_package_root(root: Path) -> None:
    workplace = root / "workplace"
    run("workplace-init", "--workplace", str(workplace), "--apply")
    run(
        "knowledge-package-create",
        "--workplace",
        str(workplace),
        "--id",
        "docs.bad.root",
        "--title",
        "Bad Root",
        "--package-root",
        "missing-root",
        "--apply",
        expect=1,
    )


def test_negative_missing_required_platform_package(root: Path) -> None:
    workplace = root / "workplace"
    run("workplace-init", "--workplace", str(workplace), "--apply")
    broken_contract = workplace / "platform-contracts" / "platform.broken" / "platform-contract.yaml"
    broken_contract.parent.mkdir(parents=True, exist_ok=True)
    broken_contract.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "id: platform.broken",
                "title: Broken Platform",
                "project_type_hints: [broken-project]",
                "requires:",
                "  capabilities: [filesystem.read]",
                "  knowledge_packages: [docs.required.missing]",
                "  templates: [template.required.missing]",
                "includes:",
                "  knowledge_packages: []",
                "  templates: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    platforms_registry = workplace / "registries" / "platforms.yaml"
    platforms_registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "platforms:",
                "  - id: broken",
                "    package_id: platform.broken",
                "    path: platform-contracts/platform.broken/platform-contract.yaml",
                "    status: available",
                "",
            ]
        ),
        encoding="utf-8",
    )
    broken = run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.broken", expect=1)
    broken_output = command_output(broken)
    if "FAIL: required knowledge package available: docs.required.missing" not in broken_output:
        raise AssertionError("missing required knowledge package did not fail")
    if "FAIL: required template available: template.required.missing" not in broken_output:
        raise AssertionError("missing required template did not fail")


def test_optional_platform_resource_warns(root: Path) -> None:
    _root, workplace = create_workplace_with_template_and_package(root)
    optional = run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "platform.optional",
        "--title",
        "Optional Missing Platform",
        "--knowledge-package",
        "docs.optional.missing",
        "--apply",
    )
    if "WARN: optional knowledge package available: docs.optional.missing" not in command_output(optional):
        raise AssertionError("optional missing knowledge package did not warn")


def test_no_powershell(root: Path) -> None:
    for path in [ROOT / "templates", ROOT / "examples", ROOT / "docs", ROOT / "bin", ROOT / "tools"]:
        if path.is_dir():
            assert_no_ps1(path)


def main() -> int:
    tests = [
        test_full_chain,
        test_negative_duplicate_template,
        test_negative_missing_package_root,
        test_negative_missing_required_platform_package,
        test_optional_platform_resource_warns,
        test_no_powershell,
    ]
    failures: list[str] = []
    for test in tests:
        with tempfile.TemporaryDirectory(prefix=f"pf-{test.__name__}-") as temp:
            test_started = time.perf_counter()
            print(f"RUN: {test.__name__} temp={temp}", flush=True)
            try:
                test(Path(temp))
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL: {test.__name__}: {exc} elapsed={time.perf_counter() - test_started:.2f}s temp={temp}", flush=True)
            else:
                print(f"PASS: {test.__name__} elapsed={time.perf_counter() - test_started:.2f}s", flush=True)
    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
