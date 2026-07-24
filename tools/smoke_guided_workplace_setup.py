#!/usr/bin/env python3
"""Smoke test for guided workplace setup."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

from processforge_subprocess import CommandResult, diagnostic_text, run_command as run_processforge_command


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
DEFAULT_TIMEOUT = 60
PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:[\\/]|/[Uu]sers/|/[Hh]ome/")


def run_cli(*args: str, expect: int = 0, timeout: int = DEFAULT_TIMEOUT) -> CommandResult:
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=timeout)
    if result.timed_out:
        raise AssertionError("timeout after command: " + " ".join(args) + "\n" + diagnostic_text(result))
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_contains(path: Path, needle: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if needle not in text:
        raise AssertionError(f"{path} does not contain {needle!r}")


def assert_no_private_path(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if PRIVATE_PATH_RE.search(text):
        raise AssertionError(f"private path leaked into public-style proposal: {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-guided-setup-") as temp:
        root = Path(temp)
        processforge_root = root / "processforge"
        workplace = root / "workplace"
        local_docs = root / "local-docs"
        project_root = root / "projects"
        processforge_root.mkdir()
        local_docs.mkdir()
        project_root.mkdir()
        answers = root / "answers.yaml"
        answers.write_text(
            f"""schema_version: 1
session:
  id: first-machine
  status: draft
machine_layout:
  processforge_root: ${{PROCESSFORGE_ROOT}}
  workplace_path: ${{PF_WORKPLACE}}
  local_docs_path: ${{PF_WORKPLACE}}/knowledge
  project_roots:
    - ${{PF_WORKPLACE}}/projects
agent_environment:
  tools:
    - generic
  instructions_targets:
    - AGENTS.md
  global_agents_policy: bounded_processforge_section
privacy_safety:
  local_paths_private_only: true
  public_manifests_use_path_ref: true
  secret_handling: store secret names only; never store secret values
  update_trust_policy:
    require_https: true
    require_sha256_for_download: true
    require_sha256_for_install: true
resources:
  knowledge_roots:
    -
      id: local-docs
      path_ref: ${{PF_WORKPLACE}}/knowledge
      status: available
  package_roots:
    -
      id: global
      path_ref: ${{PF_WORKPLACE}}/packages
      default: true
      writable: true
  tools: []
  mcp_servers: []
  templates: []
platform_contracts:
  policy: neutral_or_explicit
  create: []
first_project:
  onboard_now: false
  project_root: ""
  project_type: generic-software-project
  suggested_run: first-run
""",
            encoding="utf-8",
        )
        session = workplace / ".pf-workplace" / "setup-sessions" / "first-machine"
        run_cli("workplace-setup", "start", "--workplace", str(workplace), "--session-id", "first-machine", "--answers", str(answers), "--apply")
        run_cli("workplace-setup", "review", "--workplace", str(workplace), "--session-id", "first-machine")
        run_cli("workplace-setup", "apply", "--workplace", str(workplace), "--session-id", "first-machine", "--apply")
        run_cli("workplace-setup", "status", "--workplace", str(workplace), "--session-id", "first-machine")
        run_cli("doctor-workplace", "--root", str(workplace))

        for rel_path in [
            "answers.yaml",
            "proposal.yaml",
            "proposal.md",
            "review.md",
            "apply-report.md",
            "agent-instructions.md",
            "next-steps.md",
            "workplace-init.answers.yaml",
        ]:
            assert_file(session / rel_path)
        for rel_path in [
            "workplace.yaml",
            "terms.yaml",
            "registries/knowledge-roots.yaml",
            "registries/package-roots.yaml",
            "registries/tools.yaml",
            "registries/mcp.yaml",
        ]:
            assert_file(workplace / rel_path)
        assert_contains(session / "proposal.md", "Apply Plan")
        assert_contains(session / "agent-instructions.md", "Do not copy ProcessForge into agent config folders or projects.")
        assert_contains(session / "agent-instructions.md", "python .pf/runtime/bin/pf.py")
        assert_contains(session / "apply-report.md", "doctor-workplace")
        assert_no_private_path(session / "proposal.yaml")
        if not os.path.isdir(local_docs):
            raise AssertionError(f"temp local docs path missing: {local_docs}")
        if not os.path.isdir(project_root):
            raise AssertionError(f"temp project root missing: {project_root}")
    print("PASS: guided workplace setup smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
