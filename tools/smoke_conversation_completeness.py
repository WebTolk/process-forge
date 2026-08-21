#!/usr/bin/env python3
"""Focused proof for private, idempotent conversation capture."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Iterator

from codex_exec_worker import capture_worker_input, prompt_payload
from processforge_subprocess import diagnostic_text, run_command
from pf_runtime.codex_hooks import native_envelope
from pf_runtime.host import worker_input_summary


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "processforge.py"


def pf(*args: str, expect: int = 0) -> str:
    result = run_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=120)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}: {' '.join(args)}\n{diagnostic_text(result)}")
    return result.stdout


def write(path: Path, value: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def event(workplace: Path, payload: dict[str, object], path: Path) -> dict[str, object]:
    return json.loads(pf("runtime-host", "event", "--workplace", str(workplace), "--input", str(write(path, payload)), "--json"))


def transcript(project: Path, session: str) -> list[dict[str, object]]:
    root = project / ".pf" / "runtime" / "chat" / "transcripts"
    if not root.is_dir():
        return []
    rows: list[dict[str, object]] = []
    for path in sorted(root.glob("*.ndjson")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            if row.get("session_id") == session:
                rows.append(row)
    return rows


def events(project: Path) -> list[dict[str, object]]:
    path = project / ".pf" / "runtime" / "events" / "events.ndjson"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line] if path.is_file() else []


def events_text(project: Path) -> str:
    path = project / ".pf" / "runtime" / "events" / "events.ndjson"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def chat_event_id(message_id: str) -> str:
    return "evt_" + hashlib.sha256(("chat.message.recorded:" + message_id).encode("utf-8")).hexdigest()[:32]


def event_count(project: Path, event_id: str) -> int:
    return sum(1 for item in events(project) if item.get("event_id") == event_id)


def remove_event(project: Path, event_id: str) -> None:
    path = project / ".pf" / "runtime" / "events" / "events.ndjson"
    lines = path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    removed = 0
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if item.get("event_id") == event_id:
            removed += 1
        else:
            kept.append(line)
    if removed != 1:
        raise AssertionError(f"expected to remove one event {event_id}, removed {removed}")
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


@contextlib.contextmanager
def patched_env(values: dict[str, str]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def assert_no_extra_content(project: Path, forbidden: list[str]) -> None:
    outbox = project / ".pf" / "runtime" / "hooks" / "outbox"
    visible = "\n".join(
        [
            events_text(project),
            "\n".join(
                path.read_text(encoding="utf-8", errors="replace")
                for path in sorted(outbox.glob("*.json"))
            ) if outbox.is_dir() else "",
        ]
    )
    for marker in forbidden:
        if marker in visible:
            raise AssertionError(f"forbidden marker leaked into project-visible runtime output: {marker}")


def setup_basic_project(root: Path, name: str) -> tuple[Path, Path]:
    workplace, project = root / f"{name}-workplace", root / name
    project.mkdir()
    (project / "README.md").write_text("# fixture\n", encoding="utf-8")
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    pf("project-onboard", "--project-root", str(project), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    return workplace, project


def setup_worker_project(root: Path) -> tuple[Path, Path, Path, str, str, str, str]:
    workplace, project = setup_basic_project(root, "worker-project")
    second = root / "foreign-project"
    second.mkdir()
    (second / "README.md").write_text("# foreign\n", encoding="utf-8")
    pf("project-onboard", "--project-root", str(second), "--workplace", str(workplace), "--type", "generic-software-project", "--apply")
    run_id, task_id = "worker-run", "worker-task"
    report_rel = ".pf/artifacts/worker-report.md"
    pf("run-create", "--project-root", str(project), "--id", run_id, "--title", "Worker smoke", "--process", "task-batch-execution", "--apply")
    pf(
        "task-create",
        "--project-root",
        str(project),
        "--run",
        run_id,
        "--id",
        task_id,
        "--title",
        "Worker task",
        "--process",
        "prompt-only",
        "--execution-mode",
        "implementation",
        "--allowed-file",
        report_rel,
        "--required-output",
        f"id=worker-report,path={report_rel}",
        "--expected-report-language",
        "ru",
        "--expected-report-artifact",
        report_rel,
        "--apply",
    )
    pf("worker-run", "prepare", "--project-root", str(project), "--task", task_id, "--driver", "manual")
    return workplace, project, second, run_id, task_id, "1", report_rel


def worker_input_capture(project: Path, run_id: str, task_id: str, attempt: str, report_rel: str) -> dict[str, object]:
    state_root = project / ".pf" / "runtime" / "agent-runs" / run_id / task_id
    payload = prompt_payload(
        project / ".pf" / "runs" / run_id / "worker-prompts" / f"{task_id}.md",
        project / ".pf" / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml",
        state_root / "workspace-access.json",
    )
    with patched_env({"PF_PROJECT_ROOT": str(project), "PF_RUN_ID": run_id, "PF_TASK_ID": task_id, "PF_WORKER_ATTEMPT": attempt, "PF_AGENT_RUN_DIR": str(state_root)}):
        return capture_worker_input(payload, project / report_rel)


def worker_envelope(
    project: Path,
    run_id: str,
    task_id: str,
    attempt: str,
    report_rel: str,
    event_type: str,
    content: str,
    *,
    source_project: Path | None = None,
    source_session: str | None = None,
    content_source: dict[str, object] | None = None,
    raw_extra: dict[str, object] | None = None,
    native_event_id: str | None = None,
) -> dict[str, object]:
    role = "assistant" if event_type == "WorkerExpectedReportCaptured" else "system"
    kind = "pf_codex_exec_output" if role == "assistant" else "pf_codex_exec_input"
    provenance = "pf_owned_output_file" if role == "assistant" else "pf_owned_safe_summary"
    raw_payload: dict[str, object] = {
        "run_id": run_id,
        "task_id": task_id,
        "attempt": attempt,
        "expected_report": report_rel,
    }
    if role == "assistant":
        raw_payload.update({"report_content": content, "report_hash": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()})
    else:
        raw_payload.update({"stdin_payload": "payload", "stdin_payload_hash": "sha256:" + hashlib.sha256(b"payload").hexdigest()})
    raw_payload.update(raw_extra or {})
    session = source_session if source_session is not None else f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"
    return {
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": event_type,
        "native_event_id": native_event_id or f"smoke:{event_type}:{run_id}:{task_id}:{attempt}:{hashlib.sha256(json.dumps(raw_payload, sort_keys=True).encode('utf-8')).hexdigest()}",
        "native_id_scope": "project",
        "native_event_id_stable": True,
        "source_session_id": session,
        "source_project_ref": str(source_project or project),
        "payload_version": "1",
        "raw_payload": raw_payload,
        "derived_conversation_messages": [
            {
                "message_role": role,
                "participant": {"id": "smoke-worker", "type": "agent", "role": "worker"},
                "session_id": session,
                "turn_id": f"worker-turn:{run_id}:{task_id}:attempt:{attempt}",
                "content": content,
                "content_source": content_source
                or {
                    "kind": kind,
                    "provider": "processforge",
                    "adapter": "pf-codex-exec-worker",
                    "native_event_type": event_type,
                    "content_provenance": provenance,
                },
                "delivery": {"state": "complete", "sequence": 1 if role == "assistant" else 0, "final": True},
            }
        ],
    }


def assert_denied(result: dict[str, object], reason: str) -> None:
    diagnostics = result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else {}
    conversation = diagnostics.get("conversation") if isinstance(diagnostics.get("conversation"), dict) else {}
    if not result.get("accepted") or result.get("chat_message_ids") != [] or conversation.get("reason") != reason:
        raise AssertionError(f"expected denied reason={reason}, got {json.dumps(result, ensure_ascii=False, sort_keys=True)}")


def deliver_parallel(workplace: Path, payload: dict[str, object], first: Path, second: Path) -> list[dict[str, object]]:
    write(first, payload)
    write(second, payload)
    commands = [
        [sys.executable, str(CLI), "runtime-host", "event", "--workplace", str(workplace), "--input", str(first), "--json"],
        [sys.executable, str(CLI), "runtime-host", "event", "--workplace", str(workplace), "--input", str(second), "--json"],
    ]
    processes = [subprocess.Popen(command, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") for command in commands]
    results: list[dict[str, object]] = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=120)
        if process.returncode != 0:
            raise AssertionError(f"parallel delivery failed rc={process.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")
        results.append(json.loads(stdout))
    return results


def smoke_codex_user_prompt(root: Path) -> None:
    workplace, project = setup_basic_project(root, "codex-project")
    session = "conversation-session"
    started = {
        "provider": "codex", "adapter": "codex-hooks", "native_event_type": "SessionStart",
        "native_event_id": None, "native_id_scope": "session", "native_event_id_stable": False,
        "source_session_id": session, "source_project_ref": str(project), "payload_version": "1",
        "raw_payload": {"hook_event_name": "SessionStart", "cwd": str(project), "session_id": session},
        "derived_event": {"schema_version": 1, "event_type": "agent.session.started", "event_id": "conversation-start", "project_root": str(project), "session_id": session, "agent_id": "codex", "source": {"adapter": "codex-hooks", "session_id": session}},
    }
    assert event(workplace, started, root / "start.json")["accepted"]

    prompt = native_envelope({"hook_event_name": "UserPromptSubmit", "cwd": str(project), "session_id": session, "turn_id": "turn-1", "prompt": "Hello, capture this."})
    assert prompt is not None
    first = event(workplace, prompt, root / "prompt.json")
    repeated = event(workplace, prompt, root / "prompt-repeat.json")
    assert len(first["chat_message_ids"]) == 1 and first["chat_message_ids"] == repeated["chat_message_ids"]
    rows = transcript(project, session)
    assert len(rows) == 1 and rows[0]["message"]["role"] == "user"
    assert "Hello, capture this." not in events_text(project) and '"content_mode": "metadata_only"' in events_text(project)

    unsafe = {**prompt, "native_event_type": "Unsafe", "raw_payload": {"value": "kept raw"}, "derived_conversation_messages": [{"message_role": "system", "participant": {"id": "system", "type": "system", "role": "system"}, "content": "C:\\Users\\private", "content_source": {"kind": "automatic"}}]}
    denied = event(workplace, unsafe, root / "unsafe.json")
    assert_denied(denied, "untrusted_conversation_provenance")
    assert len(transcript(project, session)) == 1

    lifecycle = native_envelope({"hook_event_name": "SessionEnd", "cwd": str(project), "session_id": session})
    assert lifecycle is not None
    event(workplace, lifecycle, root / "end.json")
    assert len(transcript(project, session)) == 1
    pf("events-validate", "--project-root", str(project))


def smoke_worker_capture(root: Path) -> None:
    workplace, project, second, run_id, task_id, attempt, report_rel = setup_worker_project(root)
    session = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"

    input_result = worker_input_capture(project, run_id, task_id, attempt, report_rel)
    repeated_input = worker_input_capture(project, run_id, task_id, attempt, report_rel)
    assert len(input_result["chat_message_ids"]) == 1 and input_result["chat_message_ids"] == repeated_input["chat_message_ids"]
    rows = transcript(project, session)
    assert len(rows) == 1 and rows[0]["message"]["role"] == "system"
    input_message = str(input_result["chat_message_ids"][0])
    input_event = chat_event_id(input_message)
    assert event_count(project, input_event) == 1
    input_payload = prompt_payload(
        project / ".pf" / "runs" / run_id / "worker-prompts" / f"{task_id}.md",
        project / ".pf" / "contexts" / "assignment-capsules" / f"{task_id}.capsule.yaml",
        project / ".pf" / "runtime" / "agent-runs" / run_id / task_id / "workspace-access.json",
    )
    input_hash = "sha256:" + hashlib.sha256(input_payload.encode("utf-8")).hexdigest()
    input_summary = worker_input_summary(run_id, task_id, attempt, input_hash, report_rel)
    input_raw = {"stdin_payload": input_payload, "stdin_payload_hash": input_hash}

    remove_event(project, input_event)
    recovered_input = worker_input_capture(project, run_id, task_id, attempt, report_rel)
    assert recovered_input["chat_message_ids"] == input_result["chat_message_ids"]
    assert len(transcript(project, session)) == 1 and event_count(project, input_event) == 1

    forged_source = {
        "kind": "pf_codex_exec_input",
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerPromptPayloadSubmitted",
        "content_provenance": "operator_prompt",
    }
    forged = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerPromptPayloadSubmitted", input_summary, content_source=forged_source, raw_extra=input_raw),
        root / "forged-provenance.json",
    )
    assert_denied(forged, "untrusted_conversation_provenance")
    assert len(transcript(project, session)) == 1

    forged_safe_summary = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerPromptPayloadSubmitted", "forged safe system summary", raw_extra=input_raw),
        root / "forged-safe-summary.json",
    )
    assert_denied(forged_safe_summary, "untrusted_conversation_provenance")

    alternate_input_id = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerPromptPayloadSubmitted", input_summary, raw_extra=input_raw, native_event_id=f"worker-input:{run_id}:{task_id}:attempt:{attempt}:forged"),
        root / "alternate-input-id.json",
    )
    assert_denied(alternate_input_id, "untrusted_conversation_provenance")

    missing_session = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerPromptPayloadSubmitted", "safe worker summary", source_session=""),
        root / "missing-session.json",
    )
    assert_denied(missing_session, "missing_session")

    wrong_attempt = event(
        workplace,
        worker_envelope(project, run_id, task_id, "2", report_rel, "WorkerPromptPayloadSubmitted", "safe worker summary"),
        root / "wrong-attempt.json",
    )
    assert_denied(wrong_attempt, "session_not_authorized")

    foreign = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerPromptPayloadSubmitted", "safe worker summary", source_project=second),
        root / "foreign-project.json",
    )
    assert_denied(foreign, "session_not_authorized")
    assert transcript(second, session) == []

    concurrent_payload = worker_envelope(
        project,
        run_id,
        task_id,
        attempt,
        report_rel,
        "WorkerPromptPayloadSubmitted",
        input_summary,
        raw_extra=input_raw,
        native_event_id=f"worker-input:{run_id}:{task_id}:attempt:{attempt}",
    )
    parallel = deliver_parallel(workplace, concurrent_payload, root / "parallel-a.json", root / "parallel-b.json")
    ids = [item.get("chat_message_ids") for item in parallel]
    assert len(ids[0]) == 1 and ids[0] == ids[1]
    concurrent_message = str(ids[0][0])
    assert sum(1 for row in transcript(project, session) if row.get("message_id") == concurrent_message) == 1
    assert event_count(project, chat_event_id(concurrent_message)) == 1

    report_content = "# Smoke worker report\n\nExact expected report content; workspace-access markers were withheld.\n"
    (project / report_rel).parent.mkdir(parents=True, exist_ok=True)
    (project / report_rel).write_text(report_content, encoding="utf-8")
    alternate_output_id = event(
        workplace,
        worker_envelope(project, run_id, task_id, attempt, report_rel, "WorkerExpectedReportCaptured", report_content, native_event_id=f"worker-output:{run_id}:{task_id}:attempt:{attempt}:forged"),
        root / "alternate-output-id.json",
    )
    assert_denied(alternate_output_id, "untrusted_conversation_provenance")
    collect = pf("worker-run", "collect", "--project-root", str(project), "--task", task_id)
    assert "DONE: worker-task" in collect
    rows = transcript(project, session)
    assistant = [row for row in rows if row.get("message", {}).get("role") == "assistant"]
    assert len(assistant) == 1 and assistant[0]["message"]["content"] == report_content
    assert "Exact expected report content." not in events_text(project)
    assert_no_extra_content(project, ["workspace-access", "workspace_access", "assignment capsule", "C:\\Users\\private"])
    pf("events-validate", "--project-root", str(project))
    pf("events-validate", "--project-root", str(second))


def main() -> int:
    tmp_root = ROOT / ".tmp"
    tmp_root.mkdir(exist_ok=True)
    root = tmp_root / f"pf-conversation-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        smoke_codex_user_prompt(root)
        smoke_worker_capture(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS: conversation completeness smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
