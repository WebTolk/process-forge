#!/usr/bin/env python3
"""Config behavior contracts for orchestrator shell-agent plans."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
BASE_PLAN = ROOT / "examples" / "orchestrator-shell-agents" / "minimal" / "orchestrator-shell-agent-plan.yaml"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")


def new_plan(run_id: str) -> dict[str, Any]:
    plan = load_yaml(BASE_PLAN)
    plan["run"]["id"] = run_id
    plan["run"]["title"] = run_id.replace("-", " ").title()
    return plan


def bootstrap(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    workplace = root / "workplace"
    project = root / "project"
    project.mkdir()
    (project / "README.md").write_text("# Config behavior smoke\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return workplace, project


def overlap_status(project: Path, task_id: str) -> str:
    assignment = load_yaml(project / ".pf" / "assignments" / f"{task_id}.yaml")
    non_overlap = assignment.get("non_overlap") if isinstance(assignment.get("non_overlap"), dict) else {}
    check = non_overlap.get("overlap_check") if isinstance(non_overlap.get("overlap_check"), dict) else {}
    return str(check.get("status") or "")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_allow_overlap_completes(root: Path) -> None:
    workplace, project = bootstrap(root / "allow")
    plan_path = root / "plans" / "allow-overlap.yaml"
    write_yaml(plan_path, new_plan("allow-overlap"))
    pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--plan", str(plan_path), "--write-normalized", ".pf/artifacts/allow-overlap.normalized.yaml")
    pf("orchestrator-shell-plan-apply", "--project-root", str(project), "--plan", str(plan_path), "--workplace", str(workplace), "--apply", timeout=180)
    assert_true((project / ".pf" / "runs" / "allow-overlap" / "config-resolution-report.yaml").is_file(), "config resolution report missing")
    assert_true(overlap_status(project, "docs-shell-agent") != "fail", "docs assignment overlap failed despite allow policy")
    assert_true(overlap_status(project, "test-shell-agent") != "fail", "test assignment overlap failed despite allow policy")
    assert_true((project / ".pf" / "artifacts" / "docs-shell-agent-report.md").is_file(), "docs worker report missing")
    assert_true((project / ".pf" / "artifacts" / "test-shell-agent-report.md").is_file(), "test worker report missing")


def test_deny_overlap_fails_validation(root: Path) -> None:
    _workplace, project = bootstrap(root / "deny")
    plan = new_plan("deny-overlap")
    plan["allow_write_scope_overlap"] = False
    plan_path = root / "plans" / "deny-overlap.yaml"
    write_yaml(plan_path, plan)
    result = pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--plan", str(plan_path), expect=1)
    assert_true("parallel write scopes overlap" in result.stdout, "deny overlap did not fail on write-scope conflict")


def test_unknown_field_fails_validation(root: Path) -> None:
    _workplace, project = bootstrap(root / "unknown")
    plan = new_plan("unknown-field")
    plan["unsupported_public_knob"] = True
    plan_path = root / "plans" / "unknown-field.yaml"
    write_yaml(plan_path, plan)
    result = pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--plan", str(plan_path), expect=1)
    assert_true("unsupported top-level config field" in result.stdout, "unknown public config field was not rejected")


def test_wrong_type_fails_validation(root: Path) -> None:
    _workplace, project = bootstrap(root / "wrong-type")
    plan = new_plan("wrong-type")
    plan["allow_write_scope_overlap"] = "true"
    plan_path = root / "plans" / "wrong-type.yaml"
    write_yaml(plan_path, plan)
    result = pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--plan", str(plan_path), expect=1)
    assert_true("allow_write_scope_overlap boolean" in result.stdout, "wrong allow_write_scope_overlap type was not rejected")


def test_missing_subagent_reports_fail_collect(root: Path) -> None:
    _workplace, project = bootstrap(root / "missing-subagents")
    plan = new_plan("missing-subagents")
    plan["runtime"]["start_policy"] = "prepare"
    plan_path = root / "plans" / "missing-subagents.yaml"
    write_yaml(plan_path, plan)
    pf("orchestrator-shell-plan-apply", "--project-root", str(project), "--plan", str(plan_path), "--apply")
    pf("worker-run", "start", "--project-root", str(project), "--task", "docs-shell-agent")
    shutil.rmtree(project / ".pf" / "artifacts" / "subagents" / "docs-shell-agent")
    result = pf("worker-run", "collect", "--project-root", str(project), "--task", "docs-shell-agent", expect=1)
    assert_true("subagent policy failures" in result.stdout, "collect did not fail when required subagent reports were missing")


def test_unknown_runtime_driver_fails_validation(root: Path) -> None:
    _workplace, project = bootstrap(root / "unknown-driver")
    plan = new_plan("unknown-driver")
    plan["workers"][0]["runtime_driver"] = "missing-driver"
    plan_path = root / "plans" / "unknown-driver.yaml"
    write_yaml(plan_path, plan)
    result = pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--plan", str(plan_path), expect=1)
    assert_true("runtime_driver registered: missing-driver" in result.stdout, "unknown runtime driver was not rejected")


def test_manual_start_policy_does_not_autostart(root: Path) -> None:
    _workplace, project = bootstrap(root / "manual")
    plan = new_plan("manual-start")
    plan["runtime"]["start_policy"] = "manual"
    plan_path = root / "plans" / "manual-start.yaml"
    write_yaml(plan_path, plan)
    pf("orchestrator-shell-plan-apply", "--project-root", str(project), "--plan", str(plan_path), "--apply")
    assert_true((project / ".pf" / "runs" / "manual-start" / "config-resolution-report.yaml").is_file(), "manual apply did not write config resolution report")
    assert_true(not (project / ".pf" / "artifacts" / "docs-shell-agent-report.md").exists(), "manual start policy auto-started docs worker")
    assert_true(not (project / ".pf" / "runtime" / "agent-runs" / "manual-start").exists(), "manual start policy prepared runtime agent runs")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-config-behavior-") as temp:
        root = Path(temp)
        for test in [
            test_allow_overlap_completes,
            test_deny_overlap_fails_validation,
            test_unknown_field_fails_validation,
            test_wrong_type_fails_validation,
            test_missing_subagent_reports_fail_collect,
            test_unknown_runtime_driver_fails_validation,
            test_manual_start_policy_does_not_autostart,
        ]:
            test(root)
    print("PASS: config behavior contracts smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
