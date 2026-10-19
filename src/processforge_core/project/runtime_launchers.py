"""Existing project-local launcher templates, without installation or execution."""

from __future__ import annotations

from pathlib import Path


class ProjectRuntimeLauncherBuilder:
    """Build the existing Python, shell and Windows launcher file contents."""

    def project_runtime_launcher_files(self, flow_root: Path) -> dict[Path, str]:
        launcher_py = r'''#!/usr/bin/env python3
"""Project-local ProcessForge launcher.

This file lives under .pf/runtime/ and may read private local paths from
.pf/process-forge.local.yaml. Public project files should use `pf` or this
launcher without exposing resolved local paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def project_marker(path: Path) -> bool:
    return (path / ".pf" / "process-forge.local.yaml").is_file()


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    if project_marker(current):
        return current
    script_path = Path(__file__).resolve()
    script_project = script_path.parents[3] if len(script_path.parents) > 3 else None
    if script_project and project_marker(script_project):
        return script_project
    for candidate in [current, *current.parents, *script_path.parents]:
        if project_marker(candidate):
            return candidate
    return None


def yaml_scalar(text: str, key: str) -> str | None:
    prefix = key + ":"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped[len(prefix) :].strip()
            if value in {"", "null", "None", "~"}:
                return None
            return value.strip("'\"")
    return None


def resolve_path(base: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def exec_args(args: list[str]) -> list[str]:
    if os.name != "nt":
        return args
    return [subprocess.list2cmdline([arg]) for arg in args]


def exec_processforge(cli: Path, argv: list[str]) -> int:
    args = exec_args([sys.executable, str(cli), *argv])
    if os.name == "nt":
        return os.spawnv(os.P_WAIT, sys.executable, args)
    os.execv(sys.executable, args)
    return 2


def distribution_from_workplace(workplace_manifest: Path) -> Path | None:
    registry = workplace_manifest.parent / "registries" / "distributions.yaml"
    if not registry.is_file():
        return None
    lines = registry.read_text(encoding="utf-8", errors="replace").splitlines()
    in_processforge = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("id:"):
            in_processforge = stripped.split(":", 1)[1].strip().strip("'\"") == "processforge"
        elif in_processforge and stripped.startswith("path:"):
            raw = stripped.split(":", 1)[1].strip().strip("'\"")
            raw = raw.replace("${PF_WORKPLACE}", str(workplace_manifest.parent))
            return resolve_path(workplace_manifest.parent, raw)
    return None


def distribution_root(project_root: Path) -> Path | None:
    env_home = os.environ.get("PROCESSFORGE_HOME")
    local_manifest = project_root / ".pf" / "process-forge.local.yaml"
    if local_manifest.is_file():
        text = local_manifest.read_text(encoding="utf-8", errors="replace")
        override = yaml_scalar(text, "distribution_override")
        if override:
            return resolve_path(local_manifest.parent, override)
        workplace_raw = yaml_scalar(text, "manifest")
        if workplace_raw:
            workplace = resolve_path(local_manifest.parent, workplace_raw)
            found = distribution_from_workplace(workplace)
            if found:
                return found
    if env_home:
        return Path(env_home).expanduser().resolve()
    return None


def main(argv: list[str]) -> int:
    project_root = find_project_root(Path.cwd())
    if project_root is None:
        message = """FAIL: ProcessForge project root not found.

Fix:
  Run this launcher from a ProcessForge project root, pass --project-root to the command, or rerun project-onboard."""
        print(message, file=sys.stderr)
        return 1
    distribution = distribution_root(project_root)
    if not distribution:
        message = """FAIL: ProcessForge distribution not found.

Fix:
  Set PROCESSFORGE_HOME to the ProcessForge distribution root, or rerun project-onboard from the distribution."""
        print(message, file=sys.stderr)
        return 1
    cli = distribution / "tools" / "processforge.py"
    if not cli.is_file():
        message = f"""FAIL: ProcessForge CLI not found under distribution root: {distribution}

Fix:
  Check PROCESSFORGE_HOME or rerun project-onboard so .pf/process-forge.local.yaml points to a valid distribution."""
        print(message, file=sys.stderr)
        return 1
    try:
        return exec_processforge(cli, argv)
    except OSError as exc:
        print("FAIL: could not exec ProcessForge CLI", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
        launcher_sh = """#!/usr/bin/env sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/pf.py" "$@"
fi
exec python "$SCRIPT_DIR/pf.py" "$@"
"""
        launcher_bat = """@echo off
set SCRIPT_DIR=%~dp0
py -3 "%SCRIPT_DIR%pf.py" %*
if errorlevel 9009 python "%SCRIPT_DIR%pf.py" %*
"""
        return {
            flow_root / "runtime" / "bin" / "pf.py": launcher_py,
            flow_root / "runtime" / "bin" / "pf": launcher_sh,
            flow_root / "runtime" / "bin" / "pf.bat": launcher_bat,
        }
