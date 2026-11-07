"""Byte-preserving publication for private retry evidence.

This primitive does not authorize retirement, launch, or journal replay. The
caller must hold the existing publication boundary and validate attempt safety.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from ..executions.model import ExecutionError
from .input import MAX_BYTES, digest, encoded, local_file, private_file


def _ordinary(info: os.stat_result) -> bool:
    return stat.S_ISREG(info.st_mode) and not (
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _checked(project: Path, path: Path) -> Path:
    checked = local_file(project, path.relative_to(project).as_posix())
    try:
        info = checked.lstat()
    except FileNotFoundError:
        return checked
    if not _ordinary(info):
        raise ExecutionError("execution_identity_conflict")
    return checked


def _full_write(stream: BinaryIO, raw: bytes) -> None:
    view = memoryview(raw)
    offset = 0
    while offset < len(view):
        count = stream.write(view[offset:])
        if type(count) is not int or count <= 0 or count > len(view) - offset:
            raise OSError("retry_publication_write_no_progress")
        offset += count
    stream.flush()
    os.fsync(stream.fileno())


def _sync_parent(path: Path) -> None:
    # Windows provides file fsync and same-volume atomic hard-link publication.
    # Portable directory/power-loss durability is deliberately not claimed.
    if os.name == "nt":
        return
    descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _exact_existing(project: Path, destination: Path, raw: bytes) -> None:
    _checked(project, destination)
    before = destination.lstat()
    with destination.open("r+b", buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        if (
            not _ordinary(opened)
            or _identity(before) != _identity(opened)
            or stream.read() != raw
        ):
            raise ExecutionError("execution_identity_conflict")
        os.fsync(stream.fileno())
        after = destination.lstat()
        if not _ordinary(after) or _identity(after) != _identity(opened):
            raise ExecutionError("execution_identity_conflict")
    _sync_parent(destination)


def publish_raw_once(project: Path, destination: Path, raw: bytes) -> None:
    """Publish complete bytes without replacing any existing final evidence.

    Failure cleanup owns only the exact temporary object created by this call.
    A committed final survives every later exception, including cleanup errors.
    Unknown orphan staging is never discovered or deleted here.
    """
    private_file(project, destination.relative_to(project).as_posix())
    _checked(project, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(".retry-" + uuid.uuid4().hex + ".tmp")
    _checked(project, staging)
    identity: tuple[int, int] | None = None
    primary: BaseException | None = None
    try:
        with staging.open("xb", buffering=0) as stream:
            identity = _identity(os.fstat(stream.fileno()))
            if sys.platform != "win32":
                os.fchmod(stream.fileno(), 0o600)
            _full_write(stream, raw)
        # Close the write handle before link/unlink, including on Windows.
        _checked(project, staging)
        if _identity(staging.lstat()) != identity:
            raise ExecutionError("execution_identity_conflict")
        try:
            os.link(staging, destination)
        except FileExistsError:
            _exact_existing(project, destination, raw)
        else:
            _exact_existing(project, destination, raw)
    except BaseException as error:
        primary = error
        raise
    finally:
        if identity is not None:
            try:
                _checked(project, staging)
                info = staging.lstat()
                if _identity(info) != identity:
                    raise ExecutionError("execution_identity_conflict")
                staging.unlink()
            except BaseException as cleanup_error:
                if primary is None:
                    raise
                primary.add_note(
                    "retry_staging_cleanup:" + type(cleanup_error).__name__
                )


# The journal is private storage, never a launch or authorization token.

OBSERVATIONS = ("status", "command", "process", "exit", "stdout", "stderr", "heartbeat")
PROJECTIONS = ("workspace_access", "prompt", "status", "command")
SLOTS = (*OBSERVATIONS, "prompt", "workspace_access")
ORDER = ("process", "exit", *PROJECTIONS)
SIDECARS = {
    "status": "retry-publication-status.json",
    "command": "retry-publication-command.json",
    "prompt": "retry-publication-prompt.bin",
    "workspace_access": "retry-publication-workspace-access.json",
}
INTENT = "retry-publication.intent.json"
APPLIED = "retry-publication.applied.json"


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ExecutionError("execution_identity_conflict")
        result[key] = value
    return result


def strict_json(raw: bytes) -> dict[str, Any]:
    """Reject ambiguity before using any private journal field."""
    try:
        if len(raw) > MAX_BYTES:
            raise ValueError("journal_budget")
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
        )
        if not isinstance(value, dict):
            raise ValueError("journal_object")
        return value
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ExecutionError("execution_identity_conflict") from error


def read_raw(project: Path, path: Path, maximum: int | None = None) -> bytes | None:
    """Read an ordinary contained object and reject replacement during the read."""
    _checked(project, path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if maximum is not None and opened.st_size > maximum:
            raise ExecutionError("execution_identity_conflict")
        raw = stream.read() if maximum is None else stream.read(maximum + 1)
        after = path.lstat()
        if (
            not _ordinary(opened)
            or not _ordinary(after)
            or (maximum is not None and len(raw) > maximum)
            or _identity(before) != _identity(opened)
            or _identity(after) != _identity(opened)
        ):
            raise ExecutionError("execution_identity_conflict")
    return raw


def stamp(raw: bytes | None) -> dict[str, Any]:
    return {
        "present": raw is not None,
        "size": len(raw) if raw is not None else 0,
        "sha256": digest(raw) if raw is not None else None,
    }


def _matches(raw: bytes | None, record: Any) -> bool:
    return (
        isinstance(record, dict)
        and record == stamp(raw)
        and (type(record.get("present")) is bool and type(record.get("size")) is int)
    )


def replace_raw(project: Path, path: Path, raw: bytes, expected: bytes | None) -> None:
    """Atomically replace only the exact mutable projection checked by the caller."""
    if read_raw(project, path) != expected:
        raise ExecutionError("execution_identity_conflict")
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(".retry-" + uuid.uuid4().hex + ".tmp")
    _checked(project, staging)
    identity = None
    primary: BaseException | None = None
    try:
        with staging.open("xb", buffering=0) as stream:
            identity = _identity(os.fstat(stream.fileno()))
            if sys.platform != "win32":
                os.fchmod(stream.fileno(), 0o600)
            _full_write(stream, raw)
        _checked(project, staging)
        if (
            _identity(staging.lstat()) != identity
            or read_raw(project, path) != expected
        ):
            raise ExecutionError("execution_identity_conflict")
        os.replace(staging, path)
        identity = None  # Our object now has the projection name; never unlink it.
        _exact_existing(project, path, raw)
    except BaseException as error:
        primary = error
        raise
    finally:
        if identity is not None:
            try:
                _checked(project, staging)
                if _identity(staging.lstat()) != identity:
                    raise ExecutionError("execution_identity_conflict")
                staging.unlink()
            except BaseException as error:
                if primary is None:
                    raise
                primary.add_note("retry_staging_cleanup:" + type(error).__name__)


def _reference(root: Path, project: Path, value: Any, attempt: int) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "checksum"}
        or value.get("path")
        != (root / str(attempt) / "prepared-input.json").relative_to(project).as_posix()
        or not isinstance(value.get("checksum"), str)
        or len(value["checksum"]) != 71
        or not value["checksum"].startswith("sha256:")
        or any(x not in "0123456789abcdef" for x in value["checksum"][7:])
    ):
        raise ExecutionError("execution_identity_conflict")


@dataclass(frozen=True)
class Publication:
    directory: Path
    intent: dict[str, Any]
    raw: bytes
    old: dict[str, bytes | None]
    new: dict[str, bytes]

    @property
    def receipt(self) -> bytes:
        return encoded(
            {
                "schema_version": 2,
                "kind": "pf.retry-publication.applied",
                "identity": self.intent["identity"],
                "intent_checksum": digest(self.raw),
                "projections": {key: stamp(self.new[key]) for key in PROJECTIONS},
            }
        )


def load_publication(project: Path, directory: Path) -> Publication:
    raw = read_raw(project, directory / INTENT, MAX_BYTES)
    if raw is None:
        raise ExecutionError("execution_identity_conflict")
    intent = strict_json(raw)
    if (
        set(intent)
        != {
            "schema_version",
            "kind",
            "operation",
            "identity",
            "old_reference",
            "old_attempt",
            "new_reference",
            "request",
            "pins",
            "old",
            "new",
        }
        or type(intent["schema_version"]) is not int
        or intent["schema_version"] != 2
        or intent["kind"] != "pf.retry-publication"
        or not isinstance(intent["identity"], dict)
        or set(intent["identity"])
        != {"project_id", "run_id", "assignment_id", "context_id", "attempt"}
        or type(intent["identity"]["attempt"]) is not int
        or intent["identity"]["attempt"] < 1
        or directory.name != str(intent["identity"]["attempt"])
        or type(intent["old_attempt"]) is not int
        or not 0 <= intent["old_attempt"] < intent["identity"]["attempt"]
        or not isinstance(intent["old"], dict)
        or set(intent["old"]) != set(SLOTS)
        or not isinstance(intent["new"], dict)
        or set(intent["new"]) != set(PROJECTIONS)
        or not isinstance(intent["request"], dict)
        or not isinstance(intent["pins"], dict)
    ):
        raise ExecutionError("execution_identity_conflict")
    content = {key: value for key, value in intent.items() if key != "operation"}
    if intent["operation"] != digest(encoded(content)):
        raise ExecutionError("execution_identity_conflict")
    _reference(
        directory.parent,
        project,
        intent["new_reference"],
        intent["identity"]["attempt"],
    )
    if intent["old_attempt"]:
        _reference(
            directory.parent, project, intent["old_reference"], intent["old_attempt"]
        )
    elif intent["old_reference"] is not None:
        raise ExecutionError("execution_identity_conflict")
    old: dict[str, bytes | None] = {}
    for key in SLOTS:
        archive = directory / (
            "retry-publication-old-" + key.replace("_", "-") + ".bin"
        )
        old[key] = read_raw(project, archive)
        if not _matches(old[key], intent["old"][key]):
            raise ExecutionError("execution_identity_conflict")
    new: dict[str, bytes] = {}
    for key, name in SIDECARS.items():
        body = read_raw(project, directory / name, MAX_BYTES)
        if body is None or not _matches(body, intent["new"][key]):
            raise ExecutionError("execution_identity_conflict")
        new[key] = body
    publication = Publication(directory, intent, raw, old, new)
    receipt = read_raw(project, directory / APPLIED, MAX_BYTES)
    if receipt is not None:
        # Parse even exact receipts so no alternative JSON parser gains authority.
        strict_json(receipt)
        if receipt != publication.receipt:
            raise ExecutionError("execution_identity_conflict")
    return publication


def discover(project: Path, attempts: Path, verify=None) -> Publication | None:
    """Analyze every journal; never select first/newest or replay applied history."""
    private_file(project, attempts.relative_to(project).as_posix())
    if not attempts.exists():
        return None
    pending = []
    for directory in attempts.iterdir():
        private_file(project, (directory / INTENT).relative_to(project).as_posix())
        intent = read_raw(project, directory / INTENT, MAX_BYTES)
        receipt = read_raw(project, directory / APPLIED, MAX_BYTES)
        if intent is None:
            if receipt is not None:
                raise ExecutionError("execution_identity_conflict")
            continue  # Uncommitted sidecars confer no recovery authority.
        publication = load_publication(project, directory)
        identity = publication.intent["identity"]
        if (
            identity["run_id"] != attempts.parent.parent.name
            or identity["assignment_id"] != attempts.parent.name
        ):
            raise ExecutionError("execution_identity_conflict")
        if verify is not None:
            verify(publication)
        if receipt is None:
            pending.append(publication)
    if len(pending) > 1:
        raise ExecutionError("execution_identity_conflict")
    return pending[0] if pending else None


def create_publication(
    project: Path,
    directory: Path,
    identity: dict[str, Any],
    old_reference: dict[str, Any] | None,
    old_attempt: int,
    new_reference: dict[str, Any],
    request: dict[str, Any],
    pins: dict[str, Any],
    old: dict[str, bytes | None],
    new: dict[str, bytes],
    validate=None,
) -> Publication:
    """Capture originals only in N, publish sidecars, then commit schema v2 intent."""
    for key, raw in old.items():
        if raw is None:
            continue
        archive = directory / (
            "retry-publication-old-" + key.replace("_", "-") + ".bin"
        )
        publish_raw_once(project, archive, raw)
    for key, raw in new.items():
        publish_raw_once(project, directory / SIDECARS[key], raw)
    identity = {
        key: identity[key]
        for key in ("project_id", "run_id", "assignment_id", "context_id", "attempt")
    }
    intent = {
        "schema_version": 2,
        "kind": "pf.retry-publication",
        "identity": identity,
        "old_attempt": old_attempt,
        "old_reference": old_reference,
        "new_reference": new_reference,
        "request": request,
        "pins": pins,
        "old": {key: stamp(old[key]) for key in SLOTS},
        "new": {key: stamp(new[key]) for key in PROJECTIONS},
    }
    intent["operation"] = digest(encoded(intent))
    raw = encoded(intent)
    if validate is not None:
        validate(Publication(directory, intent, raw, old, new))
    publish_raw_once(project, directory / INTENT, raw)
    return load_publication(project, directory)


def _aliases(project: Path, publication: Publication, *, publish: bool = False) -> bool:
    """Canonical evidence derives only from an intent-bound operation capture."""
    if not publication.intent["old_attempt"]:
        return True
    complete = True
    for key in OBSERVATIONS:
        path = (
            publication.directory.parent
            / str(publication.intent["old_attempt"])
            / ("retry-previous-" + key + ".json")
        )
        raw = publication.old[key]
        if publish and raw is not None:
            publish_raw_once(project, path, raw)
        existing = read_raw(project, path)
        if existing is not None and existing != raw:
            raise ExecutionError("execution_identity_conflict")
        if existing != raw:
            complete = False
    return complete


def prefix(project: Path, paths: dict[str, Path], publication: Publication) -> int:
    """Recognize the complete reachable vector, including missing originals."""
    current = {key: read_raw(project, paths[key]) for key in SLOTS}
    aliases_complete = _aliases(project, publication)
    if current != publication.old and not aliases_complete:
        raise ExecutionError("execution_identity_conflict")
    vector = dict(publication.old)
    matches = []
    for index in range(len(ORDER) + 1):
        if current == vector:
            matches.append(index)
        if index < len(ORDER):
            key = ORDER[index]
            vector[key] = publication.new.get(key)
    if not matches:
        raise ExecutionError("execution_identity_conflict")
    return max(matches)


def apply_publication(
    project: Path, paths: dict[str, Path], publication: Publication, retired=None
) -> None:
    """Finish only the remaining prefix using immutable bytes, then seal receipt."""
    # Refuse uncommitted capture objects, including direct internal callers.
    committed = load_publication(project, publication.directory)
    if committed.raw != publication.raw:
        raise ExecutionError("execution_identity_conflict")
    prefix(project, paths, publication)
    _aliases(project, publication, publish=True)
    start = prefix(project, paths, publication)
    if retired is not None and start >= 2:
        retired()
    for index in range(start, len(ORDER)):
        key = ORDER[index]
        if prefix(project, paths, publication) < index:
            raise ExecutionError("execution_identity_conflict")
        expected = read_raw(project, paths[key])
        if expected != publication.old[key]:
            # Equal old/new values may already advance the reachable prefix.
            if expected == publication.new.get(key):
                continue
            raise ExecutionError("execution_identity_conflict")
        if key in {"process", "exit"}:
            if expected is not None:
                _checked(project, paths[key])
                paths[key].unlink()
                _sync_parent(paths[key])
            if read_raw(project, paths[key]) is not None:
                raise ExecutionError("execution_identity_conflict")
        else:
            replace_raw(project, paths[key], publication.new[key], expected)
        if retired is not None and index == 1:
            retired()
    if prefix(project, paths, publication) != len(ORDER):
        raise ExecutionError("execution_identity_conflict")
    publish_raw_once(project, publication.directory / APPLIED, publication.receipt)
