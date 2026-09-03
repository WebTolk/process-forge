"""Provider-neutral raw ingress identity and durable storage primitives.

This module deliberately has no Runtime, Ledger, or provider-adapter imports.
Those layers may use its raw receipt only after durable persistence succeeds.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class RawIngressError(ValueError):
    """An envelope or durable raw ingress operation is invalid."""


class PathContainmentError(RawIngressError):
    """A computed runtime path escaped its configured storage root."""


@dataclass(frozen=True)
class NativeAgentEvent:
    """The provider-neutral event passed from a thin adapter to ingress."""

    provider: str
    adapter: str
    native_event_type: str
    raw_payload: Mapping[str, Any]
    payload_version: str = "1"
    native_event_id: str | None = None
    native_id_scope: str = "provider"
    native_event_id_stable: bool = True
    source_session_id: str | None = None
    source_project_ref: str | None = None


@dataclass(frozen=True)
class RawReceipt:
    raw_event_id: str | None
    accepted: bool
    deduplicated: bool
    raw_location: str | None
    routing_status: str
    normalized_event_ids: tuple[str, ...] = ()
    chat_message_ids: tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON with NFC strings and sorted keys."""

    return json.dumps(
        _normalise_json(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def raw_payload_hash(payload: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload)).hexdigest()


def raw_event_id(event: NativeAgentEvent) -> str:
    """Derive the v1 raw identity, excluding receipt/transport metadata."""

    document = _identity_document(event, include_payload_hash=True)
    return "raw_" + hashlib.sha256(canonical_json(document)).hexdigest()


def stable_native_identity_key(event: NativeAgentEvent) -> str | None:
    """Return the conflict-detection key, deliberately excluding payload hash."""

    if not _uses_stable_native_id(event):
        return None
    digest = hashlib.sha256(canonical_json(_identity_document(event, include_payload_hash=False))).hexdigest()
    return "native_" + digest


def deterministic_derived_key(
    raw_id: str, derived_kind: str, processor_id: str, processor_version: str, semantic_target: Any
) -> str:
    """Return a deterministic idempotency key for a derived sink effect."""

    if not raw_id.startswith("raw_"):
        raise RawIngressError("raw_id must start with raw_")
    return hashlib.sha256(
        canonical_json(
            {
                "contract": "processforge.derived-id.v1",
                "raw_event_id": raw_id,
                "derived_kind": _text(derived_kind, "derived_kind"),
                "processor_id": _text(processor_id, "processor_id"),
                "processor_version": _text(processor_version, "processor_version"),
                "semantic_target": semantic_target,
            }
        )
    ).hexdigest()


def _strip_windows_extended_prefix(value: str) -> str:
    """Return a normal spelling for an equivalent Win32 extended path."""

    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _resolved_for_containment(path: Path | str) -> Path:
    resolved = Path(path).resolve(strict=False)
    if os.name == "nt":
        return Path(_strip_windows_extended_prefix(str(resolved)))
    return resolved


def contained_path(root: Path | str, *parts: str) -> Path:
    root_path = _resolved_for_containment(root)
    candidate = _resolved_for_containment(root_path.joinpath(*parts))
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise PathContainmentError(f"path escapes runtime root: {candidate}") from exc
    return candidate


def atomic_write_json(path: Path, data: Mapping[str, Any], root: Path) -> None:
    """Atomically replace an index/checkpoint file confined to *root*."""

    target = contained_path(root, str(path.relative_to(root)))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=target.parent, prefix=f".{target.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(canonical_json(data) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink(missing_ok=True)


class _ExclusiveFileLock:
    """Cross-process lock; stale locks require explicit, auditable recovery."""

    def __init__(self, path: Path, timeout_seconds: float = 20.0) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self._fd: int | None = None

    def __enter__(self) -> "_ExclusiveFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "created_at": time.time()}).encode("utf-8"))
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise RawIngressError(f"timed out waiting for raw ingress lock: {self.path.name}")
                time.sleep(0.05)

    def __exit__(self, *_: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
        self.path.unlink(missing_ok=True)


def recover_stale_lock(path: Path, *, stale_seconds: float, force: bool = False) -> bool:
    """Explicitly reap a dead local lock; callers must audit forced recovery.

    No live lock is removed automatically.  This function reaps only a lock
    older than the declared lease whose recorded PID is no longer alive on the
    same host, unless an operator passes ``force=True``.
    """

    if not path.is_file():
        return False
    try:
        owner = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - float(owner["created_at"])
        same_host = owner.get("host") == socket.gethostname()
        pid = int(owner["pid"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        if not force:
            raise RawIngressError(f"lock metadata is unreadable; explicit force required: {path.name}")
        path.unlink(missing_ok=True)
        return True
    if age < stale_seconds:
        return False
    alive = same_host and _pid_alive(pid)
    if alive and not force:
        return False
    path.unlink(missing_ok=True)
    return True


class RawIngressKernel:
    """Append raw events, maintain identity indexes, and return durable receipts."""

    def __init__(self, workplace_root: Path | str, *, max_payload_bytes: int = 1_048_576) -> None:
        self.workplace_root = Path(workplace_root).resolve(strict=False)
        self.root = contained_path(self.workplace_root, "runtime", "agent-events")
        if max_payload_bytes <= 0:
            raise RawIngressError("max_payload_bytes must be positive")
        self.max_payload_bytes = max_payload_bytes

    def ingest(self, event: NativeAgentEvent, received_at: datetime | None = None) -> RawReceipt:
        _validate(event, self.max_payload_bytes)
        moment = (received_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        payload_hash = raw_payload_hash(event.raw_payload)
        event_id = raw_event_id(event)
        native_key = stable_native_identity_key(event)
        raw_index = self._index_path("raw_event_id", event_id)
        native_index = self._index_path("native_identity", native_key) if native_key else None
        with _ExclusiveFileLock(contained_path(self.root, "indexes", ".ingress.lock")):
            native_existing = self._read_index(native_index)
            existing = self._read_index(raw_index)
            if native_existing is None or existing is None:
                recovered_raw, recovered_native = self._recover_indexes(event_id, native_key)
                native_existing = native_existing or recovered_native
                existing = existing or recovered_raw
            if native_existing and native_existing.get("raw_payload_hash") != payload_hash:
                return self._quarantine("native_id_payload_conflict", event, event_id, payload_hash, native_existing)
            if existing:
                if existing.get("raw_payload_hash") == payload_hash:
                    return RawReceipt(event_id, True, True, existing.get("raw_location"), "duplicate_raw")
                return self._quarantine("raw_event_id_hash_collision", event, event_id, payload_hash, existing)

            shard = self._shard(moment)
            line = canonical_json(self._raw_record(event, event_id, payload_hash, native_key, moment)) + b"\n"
            offset = self._append_line(shard, line)
            location = f"{shard.relative_to(self.root).as_posix()}:{offset}"
            index = {
                "schema_version": 1,
                "raw_event_id": event_id,
                "raw_payload_hash": payload_hash,
                "native_identity_key": native_key,
                "raw_location": location,
                "routing_status": "raw_accepted",
            }
            atomic_write_json(raw_index, index, self.root)
            if native_index is not None:
                atomic_write_json(native_index, index, self.root)
            return RawReceipt(event_id, True, False, location, "raw_accepted")

    def _shard(self, moment: datetime) -> Path:
        return contained_path(
            self.root, "raw", "v1", f"{moment.year:04d}", f"{moment.month:02d}", f"{moment.day:02d}", f"{moment.hour:02d}.ndjson"
        )

    def _index_path(self, kind: str, key: str | None) -> Path:
        if not key or any(char in key for char in ("/", "\\", "\x00")):
            raise RawIngressError("unsafe index key")
        return contained_path(self.root, "indexes", kind, f"{key}.json")

    def _append_line(self, shard: Path, line: bytes) -> int:
        shard.parent.mkdir(parents=True, exist_ok=True)
        with _ExclusiveFileLock(shard.with_suffix(shard.suffix + ".lock")):
            descriptor = os.open(str(shard), os.O_CREAT | os.O_APPEND | os.O_WRONLY)
            try:
                offset = os.lseek(descriptor, 0, os.SEEK_END)
                if os.write(descriptor, line) != len(line):
                    raise OSError("short raw journal write")
                os.fsync(descriptor)
                return offset
            finally:
                os.close(descriptor)

    def _read_index(self, path: Path | None) -> Mapping[str, Any] | None:
        if path is None or not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise RawIngressError(f"index is not an object: {path.name}")
        return data

    def _recover_indexes(self, event_id: str, native_key: str | None) -> tuple[Mapping[str, Any] | None, Mapping[str, Any] | None]:
        """Rebuild missing lookup records after a crash between append and index."""

        raw_found: Mapping[str, Any] | None = None
        native_found: Mapping[str, Any] | None = None
        raw_root = contained_path(self.root, "raw", "v1")
        if not raw_root.is_dir():
            return None, None
        for shard in raw_root.rglob("*.ndjson"):
            offset = 0
            with shard.open("rb") as handle:
                for line in handle:
                    try:
                        record = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise RawIngressError(f"corrupt raw journal shard: {shard.name}") from exc
                    location = f"{shard.relative_to(self.root).as_posix()}:{offset}"
                    candidate = {
                        "schema_version": 1,
                        "raw_event_id": record.get("raw_event_id"),
                        "raw_payload_hash": record.get("raw_payload_hash"),
                        "native_identity_key": record.get("native_identity_key"),
                        "raw_location": location,
                        "routing_status": "raw_recovered",
                    }
                    if candidate["raw_event_id"] == event_id:
                        raw_found = candidate
                    if native_key and candidate["native_identity_key"] == native_key:
                        native_found = candidate
                    offset += len(line)
        if raw_found:
            atomic_write_json(self._index_path("raw_event_id", event_id), raw_found, self.root)
        if native_key and native_found:
            atomic_write_json(self._index_path("native_identity", native_key), native_found, self.root)
        return raw_found, native_found

    def _raw_record(self, event: NativeAgentEvent, event_id: str, payload_hash: str, native_key: str | None, moment: datetime) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "raw_event_id": event_id,
            "provider": event.provider,
            "adapter": event.adapter,
            "native_event_type": event.native_event_type,
            "native_event_id": event.native_event_id,
            "source_session_id": event.source_session_id,
            "source_project_ref": event.source_project_ref,
            "payload_version": event.payload_version,
            "received_at": moment.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "raw_payload": event.raw_payload,
            "raw_payload_hash": payload_hash,
            "native_identity_key": native_key,
            "privacy": "private",
        }

    def _quarantine(self, code: str, event: NativeAgentEvent, event_id: str, payload_hash: str, existing: Mapping[str, Any]) -> RawReceipt:
        bucket = "poisoned" if code == "native_id_payload_conflict" else "collisions"
        error = contained_path(self.root, "errors", bucket, f"{event_id}.json")
        atomic_write_json(error, {"code": code, "raw_event_id": event_id, "raw_payload_hash": payload_hash, "existing_raw_event_id": existing.get("raw_event_id"), "raw_payload": event.raw_payload, "privacy": "private"}, self.root)
        return RawReceipt(
            raw_event_id=event_id,
            accepted=False,
            deduplicated=False,
            raw_location=None,
            routing_status="quarantined",
            diagnostics={"code": code},
        )


def _identity_document(event: NativeAgentEvent, include_payload_hash: bool) -> dict[str, Any]:
    stable = _uses_stable_native_id(event)
    document: dict[str, Any] = {
        "contract": "processforge.raw-identity.v1" if include_payload_hash else "processforge.native-identity.v1",
        "provider": _text(event.provider, "provider"),
        "adapter": _text(event.adapter, "adapter"),
        "native_event_type": _text(event.native_event_type, "native_event_type"),
        "native_id_scope": event.native_id_scope,
        "native_event_id": _optional(event.native_event_id) if stable else None,
        "source_session_id": _optional(event.source_session_id) if not stable or event.native_id_scope == "session" else None,
        "source_project_ref": _optional(event.source_project_ref) if not stable or event.native_id_scope == "project" else None,
        "payload_version": _text(event.payload_version, "payload_version"),
    }
    if include_payload_hash:
        document["raw_payload_hash"] = raw_payload_hash(event.raw_payload)
    return document


def _uses_stable_native_id(event: NativeAgentEvent) -> bool:
    return bool(_optional(event.native_event_id) and event.native_event_id_stable)


def _validate(event: NativeAgentEvent, max_payload_bytes: int) -> None:
    if not isinstance(event, NativeAgentEvent) or not isinstance(event.raw_payload, Mapping):
        raise RawIngressError("event must be NativeAgentEvent with object raw_payload")
    if event.native_id_scope not in {"provider", "adapter", "session", "project"}:
        raise RawIngressError("unsupported native_id_scope")
    _identity_document(event, include_payload_hash=True)
    if len(canonical_json(event.raw_payload)) > max_payload_bytes:
        raise RawIngressError("raw payload exceeds configured size limit")


def _normalise_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalised: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RawIngressError("JSON object keys must be strings")
            normalised_key = unicodedata.normalize("NFC", key)
            if normalised_key in normalised:
                raise RawIngressError("duplicate JSON key after NFC normalisation")
            normalised[normalised_key] = _normalise_json(item)
        return normalised
    if isinstance(value, (list, tuple)):
        return [_normalise_json(item) for item in value]
    raise RawIngressError(f"not JSON serializable: {type(value).__name__}")


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RawIngressError(f"{name} must be a non-empty string")
    return unicodedata.normalize("NFC", value).strip()


def _optional(value: str | None) -> str | None:
    return unicodedata.normalize("NFC", value).strip() or None if isinstance(value, str) else None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Windows does not consistently map a non-existent PID to
        # ProcessLookupError (for example WinError 11).  A recovery helper
        # must treat that as dead rather than crash while assessing a stale
        # lease.  PermissionError above remains the conservative live case.
        return False
    return True


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
