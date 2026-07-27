#!/usr/bin/env python3
"""Smoke test for error workflow behavior across coordination modes."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

try:
    import yaml  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for this smoke") from exc

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


def read_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def init_project(workplace: Path, name: str, mode: str) -> Path:
    project = workplace / "projects" / name
    project.mkdir(parents=True)
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", mode, "--apply")
    return project


def latest_error(project: Path) -> dict[str, object]:
    files = sorted((project / ".pf" / "artifacts" / "error-workflow").glob("*.yaml"), key=lambda path: path.stat().st_mtime)
    if not files:
        raise AssertionError("missing error workflow artifact")
    return read_yaml(files[-1])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-error-workflow-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        answers = root / "workplace.answers.yaml"
        answers.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "workplace:",
                    "  id: error-workflow",
                    "  name: Error Workflow",
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
        organized = init_project(workplace, "organized", "organized")
        simple = init_project(workplace, "simple", "simple")

        pf("error-route", "--project-root", str(organized), "--workplace", str(workplace), "--mode", "director_inbox", "--summary", "organized error")
        if not any("error_report" in path.read_text(encoding="utf-8", errors="replace") for path in (workplace / ".pf" / "director" / "inbox").glob("*.yaml")):
            raise AssertionError("organized director_inbox error was not submitted")

        pf("error-route", "--project-root", str(simple), "--workplace", str(workplace), "--mode", "director_inbox", "--fallback-if-no-director", "needs_operator", "--summary", "simple fallback")
        if latest_error(simple)["result_mode"] != "needs_operator":
            raise AssertionError("simple director_inbox fallback did not record needs_operator")

        routes = simple / ".pf" / "process-routes.yaml"
        routes.write_text(
            "\n".join(
                [
                    "schema_version: 1",
                    "routes:",
                    "  - id: simple-error-route",
                    "    target_process: needs-operator",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        pf("error-route", "--project-root", str(simple), "--workplace", str(workplace), "--mode", "route_to_process", "--summary", "simple route")
        if latest_error(simple)["result_mode"] != "route_to_process":
            raise AssertionError("simple route_to_process did not stay in process route mode")

    print("PASS: error workflow smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
