#!/usr/bin/env python3
"""Regression smoke for aggregate authoring and release gate selection."""

from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
from pathlib import Path

import processforge


def authoring_args(project_root: Path) -> argparse.Namespace:
    return argparse.Namespace(project_root=str(project_root))


def release_args(root: Path, *, only: list[str]) -> argparse.Namespace:
    return argparse.Namespace(
        root=str(root),
        timeout_scale=1.0,
        no_clean=True,
        clean_first=False,
        public=False,
        only=only,
        skip=[],
        list=False,
        fail_fast=False,
        trace_smokes=False,
    )


def test_authoring_aggregate_exit(root: Path) -> None:
    project = root / "project"
    (project / ".pf").mkdir(parents=True)
    (project / ".pf" / "process-forge.yaml").write_text(
        "\n".join(["schema_version: 1", "project:", "  id: aggregate-gate-fixture", ""]),
        encoding="utf-8",
    )

    original_process = processforge.command_process_parity_check_all
    original_template = processforge.command_template_parity_check
    original_package = processforge.command_knowledge_package_parity_check
    original_platform = processforge.command_platform_parity_check
    original_status = processforge.resource_report_status
    try:
        processforge.command_process_parity_check_all = lambda _args: 0
        processforge.command_template_parity_check = lambda _args: 1
        processforge.command_knowledge_package_parity_check = lambda _args: 0
        processforge.command_platform_parity_check = lambda _args: 0
        processforge.resource_report_status = (
            lambda _project, kind, _resource: ("FAIL", "fixture-review.md")
            if kind == "template"
            else ("PASS", "fixture-review.md")
        )
        with contextlib.redirect_stdout(io.StringIO()):
            code = processforge.command_authoring_parity_check_all(authoring_args(project))
        if code == 0:
            raise AssertionError("authoring-parity-check-all returned zero for a resource FAIL")
        summary = processforge.read_yaml_file(project / ".pf" / "artifacts" / "parity" / "summary.yaml")
        if summary.get("result") != "FAIL":
            raise AssertionError(f"unexpected aggregate summary: {summary}")
    finally:
        processforge.command_process_parity_check_all = original_process
        processforge.command_template_parity_check = original_template
        processforge.command_knowledge_package_parity_check = original_package
        processforge.command_platform_parity_check = original_platform
        processforge.resource_report_status = original_status


def fake_result(command: processforge.ReleaseCommand, *, fail: bool = False) -> processforge.ReleaseCommandResult:
    return processforge.ReleaseCommandResult(
        label=command.label,
        status="FAIL" if fail else "PASS",
        code=1 if fail else 0,
        output="intentional failure" if fail else "",
        started_at="2026-07-30T00:00:00Z",
        finished_at="2026-07-30T00:00:01Z",
        elapsed_seconds=1.0,
        timeout_seconds=command.timeout,
        command=command.command,
        layer=command.layer,
        public_gate=command.public_gate,
    )


def test_public_gate_expansion(root: Path) -> None:
    commands = [
        processforge.ReleaseCommand("public-a", ["public-a"], 10, public_gate=True),
        processforge.ReleaseCommand("internal", ["internal"], 10, layer="development", public_gate=False),
        processforge.ReleaseCommand("public-b", ["public-b"], 10, public_gate=True),
    ]
    executed: list[str] = []
    original_commands = processforge.release_test_commands
    original_run = processforge.run_release_command
    original_public_checks = processforge.public_release_checks
    try:
        processforge.release_test_commands = lambda _root, clean_first=True, public=False: list(commands)

        def run(label: str, _command: list[str], _cwd: Path, timeout: int, allow_warn: bool = False, *, layer: str = "public", public_gate: bool = True) -> processforge.ReleaseCommandResult:
            del allow_warn
            command = next(item for item in commands if item.label == label)
            executed.append(label)
            return fake_result(command)

        processforge.run_release_command = run
        processforge.public_release_checks = lambda _root: [processforge.check("PASS", "fixture public checks")]
        with contextlib.redirect_stdout(io.StringIO()):
            code = processforge.command_release_test(release_args(root, only=["public-gate"]))
        if code != 0:
            raise AssertionError(f"public-gate fixture returned {code}")
        if executed != ["public-a", "public-b"]:
            raise AssertionError(f"public-gate selected wrong commands: {executed}")
    finally:
        processforge.release_test_commands = original_commands
        processforge.run_release_command = original_run
        processforge.public_release_checks = original_public_checks


def test_public_gate_failure_and_empty_selection(root: Path) -> None:
    original_commands = processforge.release_test_commands
    original_run = processforge.run_release_command
    original_public_checks = processforge.public_release_checks
    try:
        public = processforge.ReleaseCommand("public-fail", ["public-fail"], 10, public_gate=True)
        def public_commands(_root: Path, *, clean_first: bool = True, public: bool = False) -> list[processforge.ReleaseCommand]:
            del clean_first, public
            return [public_command]

        public_command = public
        processforge.release_test_commands = public_commands
        processforge.run_release_command = (
            lambda label, command, cwd, timeout, allow_warn=False, *, layer="public", public_gate=True: fake_result(public, fail=True)
        )
        processforge.public_release_checks = lambda _root: [processforge.check("PASS", "fixture public checks")]
        with contextlib.redirect_stdout(io.StringIO()):
            code = processforge.command_release_test(release_args(root, only=["public-gate"]))
        if code == 0:
            raise AssertionError("public-gate hid an intentional public command failure")

        internal = processforge.ReleaseCommand("internal", ["internal"], 10, layer="development", public_gate=False)
        def internal_commands(_root: Path, *, clean_first: bool = True, public: bool = False) -> list[processforge.ReleaseCommand]:
            del clean_first, public
            return [internal]

        processforge.release_test_commands = internal_commands
        with contextlib.redirect_stdout(io.StringIO()):
            code = processforge.command_release_test(release_args(root, only=["public-gate"]))
        if code == 0:
            raise AssertionError("public-gate accepted an empty command selection")
    finally:
        processforge.release_test_commands = original_commands
        processforge.run_release_command = original_run
        processforge.public_release_checks = original_public_checks


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-remediation-gates-") as raw:
        root = Path(raw)
        test_authoring_aggregate_exit(root)
        test_public_gate_expansion(root)
        test_public_gate_failure_and_empty_selection(root)
    print("PASS: remediation aggregate gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
