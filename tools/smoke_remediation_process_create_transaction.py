#!/usr/bin/env python3
"""Regression for process-create preflight, plan parity, and rollback."""

from __future__ import annotations

import hashlib
import importlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"
sys.path.insert(0, str(ROOT / "tools"))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def fingerprint(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "authoring-transactions" not in path.parts
    }


def init_project(project: Path, workplace: Path) -> None:
    workplace_result = run("workplace-init", "--workplace", str(workplace), "--apply")
    assert workplace_result.returncode == 0, workplace_result.stdout
    project_result = run(
        "project-init",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic",
        "--apply",
    )
    assert project_result.returncode == 0, project_result.stdout


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pf-process-transaction-") as raw:
        root = Path(raw)
        uninitialized = root / "uninitialized"
        uninitialized.mkdir()
        before = fingerprint(uninitialized)
        rejected = run(
            "process-create",
            "--project-root",
            str(uninitialized),
            "--id",
            "uninitialized-process",
            "--title",
            "Uninitialized Process",
            "--apply",
        )
        if rejected.returncode == 0 or fingerprint(uninitialized) != before:
            failures.append("uninitialized process-create mutated project before root preflight")

        project = root / "project"
        workplace = root / "workplace"
        init_project(project, workplace)
        before = fingerprint(project)
        missing_mode = run(
            "process-create",
            "--project-root",
            str(project),
            "--id",
            "missing-mode",
            "--title",
            "Missing Mode",
        )
        both_modes = run(
            "process-create",
            "--project-root",
            str(project),
            "--id",
            "both-modes",
            "--title",
            "Both Modes",
            "--dry-run",
            "--apply",
        )
        if missing_mode.returncode == 0 or both_modes.returncode == 0 or fingerprint(project) != before:
            failures.append("process-create did not enforce explicit xor mode without mutation")
        dry = run(
            "process-create",
            "--project-root",
            str(project),
            "--id",
            "atomic-process",
            "--title",
            "Atomic Process",
            "--dry-run",
        )
        expected = [
            ".pf/authoring/processes/atomic-process/answers.yaml",
            ".pf/authoring/processes/atomic-process/draft.process.yaml",
            ".pf/authoring/processes/atomic-process/questions.md",
            ".pf/authoring/processes/atomic-process/logic-review.md",
            ".pf/authoring/processes/atomic-process/authoring-log.md",
            ".pf/authoring/processes/atomic-process/apply-report.md",
            "processes/user/atomic-process.yaml",
            "prompts/atomic-process-agent.md",
            "docs/processes/atomic-process.md",
        ]
        if dry.returncode != 0 or any(item not in dry.stdout.replace("\\", "/") for item in expected):
            failures.append("process-create dry-run omitted complete session/materialized plan")
        if fingerprint(project) != before:
            failures.append("process-create dry-run mutated project")
        legacy_apply = run(
            "process-authoring-apply",
            "--project-root",
            str(project),
            "--id",
            "atomic-process",
            "--dry-run",
        )
        if legacy_apply.returncode == 0 or fingerprint(project) != before:
            failures.append("process-authoring-apply accepted deprecated --id alias or mutated project")

        processforge = importlib.import_module("processforge")
        if not hasattr(processforge, "AUTHORING_FAILURE_INJECTOR"):
            failures.append("transaction failure injector missing")
        else:
            def inject(phase: str, _plan: object, _write: object | None = None) -> None:
                if phase == "after_entity_publish:4":
                    raise RuntimeError("injected process failure")

            processforge.AUTHORING_FAILURE_INJECTOR = inject
            try:
                args = processforge.build_parser().parse_args(
                    [
                        "process-create",
                        "--project-root",
                        str(project),
                        "--id",
                        "atomic-process",
                        "--title",
                        "Atomic Process",
                        "--apply",
                    ]
                )
                try:
                    args.func(args)
                except (RuntimeError, SystemExit):
                    pass
                else:
                    failures.append("injected process-create returned success")
            finally:
                processforge.AUTHORING_FAILURE_INJECTOR = None
            if fingerprint(project) != before:
                failures.append("process-create rollback did not restore exact authoritative/audit state")
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1
    print("PASS: process-create transactional smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
