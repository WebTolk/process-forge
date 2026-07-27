#!/usr/bin/env python3
"""Helpers for project context snapshot lock-model smokes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run_pf(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PF), *args], cwd=str(cwd or ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def require_ok(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout


def write_yaml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def make_project(root: Path, *, organized: bool = False) -> Path:
    project = root / "project"
    flow = project / ".pf"
    write_yaml(
        flow / "process-forge.yaml",
        f"""
schema_version: 1
process_forge:
  version: "1.0.0"
  version_constraint: "^1.0"
  mode: file_only
  install_mode: linked
  runner_required: false
  backend_required: false
project:
  id: context-lock-demo
  name: Context Lock Demo
coordination:
  mode: {"organized" if organized else "simple"}
paths:
  packages: packages
  contexts: contexts
  artifacts: artifacts
  runtime: runtime
policies:
  one_writer_per_file_scope: true
  approved_artifacts_are_protected: true
workplace:
  reference: {"auto" if organized else "none"}
required_capabilities: []
optional_capabilities: []
knowledge_stack:
  - id: docs-joomla
    version: "^1.0"
    source: project
context_requirements:
  knowledge_packages:
    - id: docs-joomla
      constraint: "^1.0"
      required: true
  knowledge_resources:
    - id: joomla-core
      constraint: ">=5.0 <6.0"
      preferred_version: "5.4.5"
      required: true
    - id: joomla-development-articles
      channel: stable
      required: true
context_policy:
  on_session_start:
    check_freshness: true
    if_fresh: continue
    if_fresh_with_updates: notify
    if_stale: {"notify_director" if organized else "ask_operator"}
    if_broken: block
  active_run_behavior:
    existing_capsules: pin_existing
    new_capsules: require_fresh_snapshot
""",
    )
    write_yaml(flow / "AGENTS.md", "# AGENTS\n")
    if organized:
        write_yaml(
            project / "workplace.yaml",
            """
schema_version: 1
id: context-lock-workplace
coordination:
  director_enabled: true
  director_office_enabled: true
  default_project_mode: simple
  director:
    process_id: agent-director-supervision
""",
        )
        for relative in [
            ".pf/director",
            ".pf/director/inbox",
            ".pf/director/outbox",
            ".pf/director/cases",
            ".pf/director/history",
        ]:
            (project / relative).mkdir(parents=True, exist_ok=True)
    write_package(project, core_versions=["5.4.5"], articles_generation="A")
    return project


def resource_core(version: str) -> str:
    return f"""
  - id: joomla-core
    kind: source_tree
    title: Joomla Core {version}
    version: "{version}"
    path_ref:
      package: docs-joomla
      relative_path: joomla-core/{version}
    load_policy: on_demand
    index_policy: symbols
    versioning:
      mode: multi_version
      version_field: version
      instance_id_template: "{{id}}@{{version}}"
    retention:
      policy: keep_versions
      keep_last_n: null
    snapshot_behavior:
      on_new_version: notify_only
      on_current_generation_changed: notify_only
      on_instance_missing: broken
      reproducibility: exact
    fingerprint:
      type: manifest_sha256
      value: sha256:{version.replace('.', ''):0<64}
"""


def write_package(project: Path, *, core_versions: list[str], articles_generation: str) -> None:
    resources = "".join(resource_core(version) for version in core_versions)
    resources += f"""
  - id: joomla-development-articles
    kind: article_collection
    title: Joomla Development Articles
    generation: "{articles_generation}"
    path_ref:
      package: docs-joomla
      relative_path: articles/index.yaml
    load_policy: on_demand
    index_policy: metadata
    versioning:
      mode: rolling_index
      version_field: generation
      instance_id_template: "{{id}}@{{generation}}"
    retention:
      policy: replace_in_place
      keep_last_n: null
    snapshot_behavior:
      on_new_version: mark_stale
      on_current_generation_changed: mark_stale
      on_instance_missing: broken
      reproducibility: best_effort
    fingerprint:
      type: index_sha256
      value: sha256:{articles_generation.lower():0<64}
"""
    write_yaml(
        project / ".pf" / "packages" / "docs-joomla" / "package.yaml",
        f"""
schema_version: 1
id: docs-joomla
name: Docs Joomla
version: "1.0.0"
kind: platform
scope: project
resources:
{resources}
""",
    )


def refresh(project: Path) -> None:
    require_ok(run_pf("project-context-refresh", "--project-root", str(project), "--reason", "smoke"))


def check_json(project: Path, *extra: str) -> dict:
    result = run_pf("project-context-check", "--project-root", str(project), "--json", *extra)
    output = result.stdout
    if result.returncode != 0:
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise AssertionError(output) from exc
    return json.loads(output)


def snapshot(project: Path) -> dict:
    import yaml  # type: ignore

    return yaml.safe_load((project / ".pf" / "contexts" / "project-context.snapshot.yaml").read_text(encoding="utf-8"))


def make_assignment(project: Path, name: str = "demo-task") -> Path:
    path = project / ".pf" / "assignments" / f"{name}.md"
    write_yaml(
        path,
        f"""
---
id: {name}
status: ready
objective: Demo task
allowed_files:
  - README.md
required_capabilities: []
---

# Demo task
""",
    )
    return path
