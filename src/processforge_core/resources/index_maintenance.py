"""Own explicit index execution, writer coordination and durable recovery.

Construction is cold. Workplace maintenance selects the live registered
catalogue; scoped CLI operations retain their supplied project snapshot.
Neither a constructor nor this backend seam grants access to source material.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, Literal, cast

from processforge_core.common.clock import now_utc
from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.resources.catalog_read import WorkplaceSearchCatalogReader
from processforge_core.resources.index_backend import (
    ResourceIndexBackend,
    ResourceIndexBackendFactory,
)
from processforge_core.resources.index_observation import (
    invalidation_notifications_path,
    invalidation_token_path,
    maintenance_state_path,
    pending_invalidation_notifications,
    read_invalidation_token,
)
from processforge_core.resources.local_search import (
    LocalSearchError,
    ResourceSearchIndex,
    authorized_roots,
    normalize_indexing_policy,
)

_REPORT = "runtime/search/latest-maintenance.yaml"
_SAFE_ERRORS = frozenset(
    {
        "allowed_resources_changed",
        "document_fingerprint_changed",
        "document_read_failed",
        "document_scan_failed",
        "fts5_unavailable",
        "index_schema_missing",
        "index_schema_mismatch",
        "index_unreadable",
        "resource_not_indexed",
        "scope_not_indexed",
        "snapshot_checksum_changed",
    }
)
_COORDINATION_ERRORS = frozenset(
    {
        "search_maintenance_busy",
        "search_maintenance_lock_unavailable",
        "search_maintenance_state_write_failed",
        "search_maintenance_report_write_failed",
        "search_maintenance_source_failed",
        "search_maintenance_selection_invalid",
        "search_maintenance_resource_missing",
    }
)


class IndexMaintenanceError(RuntimeError):
    """Describe a bounded coordination or required persistence failure."""

    def __init__(self, code: str) -> None:
        """Store a portable diagnostic code without private exception text."""
        self.code = (
            code if code in _COORDINATION_ERRORS else "search_maintenance_failed"
        )
        super().__init__(self.code)


def _safe_reason(reason: str) -> str:
    return reason if re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", reason) else "explicit"


def _safe_error(error: object) -> str:
    if isinstance(error, IndexMaintenanceError):
        return (
            error.code
            if error.code in _COORDINATION_ERRORS
            else "search_maintenance_failed"
        )
    if isinstance(error, LocalSearchError):
        return error.code if error.code in _SAFE_ERRORS else "search_maintenance_failed"
    if isinstance(error, sqlite3.Error):
        return "search_maintenance_database_failed"
    if isinstance(error, OSError):
        return "search_maintenance_io_failed"
    if isinstance(error, str) and error in _SAFE_ERRORS:
        return error
    return "search_maintenance_failed"


def _atomic_write(path: Path, content: str) -> None:
    """Publish a flushed file beside its destination, retaining prior bytes on error."""
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    staging = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        staging.unlink(missing_ok=True)


def _writer_lock(workplace_root: Path) -> IO[bytes]:
    """Try once for an OS-owned lock; closing or process death releases it."""
    folder = maintenance_state_path(workplace_root).parent
    try:
        folder.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(folder / "maintenance.lock", os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        raise IndexMaintenanceError("search_maintenance_lock_unavailable") from error
    stream = os.fdopen(descriptor, "r+b")
    try:
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            busy = error.errno in {
                errno.EACCES,
                errno.EAGAIN,
                errno.EDEADLK,
                errno.EBUSY,
            }
            code = (
                "search_maintenance_busy"
                if busy
                else "search_maintenance_lock_unavailable"
            )
            raise IndexMaintenanceError(code) from error
        # The caller owns this file context. Closing releases the OS lock
        # without mutating a frozen backend exception's traceback. Keep the
        # file in place so concurrent clients use the same inode.
        return stream
    except BaseException:
        stream.close()
        raise


def _previous_status(workplace_root: Path) -> str | None:
    try:
        value = json.loads(
            maintenance_state_path(workplace_root).read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        return None
    except (OSError, ValueError, UnicodeError):
        return "unavailable"
    if isinstance(value, dict) and value.get("status") in (
        "running",
        "complete",
        "failed",
    ):
        return str(value["status"])
    return "unavailable"


def _previous_invalidation(workplace_root: Path) -> str | None:
    try:
        value = json.loads(
            maintenance_state_path(workplace_root).read_text(encoding="utf-8")
        )
    except (OSError, ValueError, UnicodeError):
        return None
    token = value.get("invalidation_token") if isinstance(value, dict) else None
    return token if isinstance(token, str) else None


def _record_state(workplace_root: Path, record: dict[str, Any]) -> None:
    """Retain each running/terminal receipt and publish the current safe state."""
    path = maintenance_state_path(workplace_root)
    history = path.parent / "maintenance-history"
    try:
        history.mkdir(parents=True, exist_ok=True)
        text = json.dumps(record, ensure_ascii=True, sort_keys=True, allow_nan=False)
        text += "\n"
        receipt = history / f"{record['attempt_id']}-{record['status']}.json"
        _atomic_write(receipt, text)
        _atomic_write(path, text)
    except OSError as error:
        raise IndexMaintenanceError("search_maintenance_state_write_failed") from error


def _pending_notifications(
    workplace_root: Path,
) -> list[tuple[Path, str, set[str] | None]]:
    """Capture unique durable notifications without reading any resource body."""
    result: list[tuple[Path, str, set[str] | None]] = []
    folder = invalidation_notifications_path(workplace_root)
    try:
        for name in pending_invalidation_notifications(workplace_root):
            if not re.fullmatch(r"[a-f0-9]{32}\.json", name):
                raise ValueError("notification name invalid")
            path = folder / name
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                data = {}
            values = data.get("resource_ids") if isinstance(data, dict) else None
            resources = (
                set(values)
                if isinstance(values, list)
                and values
                and all(isinstance(value, str) and value for value in values)
                else None
            )
            token = hashlib.sha256((path.stem + "\n").encode("utf-8")).hexdigest()
            result.append((path, token, resources))
    except (OSError, ValueError):
        raise IndexMaintenanceError("search_maintenance_state_write_failed") from None
    return result


def _retire_notifications(
    workplace_root: Path, notifications: list[tuple[Path, str, set[str] | None]]
) -> None:
    """Retire only captured derived files while the durable guard is running."""
    folder = invalidation_notifications_path(workplace_root).resolve()
    try:
        if not folder.is_relative_to(workplace_root.resolve()):
            raise OSError("notification folder outside workplace")
        for path, _token, _resources in notifications:
            if path.parent.resolve() != folder:
                raise OSError("notification boundary changed")
            path.unlink(missing_ok=True)
    except OSError:
        raise IndexMaintenanceError("search_maintenance_state_write_failed") from None


def _successful(result: dict[str, Any], operation: str) -> bool:
    if operation == "workplace":
        return all(row.get("status") == "ok" for row in result["results"])
    if operation == "tick":
        after = result.get("after")
        return (
            isinstance(after, dict)
            and after.get("status") == "fresh"
            and not after.get("error")
            and not after.get("failed_file_count")
            and result.get("action") in ("none", "refresh", "rebuild")
        )
    return (
        result.get("status", "fresh") == "fresh"
        and not result.get("error")
        and not result.get("failed_file_count")
    )


def _invalidate_backend(backend: ResourceIndexBackend) -> None:
    """Leave derived schema repair to the immediately following explicit operation."""
    try:
        backend.mark_dirty(reason="pending-invalidation")
    except LocalSearchError as error:
        if error.code not in {"index_schema_missing", "index_schema_mismatch"}:
            raise


@dataclass(frozen=True)
class WorkplaceIndexMaintenanceService:
    """Coordinate explicit writes over the existing snapshot-aware index backend.

    Args:
        workplace_root: Explicitly authorized workplace target.
        distribution_root: Optional installed distribution used by the catalogue.
        backend_factory: Cold operation-local backend constructor. Its positional
            arguments are project root, snapshot and workplace root.

    No transport, Runtime, project enumeration or Main callback is needed.
    """

    workplace_root: Path
    distribution_root: Path | None = field(default=None, kw_only=True)
    backend_factory: ResourceIndexBackendFactory = field(
        default=ResourceSearchIndex, kw_only=True, repr=False, compare=False
    )

    def mark_dirty(
        self, *, reason: str = "dirty", resource_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Durably invalidate without scanning or waiting for an active writer.

        A concurrent pass acknowledges only its starting identity, so this atomic
        notification survives publication of that pass's older collected corpus.
        """
        path = invalidation_token_path(self.workplace_root)
        identity = uuid.uuid4().hex
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            folder = invalidation_notifications_path(self.workplace_root)
            folder.mkdir(parents=True, exist_ok=True)
            _atomic_write(
                folder / (identity + ".json"),
                json.dumps({"resource_ids": resource_ids}, sort_keys=True) + "\n",
            )
            _atomic_write(path, identity + "\n")
        except OSError:
            raise IndexMaintenanceError(
                "search_maintenance_state_write_failed"
            ) from None
        marked = 0
        try:
            with _writer_lock(self.workplace_root):
                # Retain the released idle dirty-state diagnostic. The durable
                # token is authoritative if the writer/SQLite is already busy.
                backend = self.backend_factory(
                    self.workplace_root,
                    {"search_index_scope": "workplace"},
                    self.workplace_root,
                )
                result = backend.mark_dirty(reason=_safe_reason(reason))
                count = result.get("marked_scope_count")
                if type(count) is int and count >= 0:
                    marked = count
        except (IndexMaintenanceError, LocalSearchError, sqlite3.Error, OSError):
            # The required notification already persisted. Never wait or lose it
            # merely because this compatibility-only SQLite update was refused.
            marked = 0
        return {
            "schema_version": 1,
            "kind": "pf.search_index.dirty",
            "status": "stale",
            "reason": _safe_reason(reason),
            "marked_scope_count": marked,
        }

    def run(
        self, *, reason: str = "manual", verify_files: bool = True
    ) -> dict[str, Any]:
        """Maintain the workplace catalogue and return the schema1 maintenance report.

        Failures return a safe error row. Required state/report write failures
        never report success. A busy writer is refused without changing its state.
        """
        safe_reason = _safe_reason(reason)
        try:
            return self._execute(
                scope="workplace",
                operation="workplace",
                reason=safe_reason,
                perform=lambda invalidated: self._maintain_workplace(
                    safe_reason, verify_files, invalidated
                ),
            )
        except Exception as error:
            return self._payload(
                safe_reason,
                {"scope": "workplace", "status": "error", "error": _safe_error(error)},
                report=None,
            )

    def run_resources(self, resource_ids: list[str]) -> dict[str, Any]:
        """Refresh only explicitly selected registered resources, retaining others.

        A selected pass acknowledges only known changes fully covered by its IDs;
        unknown/unselected changes and old failures remain pending. The same lock and durable
        state protect manual, scoped, batch and future scheduled operations.
        """
        if (
            not isinstance(resource_ids, list)
            or not resource_ids
            or any(
                not isinstance(item, str) or not item.strip() for item in resource_ids
            )
        ):
            raise IndexMaintenanceError("search_maintenance_selection_invalid")
        selected = sorted(set(resource_ids))

        def perform(_invalidated: bool) -> dict[str, Any]:
            catalogue = (
                WorkplaceSearchCatalogReader(self.workplace_root)
                if self.distribution_root is None
                else WorkplaceSearchCatalogReader(
                    self.workplace_root, distribution_root=self.distribution_root
                )
            )
            snapshot = catalogue.runtime_snapshot()
            records = [
                record
                for record in snapshot.get("local_search_resources", [])
                if isinstance(record, dict) and record.get("id") in selected
            ]
            if {record.get("id") for record in records} != set(selected):
                raise IndexMaintenanceError("search_maintenance_resource_missing")
            identity = hashlib.sha256(
                json.dumps(records, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            narrowed = {
                "search_index_scope": "resources",
                "snapshot": {"checksum": f"resources:{identity}"},
                "local_search_resources": records,
                "selected_catalogue_metadata": snapshot,
            }
            enabled = {
                str(record["id"])
                for record in records
                if normalize_indexing_policy(record).get("mode") != "none"
            }
            available = {
                resource.resource_id
                for resource in authorized_roots(self.workplace_root, narrowed)
            }
            if not enabled.issubset(available):
                raise IndexMaintenanceError("search_maintenance_resource_missing")
            backend = self.backend_factory(
                self.workplace_root, narrowed, self.workplace_root
            )
            try:
                result = backend.refresh()
            except LocalSearchError as error:
                if error.code in {"document_read_failed", "document_scan_failed"}:
                    raise IndexMaintenanceError(
                        "search_maintenance_source_failed"
                    ) from None
                raise
            return {
                **result,
                "resource_ids": selected,
                "workplace_reconciled": False,
            }

        return self._execute(
            scope="resources",
            operation="refresh",
            reason="knowledge-add-batch",
            perform=perform,
            selected_resources=set(selected),
        )

    def run_scoped(
        self,
        project_root: Path,
        snapshot: dict[str, Any],
        *,
        operation: Literal["refresh", "rebuild", "tick"],
        verify_files: bool = True,
    ) -> dict[str, Any]:
        """Execute a legacy project operation without loading a workplace catalogue.

        Return the backend payload unchanged and re-raise backend exceptions so
        existing CLI output/error mapping stays with the caller. A project pass
        cannot clear incomplete workplace maintenance. The supplied snapshot
        must retain project scope; construction never widens its resource set.
        """
        if snapshot.get("search_index_scope") == "workplace":
            raise LocalSearchError("project_snapshot_required")
        if operation not in ("refresh", "rebuild", "tick"):
            raise LocalSearchError("maintenance_operation_invalid")

        def perform(invalidated: bool) -> dict[str, Any]:
            backend = self.backend_factory(project_root, snapshot, self.workplace_root)
            try:
                if invalidated:
                    _invalidate_backend(backend)
                if operation == "refresh":
                    return backend.refresh()
                if operation == "rebuild":
                    return backend.rebuild()
                return backend.maintenance_tick(verify_files=verify_files)
            except LocalSearchError as error:
                if error.code in {"document_read_failed", "document_scan_failed"}:
                    raise IndexMaintenanceError(
                        "search_maintenance_source_failed"
                    ) from None
                raise

        return self._execute(
            scope="project",
            operation=operation,
            reason=f"cli-{operation}",
            perform=perform,
        )

    def _execute(
        self,
        *,
        scope: str,
        operation: str,
        reason: str,
        perform: Callable[[bool], dict[str, Any]],
        selected_resources: set[str] | None = None,
    ) -> dict[str, Any]:
        with _writer_lock(self.workplace_root):
            previous = _previous_status(self.workplace_root)
            previous_token = _previous_invalidation(self.workplace_root)
            token = read_invalidation_token(self.workplace_root)
            invalidated = token != previous_token
            notifications = _pending_notifications(self.workplace_root)
            covered = (
                scope == "resources"
                and bool(notifications)
                and any(item[1] == token for item in notifications)
                and all(
                    item[2] and item[2].issubset(selected_resources or set())
                    for item in notifications
                )
                and previous not in ("running", "failed", "unavailable")
            )
            record: dict[str, Any] = {
                "schema_version": 1,
                "kind": "pf.search_index.maintenance_state",
                "attempt_id": uuid.uuid4().hex,
                "scope": scope,
                "operation": operation,
                "reason": reason,
                "started_at": now_utc(),
                "status": "running",
                "previous_status": previous,
                "invalidation_token": token
                if scope == "workplace" or covered
                else previous_token,
                "captured_notifications": [item[0].stem for item in notifications],
            }
            _record_state(self.workplace_root, record)
            try:
                result = perform(invalidated or bool(notifications))
                changed = read_invalidation_token(self.workplace_root) != token
                if changed and scope == "resources":
                    result.update(
                        {
                            "status": "stale",
                            "error": "search_maintenance_invalidated",
                        }
                    )
                if changed and operation == "workplace":
                    row = result["results"][0]
                    row.update(
                        {
                            "status": "degraded",
                            "search_status": "stale",
                            "error": "search_maintenance_invalidated",
                        }
                    )
                    try:
                        _atomic_write(
                            self.workplace_root / _REPORT, dump_yaml(result) + "\n"
                        )
                    except OSError as error:
                        raise IndexMaintenanceError(
                            "search_maintenance_report_write_failed"
                        ) from error
                complete = _successful(result, operation)
                incomplete = changed or (
                    scope != "workplace"
                    and (
                        ((invalidated or bool(notifications)) and not covered)
                        or previous in ("running", "failed", "unavailable")
                    )
                )
                if complete and not incomplete:
                    _retire_notifications(self.workplace_root, notifications)
            except BaseException as error:
                _record_state(
                    self.workplace_root,
                    {
                        **record,
                        "status": "failed",
                        "finished_at": now_utc(),
                        "error": _safe_error(error),
                    },
                )
                raise
            terminal = {
                **record,
                "status": "complete" if complete and not incomplete else "failed",
                "finished_at": now_utc(),
            }
            if not complete or incomplete:
                terminal["error"] = (
                    "search_maintenance_incomplete"
                    if incomplete
                    else "search_maintenance_failed"
                )
            _record_state(self.workplace_root, terminal)
            return result

    def _maintain_workplace(
        self, reason: str, verify_files: bool, invalidated: bool
    ) -> dict[str, Any]:
        row: dict[str, Any] = {"scope": "workplace", "status": "pending"}
        try:
            catalogue = (
                WorkplaceSearchCatalogReader(self.workplace_root)
                if self.distribution_root is None
                else WorkplaceSearchCatalogReader(
                    self.workplace_root, distribution_root=self.distribution_root
                )
            )
            snapshot = catalogue.runtime_snapshot()
            backend = self.backend_factory(
                self.workplace_root, snapshot, self.workplace_root
            )
            if invalidated:
                _invalidate_backend(backend)
            tick = backend.maintenance_tick(verify_files=verify_files)
            after = (
                cast(dict[str, Any], tick.get("after"))
                if isinstance(tick.get("after"), dict)
                else {}
            )
            action = tick.get("action")
            status = after.get("status")
            generation = after.get("generation")
            if action not in (
                "none",
                "refresh",
                "rebuild",
                "failed_refresh",
                "failed_rebuild",
            ):
                action = "failed"
            if status not in ("fresh", "missing", "stale", "degraded"):
                status = "degraded"
            if not isinstance(generation, str) or not re.fullmatch(
                r"[a-zA-Z0-9:_.-]{1,128}", generation
            ):
                generation = None
            row.update(
                {
                    "status": "ok" if _successful(tick, "tick") else "degraded",
                    "action": action,
                    "search_status": status,
                    "generation": generation,
                }
            )
            for key in ("document_count", "stale_resource_count", "failed_file_count"):
                value = after.get(key)
                row[key] = value if type(value) is int and value >= 0 else None
            if after.get("error"):
                row["error"] = _safe_error(after["error"])
        except Exception as error:
            row.update({"status": "error", "error": _safe_error(error)})
        payload = self._payload(reason, row, report=_REPORT)
        try:
            _atomic_write(self.workplace_root / _REPORT, dump_yaml(payload) + "\n")
        except OSError as error:
            raise IndexMaintenanceError(
                "search_maintenance_report_write_failed"
            ) from error
        return payload

    @staticmethod
    def _payload(
        reason: str, row: dict[str, Any], *, report: str | None
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "pf.search_index.maintenance",
            "created_at": now_utc(),
            "reason": reason,
            "scope": "workplace",
            "project_count": 0,
            "results": [row],
            "report": report,
        }
