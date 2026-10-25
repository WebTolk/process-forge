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
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from processforge_core.maintenance.storage_migration import StorageMigrationHost

from processforge_core.configuration import ConfigurationProvider
from processforge_core.database import DatabaseFactory, SQLiteDriver


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
        _normalise_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
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
    digest = hashlib.sha256(
        canonical_json(_identity_document(event, include_payload_hash=False))
    ).hexdigest()
    return "native_" + digest


def deterministic_derived_key(
    raw_id: str,
    derived_kind: str,
    processor_id: str,
    processor_version: str,
    semantic_target: Any,
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
        with tempfile.NamedTemporaryFile(
            "wb", dir=target.parent, prefix=f".{target.name}.", delete=False
        ) as handle:
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
                os.write(
                    self._fd,
                    json.dumps(
                        {
                            "pid": os.getpid(),
                            "host": socket.gethostname(),
                            "created_at": time.time(),
                        }
                    ).encode("utf-8"),
                )
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise RawIngressError(
                        f"timed out waiting for raw ingress lock: {self.path.name}"
                    )
                time.sleep(0.05)

    def __exit__(self, *_: object) -> None:
        if self._fd is not None:
            os.close(self._fd)
        self.path.unlink(missing_ok=True)


def recover_stale_lock(
    path: Path, *, stale_seconds: float, force: bool = False
) -> bool:
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
            raise RawIngressError(
                f"lock metadata is unreadable; explicit force required: {path.name}"
            )
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
    """Durably admit native events into an explicitly selected SQL journal."""

    def __init__(
        self,
        workplace_root: Path | str,
        *,
        max_payload_bytes: int = 1_048_576,
        flow_root: Path | None = None,
        record_raw: bool | None = None,
        configuration: ConfigurationProvider | None = None,
        driver: SQLiteDriver | None = None,
        storage_host: StorageMigrationHost | None = None,
    ) -> None:
        from processforge_core.raw_hook_journal import RawHookJournal

        self.workplace_root = Path(workplace_root).resolve(strict=False)
        self.root = (
            contained_path(flow_root, "runtime", "agent-events")
            if flow_root is not None
            else contained_path(self.workplace_root, "runtime", "agent-events")
        )
        self.database = contained_path(self.root, "hooks.sqlite3")
        if max_payload_bytes <= 0:
            raise RawIngressError("max_payload_bytes must be positive")
        if record_raw is not None and type(record_raw) is not bool:
            raise RawIngressError("record_raw must be boolean")
        self.max_payload_bytes = max_payload_bytes
        self.record_raw = record_raw
        self.configuration = configuration
        self.project_root = flow_root.parent if flow_root is not None else None
        self.storage = RawHookJournal(driver=driver, storage_host=storage_host)

    def _operation(self):
        """Consume the host snapshot without discovering project configuration."""
        from processforge_core.raw_hook_journal import RawHookJournal

        storage = self.storage
        retain_raw = self.record_raw
        from processforge_core.project.configuration_inputs import (
            operation_configuration,
            operation_device_path,
            operation_storage_host,
        )

        configuration = self.configuration or operation_configuration(
            self.project_root, self.workplace_root
        )
        if configuration is not None:
            config = configuration.current()
            if storage.storage_host is None:
                from processforge_core.composition import build_storage_migration_host

                host = operation_storage_host(
                    self.database
                ) or build_storage_migration_host(
                    project_root=self.project_root,
                    workplace_root=self.workplace_root,
                    device_config_path=operation_device_path(
                        self.project_root,
                        self.workplace_root,
                        configuration.device_path,
                    ),
                    configuration=configuration,
                )
                storage = RawHookJournal(driver=storage.driver, storage_host=host)
            if storage.driver is None:
                storage = RawHookJournal(
                    driver=DatabaseFactory.resolve_driver(config.database),
                    storage_host=storage.storage_host,
                )
            if retain_raw is None:
                retain_raw = config.logging.raw_hooks
        return storage, True if retain_raw is None else retain_raw

    def ingest(
        self, event: NativeAgentEvent, received_at: datetime | None = None
    ) -> RawReceipt:
        from pf_native_control import operation_lease

        with operation_lease():
            from processforge_core.sqlite_storage import JournalMigrationRequired

            _validate(event, self.max_payload_bytes)
            if not self.database.is_file():
                legacy_roots = {
                    self.root / "raw/v1",
                    self.workplace_root / "runtime/agent-events/raw/v1",
                }
                if any(any(root.rglob("*.ndjson")) for root in legacy_roots):
                    raise JournalMigrationRequired(
                        "raw_journal_migration_required: run tools/migrate-hook-journals.py"
                    )
            moment = (received_at or datetime.now(timezone.utc)).astimezone(
                timezone.utc
            )
            event_id = raw_event_id(event)
            record = self._raw_record(
                event,
                event_id,
                raw_payload_hash(event.raw_payload),
                stable_native_identity_key(event),
                moment,
            )
            storage, retain_raw = self._operation()
            result = storage.accept(self.database, record, retain_raw=retain_raw)
            return RawReceipt(
                event_id,
                result["accepted"],
                result["deduplicated"],
                result["raw_location"],
                result["routing_status"],
                diagnostics=result["diagnostics"],
            )

    def finish(self, event_id: str, response: dict[str, Any]) -> None:
        from pf_native_control import operation_lease

        with operation_lease():
            storage, _retain_raw = self._operation()
            storage.finish(self.database, event_id, response)

    def result(self, event_id: str) -> dict[str, Any] | None:
        from pf_native_control import operation_lease

        with operation_lease():
            storage, _retain_raw = self._operation()
            return storage.result(self.database, event_id)

    def records(self, **filters):
        from pf_native_control import operation_lease

        with operation_lease():
            storage, _retain_raw = self._operation()
            yield from storage.records(self.database, **filters)

    def _raw_record(
        self,
        event: NativeAgentEvent,
        event_id: str,
        payload_hash: str,
        native_key: str | None,
        moment: datetime,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "raw_event_id": event_id,
            "provider": event.provider,
            "adapter": event.adapter,
            "native_event_type": event.native_event_type,
            "native_event_id": event.native_event_id,
            "native_id_scope": event.native_id_scope,
            "native_event_id_stable": event.native_event_id_stable,
            "source_session_id": event.source_session_id,
            "source_project_ref": event.source_project_ref,
            "payload_version": event.payload_version,
            "received_at": moment.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
            "raw_payload": event.raw_payload,
            "raw_payload_hash": payload_hash,
            "native_identity_key": native_key,
            "privacy": "private",
        }


def _identity_document(
    event: NativeAgentEvent, include_payload_hash: bool
) -> dict[str, Any]:
    stable = _uses_stable_native_id(event)
    document: dict[str, Any] = {
        "contract": "processforge.raw-identity.v1"
        if include_payload_hash
        else "processforge.native-identity.v1",
        "provider": _text(event.provider, "provider"),
        "adapter": _text(event.adapter, "adapter"),
        "native_event_type": _text(event.native_event_type, "native_event_type"),
        "native_id_scope": event.native_id_scope,
        "native_event_id": _optional(event.native_event_id) if stable else None,
        "source_session_id": _optional(event.source_session_id)
        if not stable or event.native_id_scope == "session"
        else None,
        "source_project_ref": _optional(event.source_project_ref)
        if not stable or event.native_id_scope == "project"
        else None,
        "payload_version": _text(event.payload_version, "payload_version"),
    }
    if include_payload_hash:
        document["raw_payload_hash"] = raw_payload_hash(event.raw_payload)
    return document


def _uses_stable_native_id(event: NativeAgentEvent) -> bool:
    return bool(_optional(event.native_event_id) and event.native_event_id_stable)


def _validate(event: NativeAgentEvent, max_payload_bytes: int) -> None:
    if not isinstance(event, NativeAgentEvent) or not isinstance(
        event.raw_payload, Mapping
    ):
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
    return (
        unicodedata.normalize("NFC", value).strip() or None
        if isinstance(value, str)
        else None
    )


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
