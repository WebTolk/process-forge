"""Private Codex session raw-v1 replay helpers.

This module intentionally exposes no CLI. It repairs missing project-side
effects for already accepted Codex raw hook records by reusing the existing
Codex normalization boundary and Host derived-event path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .codex_hooks import normalized_event
from .host import _ingest_derived_event, event_exists, resolve_project, stable_event_id
from .raw_ingress_kernel import RawIngressKernel, atomic_write_json, contained_path

PROCESSOR_ID = "processforge.session-replay.codex-hooks"
PROCESSOR_VERSION = "1"
COUNT_KEYS = ("seen", "present", "repaired", "unsupported_mapping", "denied", "failed")


def replay_session_raw_records(
    workplace_root: Path,
    core: Any,
    *,
    session_id: str,
    project_ref: str,
    provider: str = "codex",
    adapter: str = "codex-hooks",
    limit: int | None = None,
) -> dict[str, Any]:
    """Replay accepted raw Codex records for one session and one project."""

    if not session_id:
        raise ValueError("session_id is required")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")

    root = RawIngressKernel(workplace_root).root
    project_root = resolve_project(project_ref, core)
    counts = _empty_counts()
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    processed = 0

    for item in _iter_raw_records(root):
        if item.get("malformed"):
            counts["failed"] += 1
            errors.append({"status": "failed", "code": "malformed_json", "raw_location": item["raw_location"]})
            return _result("failed", counts, records, errors)

        record = item["record"]
        if not _candidate(record, session_id=session_id, provider=provider, adapter=adapter):
            continue

        counts["seen"] += 1
        raw_location = str(item["raw_location"])
        raw_event_id = str(record.get("raw_event_id") or "")
        status = _process_record(
            record,
            raw_location=raw_location,
            raw_event_id=raw_event_id,
            project_root=project_root,
            workplace_root=Path(workplace_root),
            core=core,
            counts=counts,
        )
        if status["status"] == "failed":
            errors.append(status)
            return _result("failed", counts, records, errors)

        records.append(status)
        _write_checkpoint(
            root,
            core,
            session_id=session_id,
            project_ref=project_ref,
            provider=provider,
            adapter=adapter,
            last_raw_event_id=raw_event_id,
            last_raw_location=raw_location,
            counts=counts,
        )
        processed += 1
        if limit is not None and processed >= limit:
            break

    return _result("ok", counts, records, errors)


def checkpoint_path(workplace_root: Path, session_id: str) -> Path:
    root = RawIngressKernel(workplace_root).root
    return contained_path(root, "checkpoints", "session-replay", f"{_safe_session_id(session_id)}.json")


def _iter_raw_records(root: Path) -> Iterable[dict[str, Any]]:
    raw_root = contained_path(root, "raw", "v1")
    if not raw_root.is_dir():
        return
    for shard in sorted(raw_root.rglob("*.ndjson")):
        offset = 0
        with shard.open("rb") as handle:
            for line in handle:
                raw_location = f"{shard.relative_to(root).as_posix()}:{offset}"
                try:
                    record = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    yield {"malformed": True, "raw_location": raw_location}
                    return
                if isinstance(record, dict):
                    yield {"record": record, "raw_location": raw_location}
                offset += len(line)


def _candidate(record: Mapping[str, Any], *, session_id: str, provider: str, adapter: str) -> bool:
    return (
        record.get("schema_version") == 1
        and record.get("provider") == provider
        and record.get("adapter") == adapter
        and record.get("source_session_id") == session_id
    )


def _process_record(
    record: Mapping[str, Any],
    *,
    raw_location: str,
    raw_event_id: str,
    project_root: Path,
    workplace_root: Path,
    core: Any,
    counts: dict[str, int],
) -> dict[str, Any]:
    source_project_ref = str(record.get("source_project_ref") or "")
    if not _same_project(source_project_ref, project_root, core):
        counts["denied"] += 1
        return _record_status("denied", raw_location, raw_event_id, code="source_project_mismatch")

    raw_payload = record.get("raw_payload")
    derived = normalized_event(dict(raw_payload)) if isinstance(raw_payload, dict) else None
    if derived is None:
        counts["unsupported_mapping"] += 1
        return _record_status("unsupported_mapping", raw_location, raw_event_id)

    if not _derived_scope_allowed(derived, project_root, str(record.get("source_session_id") or ""), core):
        counts["denied"] += 1
        return _record_status("denied", raw_location, raw_event_id, code="derived_scope_mismatch")

    event_id = stable_event_id(derived)
    if event_exists(project_root, event_id, core):
        counts["present"] += 1
        return _record_status("present", raw_location, raw_event_id, event_id=event_id)

    try:
        routed = _ingest_derived_event(derived, workplace_root, core, project_ref=str(project_root))
    except (PermissionError, SystemExit) as exc:
        counts["failed"] += 1
        return _record_status("failed", raw_location, raw_event_id, code=type(exc).__name__, message=str(exc))

    counts["repaired"] += 1
    return _record_status("repaired", raw_location, raw_event_id, event_id=str(routed.get("event_id") or event_id))


def _same_project(project_ref: str, project_root: Path, core: Any) -> bool:
    if not project_ref:
        return False
    try:
        return resolve_project(project_ref, core) == project_root
    except SystemExit:
        return False


def _derived_scope_allowed(derived: Mapping[str, Any], project_root: Path, session_id: str, core: Any) -> bool:
    derived_ref = str(derived.get("project_root") or derived.get("cwd") or "")
    if derived_ref and not _same_project(derived_ref, project_root, core):
        return False
    source = derived.get("source") if isinstance(derived.get("source"), Mapping) else {}
    derived_session = str(source.get("session_id") or derived.get("session_id") or "")
    return not derived_session or derived_session == session_id


def _write_checkpoint(
    root: Path,
    core: Any,
    *,
    session_id: str,
    project_ref: str,
    provider: str,
    adapter: str,
    last_raw_event_id: str,
    last_raw_location: str,
    counts: Mapping[str, int],
) -> None:
    path = contained_path(root, "checkpoints", "session-replay", f"{_safe_session_id(session_id)}.json")
    atomic_write_json(
        path,
        {
            "schema_version": 1,
            "kind": "session-replay-checkpoint",
            "processor_id": PROCESSOR_ID,
            "processor_version": PROCESSOR_VERSION,
            "provider": provider,
            "adapter": adapter,
            "source_session_id": session_id,
            "source_project_ref": project_ref,
            "last_raw_event_id": last_raw_event_id,
            "last_raw_location": last_raw_location,
            "updated_at": core.now_utc(),
            "counts": {key: int(counts.get(key, 0)) for key in COUNT_KEYS},
        },
        root,
    )


def _safe_session_id(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id).strip("._-")
    return safe[:80] or "session"


def _empty_counts() -> dict[str, int]:
    return {key: 0 for key in COUNT_KEYS}


def _record_status(status: str, raw_location: str, raw_event_id: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "raw_location": raw_location, "raw_event_id": raw_event_id, **extra}


def _result(status: str, counts: Mapping[str, int], records: list[dict[str, Any]], errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "session-replay-result",
        "processor_id": PROCESSOR_ID,
        "processor_version": PROCESSOR_VERSION,
        "status": status,
        "counts": {key: int(counts.get(key, 0)) for key in COUNT_KEYS},
        "records": records,
        "errors": errors,
    }
