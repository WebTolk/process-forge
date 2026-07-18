#!/usr/bin/env python3
"""Smoke test for the ProcessForge first-run UX."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"
DEFAULT_TIMEOUT = 60


def output_tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.splitlines()[-lines:])


def run_subprocess(command: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if not isinstance(output, str):
            output = output.decode(errors="replace")
        print("TIMEOUT: smoke_first_run command exceeded timeout")
        print("Command:")
        print("  " + " ".join(command))
        print("CWD:")
        print(f"  {cwd}")
        print("Timeout seconds:")
        print(f"  {timeout}")
        if output:
            print("STDOUT tail:")
            print(output_tail(output))
        raise AssertionError(f"timeout after {timeout}s: {' '.join(command)}") from exc


def run_command(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CLI), *args]
    result = run_subprocess(command, cwd=cwd, env=env)
    if expect_success and result.returncode != 0:
        raise AssertionError("command failed: " + " ".join(args) + "\n" + output_tail(result.stdout))
    if not expect_success and result.returncode == 0:
        raise AssertionError("command unexpectedly succeeded: " + " ".join(args) + "\n" + output_tail(result.stdout))
    return result


def run_python(script: Path, *args: str, cwd: Path, env: dict[str, str] | None = None, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script), *args]
    result = run_subprocess(command, cwd=cwd, env=env)
    if expect_success and result.returncode != 0:
        raise AssertionError(f"python launcher failed: {script}\n{output_tail(result.stdout)}")
    if not expect_success and result.returncode == 0:
        raise AssertionError(f"python launcher unexpectedly succeeded: {script}\n{output_tail(result.stdout)}")
    return result


def assert_file(path: Path) -> None:
    if not path.is_file():
        raise AssertionError(f"missing file: {path}")


def assert_no_public_absolute_paths(project: Path) -> None:
    for path in [
        project / ".pf" / "process-forge.yaml",
        project / ".pf" / "START_AGENT_HERE.md",
        project / ".pf" / "contexts" / "project-context.snapshot.yaml",
    ]:
        text = path.read_text(encoding="utf-8", errors="replace")
        if ":\\\\" in text:
            raise AssertionError(f"public file contains Windows absolute path marker: {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="processforge-first-run-") as temp:
        root = Path(temp)
        workplace = root / "pf-workplace"
        project = root / "my-project"
        project.mkdir()
        (project / "README.md").write_text("# Smoke Project\n", encoding="utf-8")

        run_command("workplace-init", "--workplace", str(workplace), "--apply")
        for rel_path in [
            "workplace.yaml",
            "terms.yaml",
            "registries/package-roots.yaml",
            "registries/knowledge-roots.yaml",
            "registries/tools.yaml",
            "registries/mcp.yaml",
            "runtime/events/events.ndjson",
        ]:
            assert_file(workplace / rel_path)
        run_command("doctor-workplace", "--root", str(workplace))

        run_command(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )
        for rel_path in [
            ".pf/AGENTS.md",
            ".pf/START_AGENT_HERE.md",
            ".pf/process-forge.yaml",
            ".pf/process-forge.local.yaml",
            ".pf/hooks.yaml",
            ".pf/assignments/first-assignment.yaml",
            ".pf/runtime/bin/pf.py",
            ".pf/contexts/project-context.snapshot.yaml",
            ".pf/artifacts/project-onboarding-report.md",
            ".pf/reviews/project-onboarding-review.md",
            ".pf/handoffs/project-ready-handoff.md",
            ".pf/runtime/events/events.ndjson",
        ]:
            assert_file(project / rel_path)
        assert_no_public_absolute_paths(project)
        start_text = (project / ".pf" / "START_AGENT_HERE.md").read_text(encoding="utf-8", errors="replace")
        if "python tools/processforge.py" in start_text:
            raise AssertionError("START_AGENT_HERE contains broken linked-project command")
        if "python .pf/runtime/bin/pf.py doctor-project --project-root ." not in start_text:
            raise AssertionError("START_AGENT_HERE does not document the project runtime launcher fallback")

        prompt = run_command("agent-start-prompt", "--project-root", str(project)).stdout
        if "Start Agent Here" not in prompt:
            raise AssertionError("agent-start-prompt did not print the start prompt")
        if "python tools/processforge.py" in prompt:
            raise AssertionError("agent-start-prompt printed broken linked-project command")

        run_python(project / ".pf" / "runtime" / "bin" / "pf.py", "doctor-project", "--project-root", ".", cwd=project)

        run_command("project-context-refresh", "--project-root", str(project))
        run_command("doctor-project", "--project-root", str(project))
        run_command("hooks-dispatch", "--project-root", str(project), "--event-type", "project.onboarding.completed", "--outbox")

        events = (project / ".pf" / "runtime" / "events" / "events.ndjson").read_text(encoding="utf-8")
        for marker in [
            "project.onboarding.started",
            "project.flow_root.created",
            "project.snapshot.refreshed",
            "launcher.project_runtime.created",
            "agent.start_prompt.generated",
            "project.doctor.passed",
            "assignment.created",
            "project.onboarding.completed",
        ]:
            if marker not in events:
                raise AssertionError(f"missing project event: {marker}")

        outbox = project / ".pf" / "runtime" / "hooks" / "outbox" / "wtaicc"
        if not any(outbox.glob("*.json")):
            raise AssertionError("hooks-dispatch did not write first-run outbox payload")

        local_config = project / ".pf" / "process-forge.local.yaml"
        original_local = local_config.read_text(encoding="utf-8", errors="replace")
        broken_local = "\n".join(
            "  distribution_override: ./missing-processforge-distribution"
            if line.strip().startswith("distribution_override:")
            else line
            for line in original_local.splitlines()
        ) + "\n"
        local_config.write_text(broken_local, encoding="utf-8")
        env = dict(os.environ)
        env.pop("PROCESSFORGE_HOME", None)
        failed = run_python(
            project / ".pf" / "runtime" / "bin" / "pf.py",
            "doctor-project",
            "--project-root",
            ".",
            cwd=project,
            env=env,
            expect_success=False,
        )
        if "FAIL: ProcessForge CLI not found" not in failed.stdout and "FAIL: ProcessForge distribution not found" not in failed.stdout:
            raise AssertionError("broken launcher did not produce a clear FAIL message")
        local_config.write_text(original_local, encoding="utf-8")

    print("PASS: first-run smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
