#!/usr/bin/env python3
"""Smoke test for ProcessForge authoring parity and backfill."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("PF_REPO_ROOT", Path(__file__).resolve().parents[4])).resolve()
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command

CLI = ROOT / "tools" / "processforge.py"
DEFAULT_TIMEOUT = 90
CRITICAL = {
    "workplace-initialization",
    "project-onboarding",
    "task-batch-execution",
    "process-authoring",
    "reusable-template-authoring",
    "knowledge-package-authoring",
    "platform-contract-authoring",
}


def run_cmd(command: list[str], cwd: Path = ROOT, timeout: int = DEFAULT_TIMEOUT, expect: int = 0) -> CommandResult:
    result = run_processforge_command(command, cwd=cwd, timeout=timeout)
    if result.timed_out:
        print("FAIL smoke_authoring_parity: timeout")
        print(diagnostic_text(result))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(command)}")
    if result.returncode != expect:
        print("FAIL smoke_authoring_parity: unexpected command exit")
        print(f"Expected exit code: {expect}")
        print(diagnostic_text(result))
        raise AssertionError(f"expected exit {expect}, got {result.returncode}: {' '.join(command)}")
    return result


def pf(*args: str, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    return run_cmd([sys.executable, str(CLI), *args], expect=expect, timeout=timeout)


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        raise AssertionError(f"{path} does not contain {needle!r}")


def make_project(root: Path, name: str) -> Path:
    workplace = root / f"{name}-workplace"
    project = root / name
    project.mkdir(parents=True)
    (project / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return project


def positive_root_checks() -> None:
    pf("process-authoring-import", "--project-root", str(ROOT), "--process", "task-batch-execution", "--apply")
    backfill = ROOT / ".pf" / "authoring" / "backfill" / "processes" / "task-batch-execution"
    for name in ["answers.yaml", "draft.process.yaml", "source.process.yaml", "semantic-map.yaml", "unsupported-fields.yaml", "import-report.md"]:
        assert_file(backfill / name)
    pf("process-parity-check", "--project-root", str(ROOT), "--process", "task-batch-execution")
    pf("process-parity-check", "--project-root", str(ROOT), "--process", "process-authoring")
    pf("process-parity-check-all", "--project-root", str(ROOT), timeout=180)
    summary = ROOT / ".pf" / "artifacts" / "parity" / "processes" / "summary.yaml"
    index = ROOT / ".pf" / "reviews" / "parity" / "processes" / "index.md"
    assert_file(summary)
    assert_file(index)
    text = summary.read_text(encoding="utf-8", errors="replace")
    for process_id in CRITICAL:
        marker = f"process_id: {process_id}"
        if marker not in text:
            raise AssertionError(f"critical process missing from summary: {process_id}")
        chunk = text.split(marker, 1)[1].split("process_id:", 1)[0]
        if "result: FAIL" in chunk:
            raise AssertionError(f"critical process failed parity: {process_id}")
    pf("template-parity-check", "--project-root", str(ROOT), "--template", "process-agent-prompt")
    pf("knowledge-package-parity-check", "--project-root", str(ROOT), "--package", "process-forge-core")
    pf("platform-parity-check", "--project-root", str(ROOT), "--platform", "platform-contract-example-parent")
    pf("authoring-parity-check-all", "--project-root", str(ROOT), timeout=180)
    top_summary = ROOT / ".pf" / "artifacts" / "parity" / "summary.yaml"
    assert_file(top_summary)
    top_text = top_summary.read_text(encoding="utf-8", errors="replace")
    ambiguous_status = "PASS" + "_OR_" + "SKIP"
    if ambiguous_status in top_text:
        raise AssertionError("top parity summary still contains ambiguous resource status")
    if "result: WARN" in text and "result: WARN" not in top_text:
        raise AssertionError("top parity summary did not preserve WARN aggregate")
    for report in [
        ROOT / ".pf" / "reviews" / "parity" / "resources" / "template-process-agent-prompt.md",
        ROOT / ".pf" / "reviews" / "parity" / "resources" / "knowledge-package-process-forge-core.md",
        ROOT / ".pf" / "reviews" / "parity" / "resources" / "platform-platform-contract-example-parent.md",
    ]:
        assert_file(report)
        report_text = report.read_text(encoding="utf-8", errors="replace")
        if "Result: `PASS`" in report_text:
            raise AssertionError(f"shallow resource parity reported PASS: {report}")
        if "shallow parity check" not in report_text and "round-trip is not implemented" not in report_text:
            raise AssertionError(f"resource parity report lacks shallow/SKIP explanation: {report}")


def temp_process_checks(root: Path) -> None:
    project = make_project(root, "created-process")
    answers = ROOT / "examples" / "process-authoring" / "quality-audit" / "answers.yaml"
    pf("process-create", "--project-root", str(project), "--answers", str(answers), "--apply")
    pf("process-parity-check", "--project-root", str(project), "--process", "quality-audit")


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def negative_checks(root: Path) -> None:
    project = make_project(root, "negative-parity")
    source = write_yaml(
        root / "source.process.yaml",
        """
