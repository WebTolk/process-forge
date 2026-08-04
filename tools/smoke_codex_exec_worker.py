#!/usr/bin/env python3
"""Smoke test for codex-exec driver launch with a fake Codex CLI."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from context_lock_smoke_helpers import make_project, refresh, require_ok, run_pf, write_yaml


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
output = Path(argv[argv.index("-o") + 1])
output.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "argv": argv,
    "stdin": sys.stdin.read(),
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
        write_yaml(
            project / ".pf" / "assignments" / "codex-task.yaml",
            """
schema_version: 1
id: codex-task
title: Codex task
run_id: codex-run
process: task-batch-execution
status: open
objective: Execute codex-exec with workspace access.
allowed_files:
  - .pf/artifacts/**
workspace_access:
  knowledge_resources:
    - joomla-core
agent_model: gpt-5.3-codex-spark
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
        env_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(fake_bin) + os.pathsep + env_path
        try:
            result = run_pf("worker-run", "start", "--project-root", str(project), "--task", "codex-task", "--driver", "codex-exec")
            if result.returncode != 0:
                stderr = project / ".pf" / "runtime" / "agent-runs" / "codex-run" / "codex-task" / "stderr.log"
                stdout = project / ".pf" / "runtime" / "agent-runs" / "codex-run" / "codex-task" / "stdout.log"
                raise AssertionError(
                    "\n".join(
                        [
                            result.stdout,
                            "STDOUT",
                            stdout.read_text(encoding="utf-8", errors="replace"),
                            "STDERR",
                            stderr.read_text(encoding="utf-8", errors="replace"),
                        ]
                    )
                )
        finally:
            os.environ["PATH"] = env_path
        report = json.loads((project / ".pf" / "artifacts" / "codex-exec-report.json").read_text(encoding="utf-8"))
        argv = report["argv"]
        if "--add-dir" not in argv:
            raise AssertionError("codex-exec did not pass workspace grants as --add-dir")
        add_dir = Path(argv[argv.index("--add-dir") + 1])
        if add_dir != shared_docs:
            raise AssertionError("codex-exec --add-dir does not match resolved shared docs")
        if "workspace_access_file" not in report["stdin"]:
            raise AssertionError("codex-exec prompt payload missing workspace access reference")
        if not report.get("workspace_access_file"):
            raise AssertionError("fake Codex process did not receive PF_WORKSPACE_ACCESS_FILE")
        if report.get("agent_model") != "gpt-5.3-codex-spark":
            raise AssertionError("fake Codex process did not receive PF_AGENT_MODEL")
        if report.get("agent_reasoning_effort") != "high":
            raise AssertionError("fake Codex process did not receive PF_AGENT_REASONING_EFFORT")
        if report.get("codex_reasoning_effort") != "high":
            raise AssertionError("fake Codex process did not receive PF_CODEX_REASONING_EFFORT")
        if 'model_reasoning_effort="high"' not in argv:
            raise AssertionError("codex-exec did not pass selected high reasoning effort")
    print("PASS: codex exec worker smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
