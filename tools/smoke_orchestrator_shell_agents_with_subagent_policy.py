#!/usr/bin/env python3
"""Smoke test for orchestrator shell agents and subagent report policy."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
PLAN = ROOT / "examples" / "orchestrator-shell-agents" / "minimal" / "orchestrator-shell-agent-plan.yaml"
AGENT_MODEL = "gpt-test-shell-agent"


def pf(*args: str, expect: int = 0, timeout: int = 120) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def read_yaml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def tail(path: Path, max_chars: int = 1200) -> str:
    if not path.is_file():
        return "<missing>"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def project_diagnostics(project: Path, message: str) -> str:
    run_root = project / ".pf" / "runs" / "orchestrated-work"
    assignments = project / ".pf" / "assignments"
    capsules = project / ".pf" / "contexts" / "assignment-capsules"
    agent_runs = project / ".pf" / "runtime" / "agent-runs" / "orchestrated-work"
    missing = []
    for rel_path in [
        ".pf/artifacts/docs-shell-agent-report.md",
        ".pf/artifacts/test-shell-agent-report.md",
        ".pf/artifacts/subagents/docs-shell-agent/doc-reviewer.md",
        ".pf/artifacts/subagents/docs-shell-agent/link-checker.md",
    ]:
        if not (project / rel_path).is_file():
            missing.append(rel_path)
    sections = [
        message,
        "",
        f"plan: {run_root / 'orchestrator-plan.yaml'}",
        f"config_resolution_report: {run_root / 'config-resolution-report.yaml'}",
        f"assignments_dir: {assignments}",
        f"capsules_dir: {capsules}",
        f"agent_runs_dir: {agent_runs}",
        f"missing_required_reports: {', '.join(missing) if missing else 'none'}",
        "",
        "config-resolution-report.yaml tail:",
        tail(run_root / "config-resolution-report.yaml"),
        "",
        "docs assignment:",
        tail(assignments / "docs-shell-agent.yaml"),
        "",
        "test assignment:",
        tail(assignments / "test-shell-agent.yaml"),
        "",
        "supervisor report:",
        tail(project / ".pf" / "runtime" / "supervisor" / "last-tick-report.md"),
    ]
    for worker in ["docs-shell-agent", "test-shell-agent"]:
        root = agent_runs / worker
        sections.extend(
            [
                "",
                f"{worker} status.json:",
                tail(root / "status.json"),
                f"{worker} stdout tail:",
                tail(root / "stdout.log"),
                f"{worker} stderr tail:",
                tail(root / "stderr.log"),
            ]
        )
    return "\n".join(sections)


def require(condition: bool, project: Path, message: str) -> None:
    if not condition:
        raise AssertionError(project_diagnostics(project, message))


def overlap_status(data: dict[str, object]) -> str:
    non_overlap = data.get("non_overlap") if isinstance(data.get("non_overlap"), dict) else {}
    check = non_overlap.get("overlap_check") if isinstance(non_overlap.get("overlap_check"), dict) else {}
    return str(check.get("status") or "")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-orch-shell-") as temp:
        root = Path(temp)
        workplace = root / "workplace"
        project = root / "project"
        project.mkdir()
        (project / "README.md").write_text("# Orchestrator shell smoke\n", encoding="utf-8")
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
        pf("orchestrator-shell-plan-create", "--project-root", str(project), "--run", "orchestrated-work", "--title", "Orchestrated work", "--answers", str(PLAN), "--apply")
        pf("orchestrator-shell-plan-validate", "--project-root", str(project), "--run", "orchestrated-work", "--write-normalized", ".pf/artifacts/orchestrator-shell-plan.normalized.yaml")
        pf("orchestrator-shell-plan-apply", "--project-root", str(project), "--run", "orchestrated-work", "--workplace", str(workplace), "--model", AGENT_MODEL, "--apply", timeout=180)
        run_root = project / ".pf" / "runs" / "orchestrated-work"
        agent_runs = project / ".pf" / "runtime" / "agent-runs" / "orchestrated-work"
        docs_report = project / ".pf" / "artifacts" / "docs-shell-agent-report.md"
        test_report = project / ".pf" / "artifacts" / "test-shell-agent-report.md"
        subagent_dir = project / ".pf" / "artifacts" / "subagents" / "docs-shell-agent"
        require((project / ".pf" / "artifacts" / "orchestrator-shell-plan.normalized.yaml").is_file(), project, "validate did not write requested normalized plan")
        require((run_root / "orchestrator-shell-plan.normalized.yaml").is_file(), project, "apply did not write normalized plan")
        require((run_root / "config-resolution-report.yaml").is_file(), project, "apply did not write config-resolution-report.yaml")
        resolution = read_yaml(run_root / "config-resolution-report.yaml")
        resolved = resolution.get("resolved") if isinstance(resolution.get("resolved"), dict) else {}
        overlap = resolved.get("allow_write_scope_overlap") if isinstance(resolved.get("allow_write_scope_overlap"), dict) else {}
        normalized = read_yaml(run_root / "orchestrator-shell-plan.normalized.yaml")
        normalized_runtime = normalized.get("runtime") if isinstance(normalized.get("runtime"), dict) else {}
        normalized_workers = normalized.get("workers") if isinstance(normalized.get("workers"), list) else []
        require(overlap.get("value") is True, project, "allow_write_scope_overlap was not resolved to true")
        require(normalized_runtime.get("model") == AGENT_MODEL, project, "normalized runtime model did not reflect CLI override")
        require(all(isinstance(worker, dict) and worker.get("model") == AGENT_MODEL for worker in normalized_workers), project, "normalized workers did not receive CLI model override")
        require(docs_report.is_file() and test_report.is_file(), project, "required shell-agent reports missing")
        require(f"model: `{AGENT_MODEL}`" in docs_report.read_text(encoding="utf-8"), project, "docs shell-agent report did not record selected model")
        require(f"model: `{AGENT_MODEL}`" in test_report.read_text(encoding="utf-8"), project, "test shell-agent report did not record selected model")
        require("simulated_subagents: `true`" in docs_report.read_text(encoding="utf-8"), project, "subagent-enabled worker did not declare simulated subagent usage")
        require("simulated_subagents: `false`" in test_report.read_text(encoding="utf-8"), project, "subagent-disabled worker reported subagent usage")
        require((subagent_dir / "doc-reviewer.md").is_file() and (subagent_dir / "link-checker.md").is_file(), project, "required subagent reports were not written")
        docs_assignment = read_yaml(project / ".pf" / "assignments" / "docs-shell-agent.yaml")
        test_assignment = read_yaml(project / ".pf" / "assignments" / "test-shell-agent.yaml")
        docs_capsule = read_yaml(project / ".pf" / "contexts" / "assignment-capsules" / "docs-shell-agent.capsule.yaml")
        test_capsule = read_yaml(project / ".pf" / "contexts" / "assignment-capsules" / "test-shell-agent.capsule.yaml")
        docs_command = read_yaml(agent_runs / "docs-shell-agent" / "command.json")
        test_command = read_yaml(agent_runs / "test-shell-agent" / "command.json")
        docs_command_block = docs_command.get("command") if isinstance(docs_command.get("command"), dict) else {}
        test_command_block = test_command.get("command") if isinstance(test_command.get("command"), dict) else {}
        docs_env = docs_command_block.get("environment") if isinstance(docs_command_block.get("environment"), dict) else {}
        test_env = test_command_block.get("environment") if isinstance(test_command_block.get("environment"), dict) else {}
        require(docs_assignment.get("agent_model") == AGENT_MODEL, project, "docs assignment did not record selected model")
        require(test_assignment.get("agent_model") == AGENT_MODEL, project, "test assignment did not record selected model")
        require(docs_capsule.get("agent_model") == AGENT_MODEL, project, "docs capsule did not record selected model")
        require(test_capsule.get("agent_model") == AGENT_MODEL, project, "test capsule did not record selected model")
        require(docs_command.get("agent_model") == AGENT_MODEL, project, "docs command state did not record selected model")
        require(test_command.get("agent_model") == AGENT_MODEL, project, "test command state did not record selected model")
        require("--model" in docs_command_block.get("argv", []) and AGENT_MODEL in docs_command_block.get("argv", []), project, "docs shell command argv did not include --model")
        require("--model" in test_command_block.get("argv", []) and AGENT_MODEL in test_command_block.get("argv", []), project, "test shell command argv did not include --model")
        require(docs_env.get("PF_AGENT_MODEL") == AGENT_MODEL, project, "docs shell command env did not include PF_AGENT_MODEL")
        require(test_env.get("PF_AGENT_MODEL") == AGENT_MODEL, project, "test shell command env did not include PF_AGENT_MODEL")
        require(overlap_status(docs_assignment) != "fail", project, "docs assignment retained overlap_check fail despite allowed overlap")
        require(overlap_status(test_assignment) != "fail", project, "test assignment retained overlap_check fail despite allowed overlap")
        docs_capsule_scope = docs_capsule.get("scope") if isinstance(docs_capsule.get("scope"), dict) else {}
        test_capsule_scope = test_capsule.get("scope") if isinstance(test_capsule.get("scope"), dict) else {}
        require(overlap_status({"non_overlap": docs_capsule_scope.get("non_overlap")}) != "fail", project, "docs capsule retained overlap_check fail despite allowed overlap")
        require(overlap_status({"non_overlap": test_capsule_scope.get("non_overlap")}) != "fail", project, "test capsule retained overlap_check fail despite allowed overlap")
        docs_policy = docs_capsule.get("subagent_policy") if isinstance(docs_capsule.get("subagent_policy"), dict) else {}
        test_policy = test_capsule.get("subagent_policy") if isinstance(test_capsule.get("subagent_policy"), dict) else {}
        require(docs_policy.get("allow") is True and docs_policy.get("require_reports") is True, project, "allow_subagents=true policy was not copied into docs capsule")
        require(test_policy.get("allow") is False, project, "allow_subagents=false policy was not copied into test capsule")
        for worker in ["docs-shell-agent", "test-shell-agent"]:
            status = read_yaml(project / ".pf" / "runtime" / "agent-runs" / "orchestrated-work" / worker / "status.json")
            require(status.get("status") == "completed", project, f"{worker} worker run did not complete")
        leases = list((workplace / "runtime" / "agent-leases").glob("lease-orchestrated-work-*.yaml"))
        require(len(leases) == 2, project, "shell workers did not receive leases")
    print("PASS: orchestrator shell agents with subagent policy smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
