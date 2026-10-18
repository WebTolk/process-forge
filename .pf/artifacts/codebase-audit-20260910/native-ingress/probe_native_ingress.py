"""Isolated, read-only reproducer for native worker report ingress.

The probe imports the current source at execution time and uses only disposable
system temporary files plus a small fake Core/RawIngress boundary. It does not
write product or PF runtime state.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[4]
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from pf_runtime import host  # noqa: E402
import processforge as pf  # noqa: E402


class FakeCore:
    PROCESSFORGE_VERSION = "fixture"

    def __init__(self, project: Path, task: dict[str, object]) -> None:
        self.project = project
        self.task = task
        self.messages: list[dict[str, object]] = []

    def require_flow_root(self, _root: Path) -> None:
        return None

    def resolve_workplace_root(self, _value: object, *, project_root: Path | None = None) -> Path:
        return (project_root or self.project) / "workplace"

    def project_id(self, _root: Path) -> str:
        return "fixture-project"

    def load_task(self, _root: Path, _task_id: str) -> dict[str, object]:
        return self.task

    def load_agent_run_state(self, _root: Path, _run_id: str, _task_id: str) -> dict[str, object]:
        return {"attempt": "1", "status": "completed"}

    def update_stale_agent_presence(self, _workplace: Path) -> None:
        return None

    def find_agent_presence(self, _workplace: Path, *, session_id: str) -> dict[str, object]:
        return {}

    def contains_secret_value(self, _content: str) -> bool:
        return False

    def append_chat_message(self, _root: Path, **kwargs: object):
        message_id = str(kwargs["message_id"])
        record = {"message_id": message_id, "message": {"role": kwargs["message_role"], "content": kwargs["content"]}}
        self.messages.append(record)
        return Path("fixture-transcript"), record, {}


class FakeIngress:
    receipts: list[SimpleNamespace] = []
    calls = 0
    last_event: object | None = None

    def __init__(self, _workplace: Path) -> None:
        return None

    def ingest(self, _event: object) -> SimpleNamespace:
        type(self).last_event = _event
        receipt = type(self).receipts[min(type(self).calls, len(type(self).receipts) - 1)]
        type(self).calls += 1
        return receipt


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def worker_envelope(project: Path, expected_report: str, content: str) -> dict[str, object]:
    run_id, task_id, attempt = "run-fixture", "task-fixture", "1"
    report_hash = sha256_text(content)
    session_id = f"pf-worker:{run_id}:{task_id}:attempt:{attempt}"
    return {
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerExpectedReportCaptured",
        "native_event_id": f"worker-output:{run_id}:{task_id}:attempt:{attempt}:{report_hash}",
        "native_id_scope": "project",
        "native_event_id_stable": True,
        "source_session_id": session_id,
        "source_project_ref": str(project),
        "payload_version": "1",
        "raw_payload": {
            "run_id": run_id,
            "task_id": task_id,
            "attempt": attempt,
            "expected_report": expected_report,
            "report_content": content,
            "report_hash": report_hash,
        },
        "derived_conversation_messages": [{
            "message_role": "assistant",
            "participant": {"id": "worker", "type": "agent", "role": "worker"},
            "session_id": session_id,
            "turn_id": f"worker-turn:{run_id}:{task_id}:attempt:{attempt}",
            "content": content,
            "content_source": {
                "kind": "pf_codex_exec_output",
                "provider": "processforge",
                "adapter": "pf-codex-exec-worker",
                "native_event_type": "WorkerExpectedReportCaptured",
                "content_provenance": "pf_owned_output_file",
            },
            "delivery": {"state": "complete", "sequence": 1, "final": True},
        }],
    }


def run() -> dict[str, object]:
    original_kernel = host.RawIngressKernel
    results: dict[str, object] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="pf-native-ingress-") as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            (project / ".pf" / "artifacts").mkdir(parents=True)

            path_report = "# Worker report\n\nSource: C:\\workspace\\src\\module.py\n"
            path_report_rel = ".pf/artifacts/path-report.md"
            path_report_file = project / path_report_rel
            path_report_file.write_text(path_report, encoding="utf-8")
            task = {
                "id": "task-fixture",
                "run_id": "run-fixture",
                "expected_report": {"artifact": path_report_rel},
            }
            core = FakeCore(project, task)
            raw_id = "raw-worker-output-fixture"
            FakeIngress.calls = 0
            FakeIngress.receipts = [
                SimpleNamespace(raw_event_id=raw_id, accepted=True, deduplicated=False, raw_location="fixture:0", routing_status="raw_accepted", normalized_event_ids=[], chat_message_ids=[], diagnostics={}),
                SimpleNamespace(raw_event_id=raw_id, accepted=True, deduplicated=True, raw_location="fixture:0", routing_status="duplicate_raw", normalized_event_ids=[], chat_message_ids=[], diagnostics={}),
            ]
            host.RawIngressKernel = FakeIngress
            envelope = worker_envelope(project, path_report_rel, path_report)
            authorized = host._allowed_conversation_message(envelope, envelope["derived_conversation_messages"][0])
            first = host.ingest_event(envelope, root / "workplace", core, project_ref=str(project))
            second = host.ingest_event(envelope, root / "workplace", core, project_ref=str(project))
            results["path_report"] = {
                "provenance_authorized_before_safety": authorized,
                "first": first,
                "retry": second,
                "captured_messages": len(core.messages),
            }

            outside = root / "outside.md"
            outside_content = "# Outside fixture\nsecret-free external report\n"
            outside.write_text(outside_content, encoding="utf-8")
            traversal_report = "../outside.md"
            traversal_task = {
                "id": "task-fixture",
                "run_id": "run-fixture",
                "expected_report": {"artifact": traversal_report},
            }
            traversal_core = FakeCore(project, traversal_task)
            FakeIngress.calls = 0
            FakeIngress.last_event = None
            FakeIngress.receipts = [SimpleNamespace(raw_event_id="raw_traversal", accepted=True, deduplicated=False, raw_location="fixture:1", routing_status="raw_accepted", normalized_event_ids=[], chat_message_ids=[], diagnostics={})]
            # command_worker_run_collect() reads report_path first, then uses
            # rel(report_path, project_root) in raw_payload.expected_report.
            # For an escaped path rel() returns the absolute path, while the
            # task still declares the lexical ../outside.md value.
            collector_ref = pf.rel(project / traversal_report, project)
            traversal_envelope = worker_envelope(project, collector_ref, outside_content)
            traversal = host.ingest_event(traversal_envelope, root / "workplace", traversal_core, project_ref=str(project))
            helper_value = pf.expected_report_artifact(traversal_task)
            raw_event = FakeIngress.last_event
            results["report_path_traversal"] = {
                "helper_value": helper_value,
                "collector_ref": collector_ref,
                "resolved_path": str(project / helper_value),
                "resolved_inside_project": project in (project / helper_value).resolve().parents,
                "outside_file_exists": (project / helper_value).is_file(),
                "worker_session_authorized": host._worker_session_authorized(traversal_envelope, project, traversal_core),
                "raw_payload_report_content": getattr(raw_event, "raw_payload", {}).get("report_content") if raw_event is not None else None,
                "capture": traversal,
            }
    finally:
        host.RawIngressKernel = original_kernel
    return results


if __name__ == "__main__":
    payload = run()
    out = Path(__file__).with_name("evidence") / "probe-result.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
