#!/usr/bin/env python3
"""Run a Codex CLI worker from a ProcessForge worker prompt and capsule."""

from __future__ import annotations

import argparse
import hashlib
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


def codex_config_args(*, effort: str, memories: str) -> list[str]:
    """Build non-interactive Codex overrides for a governed PF worker."""
    args: list[str] = []
    if effort:
        args.extend(["-c", f'model_reasoning_effort="{effort}"'])
    if memories == "false":
        args.extend(["-c", "features.memories=false"])
    # ProcessForge is a local, assignment-scoped control plane. Without this
    # override Codex discovers pf.* tools but cannot call them under the
    # non-interactive `never` approval policy used by shell workers.
    args.extend(["-c", 'mcp_servers.processforge.default_tools_approval_mode="approve"'])
    return args


def managed_hook_trust_args(project_root: Path) -> list[str]:
    """Trust hooks only when the project config contains PF handlers exclusively."""
    target = project_root / ".codex" / "hooks.json"
    adapter = Path(__file__).resolve().parent / "pf_runtime" / "codex_hooks.py"
    expected_command = f'py -3 "{adapter}"'
    required_events = {
        "SessionStart",
        "SessionEnd",
        "PostToolUse",
        "UserPromptSubmit",
        "PreCompact",
        "PostCompact",
        "Stop",
        "SubagentStop",
    }
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    hooks = payload.get("hooks") if isinstance(payload, dict) else None
    if not isinstance(hooks, dict) or not required_events.issubset(hooks):
        return []
    found_events: set[str] = set()
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            return []
        for group in groups:
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                return []
            for handler in handlers:
                if not isinstance(handler, dict) or handler.get("type") != "command":
                    return []
                if str(handler.get("command") or "") != expected_command:
                    return []
                if str(handler.get("commandWindows") or "") != expected_command:
                    return []
                found_events.add(str(event))
    if not required_events.issubset(found_events):
        return []
    return ["--dangerously-bypass-hook-trust"]


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