schema_version: 1
id: parity-negative
name: Parity Negative
version: 0.1.0
status: draft
description: Source process for parity negatives.
run_model: {supports_multiple_tasks: true, default_task_loop: {enabled: true, iteration_kinds: [work, debug]}}
roles: [{id: author, title: Author}]
stages:
  - {id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
  - {id: work, title: Work, required_role: author, produced_artifacts: [work-output], exit_gates: [work-ready]}
artifact_definitions:
  - {id: brief, title: Brief, owner_role: author, lifecycle: [draft, approved]}
  - {id: work-output, title: Work Output, owner_role: author, lifecycle: [draft, approved]}
gates:
  - {id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}
  - {id: work-ready, description: Work ready, blocking: true, required_artifact: work-output}
evolution_policy: {active_run_upgrade: {default: manual_only}}
""",
    )
    missing_stage = write_yaml(
        root / "missing-stage.process.yaml",
        """
schema_version: 1
id: parity-negative
name: Parity Negative
version: 0.1.0
status: draft
description: Source process for parity negatives.
run_model: {supports_multiple_tasks: true, default_task_loop: {enabled: true, iteration_kinds: [work, debug]}}
roles: [{id: author, title: Author}]
stages:
  - {id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
artifact_definitions:
  - {id: brief, title: Brief, owner_role: author, lifecycle: [draft, approved]}
  - {id: work-output, title: Work Output, owner_role: author, lifecycle: [draft, approved]}
gates:
  - {id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}
  - {id: work-ready, description: Work ready, blocking: true, required_artifact: work-output}
evolution_policy: {active_run_upgrade: {default: manual_only}}
""",
    )
    missing_gate_artifact = write_yaml(
        root / "missing-gate-artifact.process.yaml",
        """
schema_version: 1
id: parity-negative
name: Parity Negative
version: 0.1.0
status: draft
description: Source process for parity negatives.
run_model: {supports_multiple_tasks: true, default_task_loop: {enabled: true, iteration_kinds: [work, debug]}}
roles: [{id: author, title: Author}]
stages:
  - {id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
  - {id: work, title: Work, required_role: author, produced_artifacts: [work-output], exit_gates: [work-ready]}
artifact_definitions:
  - {id: brief, title: Brief, owner_role: author, lifecycle: [draft, approved]}
gates:
  - {id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}
evolution_policy: {active_run_upgrade: {default: manual_only}}
""",
    )
    lost_run_model = write_yaml(
        root / "lost-run-model.process.yaml",
        """
schema_version: 1
id: parity-negative
name: Parity Negative
version: 0.1.0
status: draft
description: Source process for parity negatives.
roles: [{id: author, title: Author}]
stages:
  - {id: intake, title: Intake, required_role: author, produced_artifacts: [brief], exit_gates: [brief-approved]}
  - {id: work, title: Work, required_role: author, produced_artifacts: [work-output], exit_gates: [work-ready]}
artifact_definitions:
  - {id: brief, title: Brief, owner_role: author, lifecycle: [draft, approved]}
  - {id: work-output, title: Work Output, owner_role: author, lifecycle: [draft, approved]}
gates:
  - {id: brief-approved, description: Brief approved, blocking: true, required_artifact: brief}
  - {id: work-ready, description: Work ready, blocking: true, required_artifact: work-output}
evolution_policy: {active_run_upgrade: {default: manual_only}}
""",
    )
    pf("process-parity-check", "--project-root", str(project), "--process-file", str(source), "--candidate-file", str(missing_stage), expect=1)
    assert_contains(project / ".pf" / "artifacts" / "parity" / "processes" / "parity-negative-semantic-diff.yaml", "stages missing: work")
    pf("process-parity-check", "--project-root", str(project), "--process-file", str(source), "--candidate-file", str(missing_gate_artifact), expect=1)
    assert_contains(project / ".pf" / "artifacts" / "parity" / "processes" / "parity-negative-semantic-diff.yaml", "artifact_definitions missing: work-output")
    pf("process-parity-check", "--project-root", str(project), "--process-file", str(source), "--candidate-file", str(lost_run_model), expect=1)
    assert_contains(project / ".pf" / "artifacts" / "parity" / "processes" / "parity-negative-semantic-diff.yaml", "run_model differs")
    unsupported = write_yaml(
        root / "unsupported.process.yaml",
        source.read_text(encoding="utf-8") + "\ncustom_field: preserved-by-warning\n",
    )
    result = pf("process-parity-check", "--project-root", str(project), "--process-file", str(unsupported))
    if "WARN:" not in result.stdout:
        raise AssertionError("unsupported custom field did not produce WARN")
    byte_order = write_yaml(root / "byte-order.process.yaml", source.read_text(encoding="utf-8"))
    result = pf("process-parity-check", "--project-root", str(project), "--process-file", str(source), "--candidate-file", str(byte_order))
    if "PASS:" not in result.stdout:
        raise AssertionError("byte-order-only candidate did not pass")


def dogfooding_manifest_contains_parity() -> None:
    manifest = ROOT / ".pf" / "dogfooding" / "tests" / "manifest.yaml"
    text = manifest.read_text(encoding="utf-8", errors="replace")
    if "smoke_authoring_parity" not in text:
        raise AssertionError("dogfooding manifest does not include smoke_authoring_parity")
    result = pf("release-test", "--root", str(ROOT), "--public", "--list")
    if "smoke_authoring_parity" in result.stdout:
        raise AssertionError("public release-test includes dogfooding smoke_authoring_parity")


def main() -> int:
    positive_root_checks()
    with tempfile.TemporaryDirectory(prefix="pf-authoring-parity-smoke-") as temp:
        root = Path(temp)
        temp_process_checks(root)
        negative_checks(root)
    dogfooding_manifest_contains_parity()
    print("PASS: smoke_authoring_parity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
