"""Exact, run-owned recovery records for interrupted Work creation."""

from __future__ import annotations

import hashlib
import json
import re
from contextvars import ContextVar
from pathlib import Path
from typing import Any

MAX_START_BYTES = 8 * 1024 * 1024
RENDERING_START: ContextVar[tuple[str, str] | None] = ContextVar(
    "pf_rendering_start", default=None
)
_ID = re.compile(r"(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])\Z")


class StartIntentError(ValueError):
    def __init__(self, code: str = "work_start_intent_invalid") -> None:
        self.code = code
        super().__init__(code)


def fingerprint(value: Any) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                value, sort_keys=True, ensure_ascii=False, allow_nan=False
            ).encode()
        ).hexdigest()
    )


def intent_path(run_path: Path) -> Path:
    return run_path.parent / "start-intent.json"


def applied_path(run_path: Path) -> Path:
    return run_path.parent / "start-applied.json"


def read_record(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink():
            raise StartIntentError()
        with path.open("rb") as stream:
            raw = stream.read(MAX_START_BYTES + 1)
        if len(raw) > MAX_START_BYTES:
            raise StartIntentError()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise StartIntentError()
        return value
    except (OSError, ValueError, TypeError) as error:
        raise StartIntentError() from error


def validate(intent: dict[str, Any], run_path: Path, project_id: str) -> None:
    """Do not let a self-consistent checksum authorize different Work paths."""
    try:
        run, assignment = intent["run"], intent["assignment"]
        run_id, assignment_id = run["id"], assignment["id"]
        checksum = fingerprint({k: v for k, v in intent.items() if k != "checksum"})
        if (
            intent["schema_version"] != 1
            or intent["kind"] != "pf.work.start-intent"
            or intent["checksum"] != checksum
            or intent["project_id"] != project_id
            or not _ID.fullmatch(run_id)
            or not _ID.fullmatch(assignment_id)
            or run_id != run_path.parent.name
            or assignment["run_id"] != run_id
            or assignment["stage"] != intent["stage_id"]
            or assignment["status"] != "in_progress"
            or run["status"] != "in_progress"
            or run["objective"] != intent["objective"]
            or assignment["objective"] != intent["objective"]
            or any(
                run["process_execution"].get(k) != v
                for k, v in assignment["process_execution"].items()
            )
            or not isinstance(intent["capsule_text"], str)
            or not isinstance(intent["request"], dict)
            or not isinstance(intent["objective"], str)
            or not isinstance(intent["stage_override"], str)
            or not isinstance(intent["stages"], list)
            or intent["stage_id"] not in intent["stages"]
        ):
            raise StartIntentError()
        capsule_checksum = (
            "sha256:"
            + hashlib.sha256(intent["capsule_text"].encode("utf-8")).hexdigest()
        )
        pin = run["process_execution"]
        if (
            pin["assignment_capsule"]
            != f".pf/contexts/assignment-capsules/{assignment_id}.capsule.yaml"
            or pin["assignment_capsule_checksum"] != capsule_checksum
        ):
            raise StartIntentError()
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise StartIntentError() from error


def applied(intent: dict[str, Any], run_path: Path) -> bool:
    path = applied_path(run_path)
    if not path.exists():
        return False
    if read_record(path) != {
        "schema_version": 1,
        "checksum": intent["checksum"],
        "status": "applied",
    }:
        raise StartIntentError()
    return True


def find_pending(
    flow_root: Path, objective: str, project_id: str
) -> dict[str, Any] | None:
    selected = None
    other_pending = False
    for path in sorted((flow_root / "runs").glob("*/start-intent.json")):
        run_path = path.with_name("run.yaml")
        intent = read_record(path)
        # Any broken record fails closed rather than allowing a duplicate.
        validate(intent, run_path, project_id)
        if applied(intent, run_path):
            continue
        if intent["objective"] != objective:
            other_pending = True
            continue
        if selected is not None:
            raise StartIntentError("work_start_ambiguous")
        selected = intent
    if selected is None and other_pending:
        # An incomplete start may not yet have an assignment visible to the
        # ordinary overlap reader. Reconcile it before admitting new Work.
        raise StartIntentError("work_start_publication_pending")
    return selected


def pending_reason(run_path: Path, project_id: str) -> str:
    path = intent_path(run_path)
    if not path.exists():
        return ""
    try:
        intent = read_record(path)
        validate(intent, run_path, project_id)
        if RENDERING_START.get() == (str(run_path), intent["checksum"]):
            return ""
        return "" if applied(intent, run_path) else "work_start_publication_pending"
    except StartIntentError as error:
        return error.code
