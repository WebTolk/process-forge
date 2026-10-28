#!/usr/bin/env python3
"""Smoke test for codex-exec driver launch with a fake Codex CLI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from context_lock_smoke_helpers import (
    make_project,
    refresh,
    require_ok,
    run_pf,
    write_yaml,
)

MODEL = "chatgpt-5.3-codex-spark"
WORKER = Path(__file__).with_name("codex_exec_worker.py")


def write_fake_codex(bin_dir: Path) -> None:
    fake = bin_dir / "fake_codex.py"
    fake.write_text(
        """
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

argv = sys.argv[1:]
Path(__file__).with_name("invocation.json").write_text(
    json.dumps({"argv": argv}), encoding="utf-8"
)
output = Path(argv[argv.index("-o") + 1])
if not output.parent.is_dir():
    raise SystemExit("output parent was not created by codex-exec worker")
payload = {
    "argv": argv,
    "stdin": sys.stdin.buffer.read().decode("utf-8"),
    "workspace_access_file": os.environ.get("PF_WORKSPACE_ACCESS_FILE", ""),
    "agent_model": os.environ.get("PF_AGENT_MODEL", ""),
    "agent_reasoning_effort": os.environ.get("PF_AGENT_REASONING_EFFORT", ""),
    "codex_reasoning_effort": os.environ.get("PF_CODEX_REASONING_EFFORT", ""),
}
output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
""".lstrip(),
        encoding="utf-8",
    )
    cmd = bin_dir / "codex.cmd"
    cmd.write_text(f'@echo off\n"{sys.executable}" "%~dp0fake_codex.py" %*\n', encoding="utf-8")
    shell = bin_dir / "codex"
    shell.write_text(f'#!/usr/bin/env sh\n"{sys.executable}" "$(dirname "$0")/fake_codex.py" "$@"\n', encoding="utf-8")
    shell.chmod(shell.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else "<not created>"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-codex-exec-worker-") as temp:
        root = Path(temp)
        project = make_project(root)
        workplace = root / "workplace"
        shared_docs = workplace / "docs" / "joomla-core" / "5.4.5"
        shared_docs.mkdir(parents=True)
        (shared_docs / "README.md").write_text("# Shared docs\n", encoding="utf-8")
        write_yaml(
            workplace / "workplace.yaml",
            """
schema_version: 1
id: codex-exec-worker
registries:
  knowledge_roots: registries/knowledge-roots.yaml
""",
        )
        write_yaml(
            workplace / "registries" / "knowledge-roots.yaml",
            """
schema_version: 1
knowledge_roots:
  - id: shared-docs
    path: docs
    status: available
""",
        )
        write_yaml(
            project / ".pf" / "process-forge.local.yaml",
            f"""
schema_version: 1
workplace:
  manifest: "{(workplace / 'workplace.yaml').as_posix()}"
local:
  project_root: "{project.as_posix()}"
""",
        )
        package = project / ".pf" / "packages" / "docs-joomla" / "package.yaml"
        old_ref = "\n".join(["path_ref:", "      package: docs-joomla", "      relative_path: joomla-core/5.4.5"])
        new_ref = "\n".join(["path_ref:", "      registry: knowledge_roots", "      id: shared-docs", "      relative_path: joomla-core/5.4.5"])
        package.write_text(package.read_text(encoding="utf-8").replace(old_ref, new_ref), encoding="utf-8")
        refresh(project)
        require_ok(run_pf("run-create", "--project-root", str(project), "--id", "codex-run", "--title", "Codex fixture", "--process", "task-batch-execution", "--apply"))
        require_ok(run_pf("task-create", "--project-root", str(project), "--run", "codex-run", "--id", "codex-task", "--title", "Codex task", "--process", "task-batch-execution", "--apply"))
        write_yaml(
            project / ".pf" / "assignments" / "codex-task.yaml",
            f"""
