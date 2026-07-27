#!/usr/bin/env python3
"""Smoke test for mixed simple/organized projects in one workplace."""

from __future__ import annotations

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


def init_workplace(root: Path) -> Path:
    workplace = root / "workplace"
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
    return workplace


def onboard(workplace: Path, name: str, mode: str) -> Path:
    project = workplace / "projects" / name
    project.mkdir(parents=True)
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", mode, "--apply")
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-mixed-workplace-") as temp:
        root = Path(temp)
        workplace = init_workplace(root)
        organized = onboard(workplace, "project-a", "organized")
        simple = onboard(workplace, "project-b", "simple")

        pf("director-inbox-submit", "--project-root", str(organized), "--workplace", str(workplace), "--message-type", "worker_report", "--content", "organized worker report")
        failed = pf("director-inbox-submit", "--project-root", str(simple), "--workplace", str(workplace), "--message-type", "worker_report", "--content", "simple worker report", expect=1)
        if "project is in simple coordination mode" not in failed.stdout + failed.stderr:
            raise AssertionError("simple project failure did not explain coordination mode")

        checkin = pf("session-start", "--workplace", str(workplace), "--project-root", str(simple), "--agent", "primary-agent", "--role", "primary-agent", "--json").stdout
        if "primary-agent" not in checkin:
            raise AssertionError("simple project single-agent checkin failed")
        pf("agent-checkout", "--project-root", str(simple))

        pf("director-case-refresh", "--workplace", str(workplace))
        if not (workplace / ".pf" / "director" / "cases" / "project-a.yaml").is_file():
            raise AssertionError("organized project director case missing")
        if (workplace / ".pf" / "director" / "cases" / "project-b.yaml").exists():
            raise AssertionError("simple project got a director case by default")

    print("PASS: mixed workplace projects smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
