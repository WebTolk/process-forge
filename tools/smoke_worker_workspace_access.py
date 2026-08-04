#!/usr/bin/env python3
"""Smoke test for private workplace access grants in worker runs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from context_lock_smoke_helpers import make_project, refresh, require_ok, run_pf, write_yaml


def read_yaml(path: Path) -> dict:
    import yaml  # type: ignore

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-worker-workspace-access-") as temp:
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
id: worker-workspace-access
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
        text = package.read_text(encoding="utf-8")
        old_ref = "\n".join(["path_ref:", "      package: docs-joomla", "      relative_path: joomla-core/5.4.5"])
        new_ref = "\n".join(["path_ref:", "      registry: knowledge_roots", "      id: shared-docs", "      relative_path: joomla-core/5.4.5"])
        text = text.replace(old_ref, new_ref)
        package.write_text(text, encoding="utf-8")
        refresh(project)
        write_yaml(
            project / ".pf" / "assignments" / "workspace-task.yaml",
            """
schema_version: 1
id: workspace-task
title: Workspace task
run_id: workspace-run
process: task-batch-execution
status: open
objective: Use shared knowledge without copying it.
allowed_files:
  - .pf/artifacts/**
workspace_access:
  knowledge_resources:
    - joomla-core
required_capabilities: []
required_outputs:
  - id: report
    path: .pf/artifacts/workspace-report.md
    type: markdown
    required: true
expected_report:
  artifact: .pf/artifacts/workspace-report.md
""",
        )
        require_ok(run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(project / ".pf" / "assignments" / "workspace-task.yaml")))
        capsule_path = project / ".pf" / "contexts" / "assignment-capsules" / "workspace-task.capsule.yaml"
        capsule_text = capsule_path.read_text(encoding="utf-8")
        if str(shared_docs) in capsule_text:
            raise AssertionError("capsule leaked private shared docs path")
        capsule = read_yaml(capsule_path)
        if not capsule.get("workspace_access", {}).get("knowledge_resources"):
            raise AssertionError("capsule missing workspace_access knowledge_resources")
        require_ok(run_pf("worker-run", "prepare", "--project-root", str(project), "--task", "workspace-task", "--driver", "manual"))
        access_path = project / ".pf" / "runtime" / "agent-runs" / "workspace-run" / "workspace-task" / "workspace-access.json"
        access = json.loads(access_path.read_text(encoding="utf-8"))
        grants = access["grants"]["knowledge_resources"]
        if not grants or grants[0]["resolution"]["status"] != "resolved":
            raise AssertionError("workspace access grant did not resolve shared docs")
        if Path(grants[0]["resolution"]["path"]) != shared_docs:
            raise AssertionError("workspace access grant resolved unexpected path")
        prompt = (project / ".pf" / "runs" / "workspace-run" / "worker-prompts" / "workspace-task.md").read_text(encoding="utf-8")
        if "workspace_access_file" not in prompt or "Do not copy private paths" not in prompt:
            raise AssertionError("worker prompt does not explain workspace access boundary")
        command = json.loads((project / ".pf" / "runtime" / "agent-runs" / "workspace-run" / "workspace-task" / "command.json").read_text(encoding="utf-8"))
        if "workspace_access" not in command["paths"]:
            raise AssertionError("worker command paths missing workspace_access")
        if not command["command"]["environment"].get("PF_WORKSPACE_ACCESS_FILE"):
            raise AssertionError("worker command environment missing PF_WORKSPACE_ACCESS_FILE")
        private_like_path = "E" + ":/private/shared-docs"
        write_yaml(
            project / ".pf" / "assignments" / "bad-workspace-task.yaml",
            f"""
schema_version: 1
id: bad-workspace-task
title: Bad workspace task
run_id: workspace-run
process: task-batch-execution
status: open
objective: Do not allow private paths in public workspace refs.
allowed_files:
  - .pf/artifacts/**
workspace_access:
  knowledge_resources:
    - "{private_like_path}"
required_capabilities: []
""",
        )
        bad = run_pf("assignment-capsule", "--project-root", str(project), "--assignment", str(project / ".pf" / "assignments" / "bad-workspace-task.yaml"))
        if bad.returncode == 0 or "workspace access must use public refs" not in bad.stdout:
            raise AssertionError("assignment-capsule accepted private path in workspace_access")
    print("PASS: worker workspace access smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