schema_version: 1
id: codex-task
title: Codex task
run_id: codex-run
process: task-batch-execution
status: open
objective: "Execute codex-exec with workspace access and verify UTF-8 payload: Проверка кириллицы."
allowed_files:
  - .pf/artifacts/**
workspace_access:
  knowledge_resources:
    - joomla-core
agent_model: {MODEL}
agent_reasoning_effort: high
required_capabilities: []
required_outputs:
  - id: report
    path: .pf/artifacts/codex-exec-report.json
    type: json
    required: true
expected_report:
  artifact: .pf/artifacts/codex-exec-report.json
""",
        )
        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        write_fake_codex(fake_bin)
        fake_executable = fake_bin / ("codex.cmd" if os.name == "nt" else "codex")
        env_path = os.environ.get("PATH")
        previous_executable = os.environ.get("PF_CODEX_EXECUTABLE")
        os.environ["PATH"] = str(fake_bin) + os.pathsep + (env_path or "")
        # The driver inherits explicit executable overrides before consulting PATH.
        os.environ["PF_CODEX_EXECUTABLE"] = str(fake_executable)
        try:
            result = run_pf("worker-run", "start", "--project-root", str(project), "--task", "codex-task", "--driver", "codex-exec")
            if result.returncode != 0:
                run_dir = (
                    project
                    / ".pf"
                    / "runtime"
                    / "agent-runs"
                    / "codex-run"
                    / "codex-task"
                )
                # Only allowlisted fields/literals leave the disposable fixture.
                # Never dump command.environment, arbitrary log lines or host paths.
                safe_literals = {
                    "",
                    "-",
                    "--",
                    "-B",
                    "-I",
                    "exec",
                    "-m",
                    "-c",
                    "-o",
                    "--worker-prompt",
                    "--capsule",
                    "--workspace-access",
                    "--output",
                    "--heartbeat",
                    "--prepared-input",
                    "--prepared-sha256",
                    "--exit-path",
                    "--sandbox",
                    "--cd",
                    "--json",
                    "--add-dir",
                    MODEL,
                    "high",
                    "read-only",
                    "workspace-write",
                    'model_reasoning_effort="high"',
                    "features.memories=false",
                    'mcp_servers.processforge.default_tools_approval_mode="approve"',
                    "planned",
                    "ready",
                    "starting",
                    "running",
                    "completed",
                    "failed",
                    "blocked",
                    "cancelled",
                    "unknown",
                    "timed_out",
                    "manual_required",
                    "codex-exec",
                    "shell",
                    "codex-run",
                    "codex-task",
                    "worker-run",
                    "start",
                    "--project-root",
                    "--task",
                    "--driver",
                    "storage_safety_unavailable",
                    "The syntax of the command is incorrect.",
                }

                def safe_value(value: object) -> object:
                    if value is None or isinstance(value, (bool, int)):
                        return value
                    if isinstance(value, list):
                        return [safe_value(item) for item in value]
                    if isinstance(value, dict):
                        return {
                            key: safe_value(item)
                            for key, item in value.items()
                            if key
                            in {
                                "schema_version",
                                "attempt",
                                "driver_id",
                                "command",
                                "executable",
                                "args",
                                "argv",
                                "working_directory",
                                "shell",
                                "exit_code",
                                "status",
                                "failure_reason",
                                "error",
                                "code",
                            }
                        }
                    if isinstance(value, str):
                        if value in safe_literals or re.fullmatch(
                            r"sha256:[0-9a-f]{64}|[0-9]+", value
                        ):
                            return value
                        normalized = value.replace("\\", "/")
                        if normalized == Path(sys.executable).as_posix():
                            return "<python>"
                        for base, label in (
                            (root, "<fixture>"),
                            (WORKER.parent.parent, "<source>"),
                        ):
                            prefix = base.as_posix()
                            if normalized == prefix:
                                return label
                            if normalized.startswith(prefix + "/"):
                                relative = normalized[len(prefix) :]
                                if (
                                    re.fullmatch(r"/[A-Za-z0-9_./-]+", relative)
                                    and ".." not in Path(relative).parts
                                ):
                                    return label + relative
                                return label + "/<redacted-path>"
                        if value.startswith("FAIL: ") and value[6:] in safe_literals:
                            return value
                    return "<redacted>"

                evidence: dict[str, object] = {
                    "worker_run_command": safe_value(result.args),
                    "worker_run_exit_code": result.returncode,
                    "codex_selection": {
                        "source": "PF_CODEX_EXECUTABLE (smoke fixture binding)",
                        "executable": safe_value(str(fake_executable)),
                        "invocation_observed": (fake_bin / "invocation.json").is_file(),
                    },
                    "worker_run_output": [
                        safe_value(line) for line in result.stdout.splitlines()
                    ],
                }
                receipt_paths = [
                    run_dir / name
                    for name in (
                        "command.json",
                        "exit.json",
                        "status.json",
                        "stdout.log",
                        "stderr.log",
                    )
                ]
                receipt_paths.extend(
                    path
                    for path in sorted((run_dir / "attempts").glob("*/*"))
                    if path.parent.name.isdigit()
                    and path.name
                    in {
                        "command.json",
                        "exit.json",
                        "status.json",
                        "stdout.log",
                        "stderr.log",
                        "heartbeat.json",
                    }
                )
                receipt_paths.append(fake_bin / "invocation.json")
                receipts: dict[str, object] = {}
                evidence["receipts"] = receipts
                for path in receipt_paths:
                    name = path.relative_to(root).as_posix()
                    try:
                        raw = path.read_bytes()
                        text = raw.decode("utf-8", errors="replace")
                        body = (
                            safe_value(json.loads(text))
                            if path.suffix == ".json"
                            else [safe_value(line) for line in text.splitlines()]
                        )
                        receipts[name] = {
                            "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "body": body,
                        }
                    except FileNotFoundError:
                        receipts[name] = {"receipt": "not created"}
                    except (OSError, ValueError) as error:
                        receipts[name] = {
                            "receipt": "unreadable",
                            "error_type": type(error).__name__,
                        }
                # Flush sanitized receipts before TemporaryDirectory.__exit__ runs.
                print(
                    "CODEX SMOKE FAILURE EVIDENCE\n"
                    + json.dumps(evidence, ensure_ascii=True, indent=2),
                    file=sys.stderr,
                    flush=True,
                )
                raise AssertionError(
                    f"codex-exec worker-run failed (exit {result.returncode}); sanitized receipts emitted before cleanup"
                )
        finally:
            if env_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = env_path
            if previous_executable is None:
                os.environ.pop("PF_CODEX_EXECUTABLE", None)
            else:
                os.environ["PF_CODEX_EXECUTABLE"] = previous_executable
        report = json.loads((project / ".pf" / "artifacts" / "codex-exec-report.json").read_text(encoding="utf-8"))
        argv = report["argv"]
        if "--add-dir" in argv:
            raise AssertionError("prepared references must not become whole external directory grants")
        if '"kind": "pf.prepared-input"' not in report["stdin"]:
            raise AssertionError("codex-exec did not deliver the prepared execution input")
        if "immutable prepared input" not in report["stdin"] or "## Workspace Access File" in report["stdin"]:
            raise AssertionError("codex-exec must use immutable input, without a mutable sidecar instruction")
        if "Проверка кириллицы" not in report["stdin"]:
            raise AssertionError("codex-exec did not provide a UTF-8-decodable non-ASCII prompt payload")
        if "Your final response is captured verbatim" not in report["stdin"]:
            raise AssertionError("codex-exec prompt does not explain the output artifact delivery contract")
        if "do not attempt to write the report file yourself" not in report["stdin"]:
            raise AssertionError("codex-exec prompt does not distinguish read-only report delivery")
        if not report.get("workspace_access_file"):
            raise AssertionError("fake Codex process did not receive PF_WORKSPACE_ACCESS_FILE")
        if report.get("agent_model") != MODEL:
            raise AssertionError("fake Codex process did not receive PF_AGENT_MODEL")
        if report.get("agent_reasoning_effort") != "high":
            raise AssertionError("fake Codex process did not receive PF_AGENT_REASONING_EFFORT")
        if report.get("codex_reasoning_effort") != "high":
            raise AssertionError("fake Codex process did not receive PF_CODEX_REASONING_EFFORT")
        if 'model_reasoning_effort="high"' not in argv:
            raise AssertionError("codex-exec did not pass selected high reasoning effort")
        direct_exit = root / "direct-worker-exit.json"
        direct_output = root / "direct-worker-output.json"
        direct_heartbeat = root / "direct-worker-heartbeat.json"
        direct_env = os.environ.copy()
        direct_env["PATH"] = str(fake_bin) + os.pathsep + direct_env.get("PATH", "")
        direct_env["PF_CODEX_EXECUTABLE"] = str(fake_executable)
        direct_env.update(
            {
                "PF_AGENT_MODEL": MODEL,
                "PF_CODEX_REASONING_EFFORT": "high",
                "PF_CODEX_SANDBOX": "read-only",
                "PF_PROJECT_ROOT": str(project),
                "PF_AGENT_EXIT_PATH": str(direct_exit),
            }
        )
        direct = subprocess.run(
            [
                sys.executable,
                str(WORKER),
                "--worker-prompt", str(project / ".pf" / "runs" / "codex-run" / "worker-prompts" / "codex-task.md"),
                "--capsule", str(project / ".pf" / "contexts" / "assignment-capsules" / "codex-task.capsule.yaml"),
                "--workspace-access", str(project / ".pf" / "runtime" / "agent-runs" / "codex-run" / "codex-task" / "workspace-access.json"),
                "--output", str(direct_output),
                "--heartbeat", str(direct_heartbeat),
            ],
            env=direct_env,
            check=False,
        )
        if direct.returncode != 0:
            raise AssertionError("direct codex-exec worker did not complete")
        exit_payload = json.loads(direct_exit.read_text(encoding="utf-8"))
        if exit_payload != {"schema_version": 1, "exit_code": 0, "status": "completed"}:
            raise AssertionError("codex-exec worker did not publish its durable exit contract")
        write_yaml(
            project / ".pf" / "assignments" / "codex-task-no-model.yaml",
            """
schema_version: 1
id: codex-task-no-model
title: Codex task without model
run_id: codex-run
process: task-batch-execution
status: open
objective: Confirm codex-exec does not choose a model.
allowed_files:
  - .pf/artifacts/**
agent_reasoning_effort: medium
required_capabilities: []
required_outputs:
  - id: report
    path: .pf/artifacts/codex-exec-no-model-report.json
    type: json
    required: true
expected_report:
  artifact: .pf/artifacts/codex-exec-no-model-report.json
""",
        )
        os.environ["PF_CODEX_EXECUTABLE"] = str(fake_executable)
        try:
            no_model = run_pf(
                "worker-run",
                "start",
                "--project-root",
                str(project),
                "--task",
                "codex-task-no-model",
                "--driver",
                "codex-exec",
            )
        finally:
            if previous_executable is None:
                os.environ.pop("PF_CODEX_EXECUTABLE", None)
            else:
                os.environ["PF_CODEX_EXECUTABLE"] = previous_executable
        if no_model.returncode == 0:
            raise AssertionError("codex-exec accepted a shell-agent run without an orchestrator-selected model")
        no_model_report = project / ".pf" / "artifacts" / "codex-exec-no-model-report.json"
        if no_model_report.exists():
            raise AssertionError("codex-exec missing-model failure still produced a worker report")
    print("PASS: codex exec worker smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
