#!/usr/bin/env python3
"""Smoke checks for ProcessForge resource authoring processes."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

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
        "docs.joomla.local",
        "--title",
        "Local Joomla Documentation",
        "--package-root",
        "global",
        "--apply",
    )
    run("knowledge-package-doctor", "--workplace", str(workplace), "--package", "docs.joomla.local", "--package-root", "global")
    return root, workplace


def test_full_chain(root: Path) -> None:
    _root, workplace = create_workplace_with_template_and_package(root)
    project = root / "joomla-component"
    project.mkdir()
    (project / "README.md").write_text("# Joomla Component Smoke\n", encoding="utf-8")

    run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "platform.joomla",
        "--title",
        "Joomla Platform",
        "--project-type",
        "joomla-component",
        "--knowledge-package",
        "docs.joomla.local",
        "--template",
        "report.audit.basic",
        "--apply",
    )
    run("platform-contract-doctor", "--workplace", str(workplace), "--platform", "platform.joomla")
    run(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "joomla-component",
        "--apply",
    )
    run("project-context-refresh", "--project-root", str(project))
    snapshot = project / ".pf" / "contexts" / "project-context.snapshot.yaml"
    assert_file(snapshot)
    assert_contains(snapshot, "platform.joomla", "docs.joomla.local", "report.audit.basic")

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
        workplace / "packages" / "docs.joomla.local" / "package.yaml",
        workplace / "platform-contracts" / "platform.joomla" / "platform-contract.yaml",
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
    _root, workplace = create_workplace_with_template_and_package(root)
    assert_no_ps1(workplace)


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