def capture_worker_input(payload_text: str, output: Path) -> dict[str, Any]:
    """Persist the exact PF-owned launch payload before starting Codex.

    The raw envelope is private.  The derived system message deliberately
    contains only stable ids, a digest and a repository-relative report ref.
    """

    import processforge as core
    from pf_runtime import host

    project_root = Path(os.environ.get("PF_PROJECT_ROOT") or Path.cwd()).resolve()
    run_id = str(os.environ.get("PF_RUN_ID") or os.environ.get("PF_WORKER_RUN_ID") or "")
    task_id = str(os.environ.get("PF_TASK_ID") or os.environ.get("PF_WORKER_TASK_ID") or "")
    attempt = str(os.environ.get("PF_WORKER_ATTEMPT") or "1")
    if not run_id or not task_id:
        # The helper remains usable by the pre-existing direct CLI smoke.  A
        # prepared ProcessForge worker always has both ids and therefore
        # cannot silently bypass the fail-closed ingress capture below.
        if os.environ.get("PF_AGENT_RUN_DIR"):
            raise SystemExit("FAIL: PF worker input capture requires run and task ids")
        return {"accepted": True, "chat_message_ids": []}
    try:
        expected_report = output.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise SystemExit("FAIL: expected report must remain inside the project") from exc
    payload_hash = "sha256:" + hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
    session_id = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"
    summary = host.worker_input_summary(run_id, task_id, attempt, payload_hash, expected_report)
    agent_run_dir_raw = os.environ.get("PF_AGENT_RUN_DIR") or ""
    if not agent_run_dir_raw:
        raise SystemExit("FAIL: PF worker input capture requires PF_AGENT_RUN_DIR")
    agent_run_dir = Path(agent_run_dir_raw).resolve()
    expected_run_dir = project_root / ".pf" / "runtime" / "agent-runs" / core.safe_id(run_id, "run") / core.safe_id(task_id, "task")
    if agent_run_dir != expected_run_dir.resolve():
        raise SystemExit("FAIL: PF worker input capture run directory does not match run/task identity")
    input_contract = {"schema_version": 1, "run_id": run_id, "task_id": task_id, "attempt": attempt, "stdin_payload_hash": payload_hash, "expected_report": expected_report, "summary": summary}
    contract_path = agent_run_dir / "worker-input-contract.json"
    contract_tmp = contract_path.with_suffix(".json.tmp")
    contract_tmp.write_text(json.dumps(input_contract, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    contract_tmp.replace(contract_path)
    envelope = {
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerPromptPayloadSubmitted",
        "native_event_id": f"worker-input:{run_id}:{task_id}:attempt:{attempt}",
        "native_id_scope": "project",
        "native_event_id_stable": True,
        "source_session_id": session_id,
        "source_project_ref": str(project_root),
        "payload_version": "1",
        "raw_payload": {
            "run_id": run_id,
            "task_id": task_id,
            "attempt": attempt,
            "stdin_payload": payload_text,
            "stdin_payload_hash": payload_hash,
            "expected_report": expected_report,
        },
        "derived_conversation_messages": [
            {
                "message_role": "system",
                "participant": {"id": "processforge-runtime", "type": "agent", "role": "worker_launcher"},
                "session_id": session_id,
                "turn_id": f"worker-turn:{run_id}:{task_id}:attempt:{attempt}",
                "content": summary,
                "content_source": {"kind": "pf_codex_exec_input", "provider": "processforge", "adapter": "pf-codex-exec-worker", "native_event_type": "WorkerPromptPayloadSubmitted", "content_provenance": "pf_owned_safe_summary"},
                "delivery": {"state": "complete", "sequence": 0, "final": True},
            }
        ],
    }
    workplace_root = core.resolve_workplace_root(None, project_root=project_root)
    result = host.ingest_event(envelope, workplace_root, core)
    if not result.get("accepted") or len(result.get("chat_message_ids") or []) != 1:
        raise SystemExit("FAIL: PF worker input conversation capture was not accepted")
    return result


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
    memories = (os.environ.get("PF_CODEX_MEMORIES") or "false").strip().lower()
    if memories not in {"true", "false"}:
        raise SystemExit("FAIL: PF_CODEX_MEMORIES must be true or false")
    project_root = os.environ.get("PF_PROJECT_ROOT") or str(Path.cwd())
    add_dirs = resolved_workspace_dirs(workspace_access)
    extra_read_dir = os.environ.get("PF_CODEX_EXTRA_READ_DIR")
    if extra_read_dir:
        extra = Path(extra_read_dir).expanduser()
        if extra.exists():
            add_dirs.append(extra)

    project_path = Path(project_root).expanduser().resolve()
    command = [codex_executable(), *managed_hook_trust_args(project_path), "exec"]
    command.extend([
        "-m",
        model,
        "--sandbox",
        sandbox,
        "--cd",
        project_root,
    ])
    config_args = codex_config_args(effort=effort, memories=memories)
    command.extend(config_args)
    for path in add_dirs:
        command.extend(["--add-dir", str(path)])
    command.extend(["-o", str(output), "-"])

    output.parent.mkdir(parents=True, exist_ok=True)
    write_heartbeat(heartbeat, "starting", {"model": model, "workspace_dirs": [str(path) for path in add_dirs]})
    # Codex CLI reads its stdin as UTF-8.  ``text=True`` would encode this
    # payload with the Windows console/code-page default, corrupting a valid
    # non-ASCII assignment (for example a Russian project path) before the
    # CLI receives it.  Supply explicit UTF-8 bytes instead.
    payload_text = prompt_payload(worker_prompt, capsule, workspace_access)
    capture_worker_input(payload_text, output)
    result = subprocess.run(
        command,
        input=payload_text.encode("utf-8"),
        check=False,
    )
    write_exit_contract(exit_contract, int(result.returncode))
    write_heartbeat(heartbeat, "completed" if result.returncode == 0 else "failed", {"exit_code": result.returncode})
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
