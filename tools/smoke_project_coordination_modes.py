#!/usr/bin/env python3
"""Smoke test for workplace/project coordination mode resolution."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def status(project: Path, workplace: Path) -> dict[str, object]:
    return json.loads(pf("project-mode", "status", "--project-root", str(project), "--workplace", str(workplace), "--json").stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-project-coordination-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        projects = workplace / "projects"
        project_a = projects / "project-a"
        project_b = projects / "project-b"
        project_a.mkdir(parents=True)
        project_b.mkdir(parents=True)
        (project_a / "README.md").write_text("# Project A\n", encoding="utf-8")
        (project_b / "README.md").write_text("# Project B\n", encoding="utf-8")
        answers = root / "workplace.answers.yaml"
        answers.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "workplace:",
                    "  id: mixed-workplace",
                    "  name: Mixed Workplace",
                    "  type: workstation",
                    "  os: windows",
                    "coordination:",
                    "  director_enabled: true",
                    "  director_office_enabled: true",
                    "  default_project_mode: simple",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        pf("workplace-init", "--workplace", str(workplace), "--answers", str(answers), "--apply")
        pf("project-onboard", "--project-root", str(project_a), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", "organized", "--apply")
        pf("project-onboard", "--project-root", str(project_b), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", "simple", "--apply")

        a_status = status(project_a, workplace)
        b_status = status(project_b, workplace)
        if a_status["effective_mode"] != "organized":
            raise AssertionError(f"project A effective mode mismatch: {a_status}")
        if b_status["effective_mode"] != "simple":
            raise AssertionError(f"project B effective mode mismatch: {b_status}")
        pf("project-mode", "set", "--project-root", str(project_b), "--workplace", str(workplace), "--mode", "organized", "--init-office")
        if status(project_b, workplace)["effective_mode"] != "organized":
            raise AssertionError("project B did not switch to organized")
        pf("project-mode", "set", "--project-root", str(project_b), "--workplace", str(workplace), "--mode", "simple")
        if status(project_b, workplace)["effective_mode"] != "simple":
            raise AssertionError("project B did not switch back to simple")
        pf("project-mode", "doctor", "--project-root", str(project_a), "--workplace", str(workplace))
        pf("project-mode", "doctor", "--project-root", str(project_b), "--workplace", str(workplace))
        pf("workplace-mode", "doctor", "--workplace", str(workplace))

    print("PASS: project coordination modes smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
