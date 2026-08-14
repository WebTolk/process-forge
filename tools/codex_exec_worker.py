#!/usr/bin/env python3
"""Run a Codex CLI worker from a ProcessForge worker prompt and capsule."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def resolved_workspace_dirs(workspace_access: Path) -> list[Path]:
    if not workspace_access.is_file():
        return []
    data = json.loads(workspace_access.read_text(encoding="utf-8"))
    grants = data.get("grants") if isinstance(data.get("grants"), dict) else {}
    paths: list[Path] = []
    for items in grants.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            resolution = item.get("resolution") if isinstance(item.get("resolution"), dict) else {}
            if str(resolution.get("status") or "") not in {"resolved", "missing"}:
                continue
            raw_path = resolution.get("path")
            if not raw_path:
                continue
            path = Path(str(raw_path)).expanduser()
            if path.is_file():
                path = path.parent
            if path.exists() and path not in paths:
                paths.append(path)
    return paths


def codex_executable() -> str:
    explicit = os.environ.get("PF_CODEX_EXECUTABLE") or os.environ.get("CODEX_EXECUTABLE")
    if explicit:
        return explicit
    found = shutil.which("codex") or shutil.which("codex.cmd")
    if not found:
        raise SystemExit("FAIL: codex executable not found; set PF_CODEX_EXECUTABLE or install Codex CLI")
    return found


def prompt_payload(worker_prompt: Path, capsule: Path, workspace_access: Path) -> str:
    return "\n".join(
        [
            read_text(worker_prompt).rstrip(),
            "",
            "## Output Delivery Contract",
            "",
            "Your final response is captured verbatim as the assignment's expected report artifact.",
            "Return only the complete report content in the requested format; do not say that you saved it, link to it, or add a conversational preface.",
            "For a read-only assignment, do not attempt to write the report file yourself.",
            "",
            "## Assignment Capsule",
            "",
            read_text(capsule).rstrip(),
            "",
            "## Workspace Access File",
            "",
            str(workspace_access),
            "",
        ]
    )


def write_heartbeat(path: Path | None, status: str, extra: dict[str, Any] | None = None) -> None:
    if not path:
        return
    payload = {"status": status, **(extra or {})}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_exit_contract(path: Path | None, returncode: int) -> None:
    """Publish the durable completion fact required by detached Inspector runs."""
    if not path:
        return
    status = "completed" if returncode == 0 else "failed"
    payload = {"schema_version": 1, "exit_code": returncode, "status": status}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-prompt", required=True)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--workspace-access", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--heartbeat")
    args = parser.parse_args()

    worker_prompt = Path(args.worker_prompt).expanduser().resolve()
    capsule = Path(args.capsule).expanduser().resolve()
    workspace_access = Path(args.workspace_access).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    heartbeat = Path(args.heartbeat).expanduser().resolve() if args.heartbeat else None
    exit_contract = Path(os.environ["PF_AGENT_EXIT_PATH"]).expanduser().resolve() if os.environ.get("PF_AGENT_EXIT_PATH") else None

    model = os.environ.get("PF_AGENT_MODEL") or os.environ.get("PF_CODEX_MODEL") or ""
    if not model:
        raise SystemExit("FAIL: Codex model is not configured; set PF_AGENT_MODEL through the orchestrator or PF_CODEX_MODEL")
    effort = os.environ.get("PF_CODEX_REASONING_EFFORT") or ""
    sandbox = os.environ.get("PF_CODEX_SANDBOX") or "read-only"
    project_root = os.environ.get("PF_PROJECT_ROOT") or str(Path.cwd())
    add_dirs = resolved_workspace_dirs(workspace_access)
    extra_read_dir = os.environ.get("PF_CODEX_EXTRA_READ_DIR")
    if extra_read_dir:
        extra = Path(extra_read_dir).expanduser()
        if extra.exists():
            add_dirs.append(extra)

    command = [
        codex_executable(),
        "exec",
        "-m",
        model,
        "--sandbox",
        sandbox,
        "--cd",
        project_root,
    ]
    if effort:
        command[4:4] = ["-c", f'model_reasoning_effort="{effort}"']
    for path in add_dirs:
        command.extend(["--add-dir", str(path)])
    command.extend(["-o", str(output), "-"])

    output.parent.mkdir(parents=True, exist_ok=True)
    write_heartbeat(heartbeat, "starting", {"model": model, "workspace_dirs": [str(path) for path in add_dirs]})
    # Codex CLI reads its stdin as UTF-8.  ``text=True`` would encode this
    # payload with the Windows console/code-page default, corrupting a valid
    # non-ASCII assignment (for example a Russian project path) before the
    # CLI receives it.  Supply explicit UTF-8 bytes instead.
    result = subprocess.run(
        command,
        input=prompt_payload(worker_prompt, capsule, workspace_access).encode("utf-8"),
        check=False,
    )
    write_exit_contract(exit_contract, int(result.returncode))
    write_heartbeat(heartbeat, "completed" if result.returncode == 0 else "failed", {"exit_code": result.returncode})
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
