#!/usr/bin/env python3
"""Smoke test for snapshot/capsule awareness of Director coordination."""

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


def init_pair(root: Path) -> tuple[Path, Path, Path]:
    workplace = root / "workplace"
    answers = root / "workplace.answers.yaml"
    answers.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workplace:",
                "  id: worker-aware",
                "  name: Worker Aware",
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
    organized = workplace / "projects" / "organized"
    simple = workplace / "projects" / "simple"
    organized.mkdir(parents=True)
    simple.mkdir(parents=True)
    (organized / "README.md").write_text("# Organized\n", encoding="utf-8")
    (simple / "README.md").write_text("# Simple\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(organized), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", "organized", "--apply")
    pf("project-onboard", "--project-root", str(simple), "--workplace", str(workplace), "--type", "generic-software-project", "--coordination-mode", "simple", "--apply")
    return workplace, organized, simple


def write_assignment(project: Path, assignment_id: str, require_inbox: bool) -> Path:
    path = project / ".pf" / "assignments" / f"{assignment_id}.yaml"
    payload = {
        "schema_version": 1,
        "id": assignment_id,
        "status": "ready",
        "objective": "Verify worker awareness.",
        "allowed_files": ["README.md"],
        "coordination_requirements": {
            "mode": "organized_optional",
            "director_inbox": {"required": require_inbox, "optional": True},
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-worker-awareness-") as temp:
        workplace, organized, simple = init_pair(Path(temp))
        del workplace
        org_snapshot = read_yaml(organized / ".pf" / "contexts" / "project-context.snapshot.yaml")
        simple_snapshot = read_yaml(simple / ".pf" / "contexts" / "project-context.snapshot.yaml")
        if org_snapshot["workplace_coordination"]["effective_mode"] != "organized":
            raise AssertionError("organized snapshot missing effective organized mode")
        if not org_snapshot["workplace_coordination"]["director_inbox"]["enabled"]:
            raise AssertionError("organized snapshot missing director inbox metadata")
        if simple_snapshot["workplace_coordination"]["effective_mode"] != "simple":
            raise AssertionError("simple snapshot missing effective simple mode")
        if simple_snapshot["workplace_coordination"]["director_required"] is not False:
            raise AssertionError("simple snapshot should not require Director")

        org_assignment = write_assignment(organized, "organized-worker", True)
        simple_assignment = write_assignment(simple, "simple-worker", False)
        pf("assignment-capsule", "--project-root", str(organized), "--assignment", str(org_assignment))
        pf("assignment-capsule", "--project-root", str(simple), "--assignment", str(simple_assignment))
        org_capsule = read_yaml(organized / ".pf" / "contexts" / "assignment-capsules" / "organized-worker.capsule.yaml")
        simple_capsule = read_yaml(simple / ".pf" / "contexts" / "assignment-capsules" / "simple-worker.capsule.yaml")
        if not org_capsule["workplace_coordination"]["director_inbox"]["submit_required"]:
            raise AssertionError("organized capsule missing required director inbox metadata")
        if simple_capsule["workplace_coordination"]["director_required"] is not False:
            raise AssertionError("simple capsule should not require Director")
        if "director_inbox" in simple_capsule["workplace_coordination"]:
            raise AssertionError("simple capsule should not include Director inbox obligations")

    print("PASS: worker awareness of director smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
