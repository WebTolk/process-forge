"""Scan legacy journals, verify identities and preserve exact corrupt bytes."""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ..database import DatabaseFactory, SQLiteDriver
from ..executions.model import ExecutionKey, ExecutionRecord
from ..executions.projection import canonical_json, compatibility_payload
from .contracts import (
    JournalRow,
    JournalSource,
    JsonObject,
    MaintenanceError,
    SourceKind,
)


@dataclass(frozen=True)
class ExecutionSnapshot:
    """One bounded legacy latest snapshot; original bytes are never rewritten."""

    relative_path: str
    raw: bytes
    payload: JsonObject
    key: ExecutionKey
    next_attempt: int
    invalid_historical: bool

    def record(self, generation: int) -> ExecutionRecord:
        """Map only observable latest state, with no invented overwritten history."""
        status = self.payload["status"]
        prepared = status in {"planned", "ready", "manual_required", "blocked"}
        return ExecutionRecord(
            self.key,
            None,
            1,
            generation,
            "prepared" if prepared else "absent",
            None if prepared else status,
            "pending",
            None,
            None if prepared else 1,
            canonical_json(self.payload),
            0,
        )


def execution_ordered(directory: Path, *, subtree: bool = False) -> Iterator[Path]:
    """Visit raw UTF-8 names in chunks of 256 without an all-history path list.

    Repeated directory passes trade CPU for bounded memory on read-only plans.
    Import evidence is an external NDJSON spool, not an in-memory envelope.
    """
    _check_links(directory, "migration_source_symlink")
    if not directory.exists():
        return
    last: bytes | None = None
    suffix = "/" if subtree else ""
    while True:
        with os.scandir(directory) as entries:
            names = heapq.nsmallest(
                256,
                (
                    (entry.name + suffix).encode("utf-8")
                    for entry in entries
                    if last is None or (entry.name + suffix).encode("utf-8") > last
                ),
            )
        if not names:
            return
        for name in names:
            path = directory / (
                name.decode("utf-8")[:-1] if subtree else name.decode("utf-8")
            )
            _check_links(path, "migration_source_symlink")
            yield path
        last = names[-1]


def execution_bytes(path: Path) -> bytes:
    """Read one regular, stable, bounded status or direct receipt body only."""
    before = _signature(path)
    if before[2] > 65536:
        raise MaintenanceError("execution_source_too_large")
    with path.open("rb") as handle:
        raw = handle.read(65537)
        if _stat_signature(os.fstat(handle.fileno()))[:4] != before[:4]:
            raise MaintenanceError("migration_source_changed")
    if len(raw) > 65536 or _signature(path) != before:
        raise MaintenanceError("migration_source_changed")
    return raw


def execution_json(raw: bytes) -> JsonObject:
    """Decode exact schema input, rejecting duplicates, NUL and nonfinite data."""
    try:
        value = _decode(raw)

        # Compatibility DTO validation recursively rejects NUL/invalid Unicode.
        def walk(item: object) -> None:
            if isinstance(item, str):
                if "\x00" in item:
                    raise ValueError("json_nul")
                item.encode("utf-8")
            elif isinstance(item, dict):
                for key, child in item.items():
                    walk(key)
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)

        walk(value)
        canonical_json(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise MaintenanceError("execution_source_invalid") from None


def execution_snapshots(
    project: Path, flow: Path, project_id: str, *, skip_terminal_invalid: bool
) -> Iterator[tuple[JsonObject, ExecutionSnapshot | None, bytes | None]]:
    """Stream inventory facts and latest snapshots, never output/report inputs.

    Directory names are allocation evidence only. Direct bounded receipts enter
    the manifest for host quiescence verification, never recreate missing history.
    Unknown/active statuses and ambiguous attempt names always block.
    """
    import re

    def fact(path: Path, raw: bytes) -> JsonObject:
        return {
            "relative_path": path.relative_to(project).as_posix(),
            "size": len(raw),
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }

    def receipt_bytes(path: Path, expected_attempt: int | None = None) -> bytes:
        raw = execution_bytes(path)
        body = execution_json(raw)
        if type(body.get("schema_version")) is not int or body["schema_version"] != 1:
            raise MaintenanceError("execution_source_invalid")
        expected: dict[str, object] = {
            "project_id": project_id,
            "run_id": run.name,
            "task_id": task.name,
        }
        if expected_attempt is not None:
            expected["attempt"] = expected_attempt
        if any(
            key in body and (type(body[key]) is not type(value) or body[key] != value)
            for key, value in expected.items()
        ):
            raise MaintenanceError("execution_identity_conflict")
        return raw

    root = flow / "runtime/agent-runs"
    for run in execution_ordered(root, subtree=True):
        if not run.is_dir():
            raise MaintenanceError("execution_inventory_invalid")
        for task in execution_ordered(run, subtree=True):
            if not task.is_dir():
                raise MaintenanceError("execution_inventory_invalid")
            floor = 1
            for attempt in execution_ordered(task / "attempts"):
                if (
                    not attempt.is_dir()
                    or re.fullmatch(r"[1-9][0-9]{0,18}", attempt.name) is None
                    or int(attempt.name) >= 9223372036854775807
                ):
                    raise MaintenanceError("execution_attempt_directory_invalid")
                floor = max(floor, int(attempt.name) + 1)
                yield (
                    {"directory": attempt.relative_to(project).as_posix()},
                    None,
                    None,
                )
                for name in ("exit.json", "heartbeat.json", "process.json"):
                    receipt = attempt / name
                    _check_links(receipt, "migration_source_symlink")
                    if receipt.exists():
                        raw = receipt_bytes(receipt, int(attempt.name))
                        yield fact(receipt, raw), None, raw
            for name in ("exit.json", "heartbeat.json", "process.json"):
                receipt = task / name
                _check_links(receipt, "migration_source_symlink")
                if receipt.exists():
                    raw = receipt_bytes(receipt)
                    yield fact(receipt, raw), None, raw
            status_path = task / "status.json"
            _check_links(status_path, "migration_source_symlink")
            if not status_path.exists():
                # Missing status proves nothing about activity. The independent
                # host proof still gates planning/freeze/cutover. Names reserve
                # allocation only; they never reconstruct missing executions.
                missing: JsonObject = {
                    "missing_status": status_path.relative_to(project).as_posix()
                }
                if floor > 1:
                    ExecutionKey(project_id, run.name, task.name, floor)
                    missing["allocation_floor"] = {
                        "run_id": run.name,
                        "task_id": task.name,
                        "next_attempt": floor,
                    }
                yield missing, None, None
                continue
            raw = execution_bytes(status_path)
            payload = execution_json(raw)
            number = payload.get("attempt")
            if type(number) is not int or not 1 <= number < 9223372036854775807:
                raise MaintenanceError("execution_attempt_required")
            key = ExecutionKey(project_id, run.name, task.name, number)
            if (
                type(payload.get("schema_version")) is not int
                or payload["schema_version"] != 1
                or payload.get("run_id") != run.name
                or payload.get("task_id") != task.name
                or payload.get("project_id", project_id) != project_id
            ):
                raise MaintenanceError("execution_identity_conflict")
            if payload.get("status") not in {
                "planned",
                "ready",
                "manual_required",
                "blocked",
                "completed",
                "failed",
                "timed_out",
                "cancelled",
                "unknown_exit",
                "lost",
            }:
                raise MaintenanceError("execution_activity_unknown")
            invalid = False
            try:
                compatibility_payload(canonical_json(payload), key)
            except ValueError:
                if not skip_terminal_invalid or payload["status"] not in {
                    "completed",
                    "failed",
                    "timed_out",
                    "cancelled",
                    "unknown_exit",
                    "lost",
                }:
                    raise MaintenanceError("execution_source_invalid") from None
                # Historical classification additionally requires the exact whole
                # inventory host proof at freeze/cutover. Raw bytes are quarantined.
                invalid = True
            if payload["status"] in {
                "planned",
                "ready",
                "manual_required",
                "blocked",
            } and (
                payload.get("pid") is not None or payload.get("started_at") is not None
            ):
                raise MaintenanceError("execution_activity_unknown")
            snapshot = ExecutionSnapshot(
                status_path.relative_to(project).as_posix(),
                raw,
                cast(JsonObject, payload),
                key,
                max(floor, number + 1),
                invalid,
            )
            item = fact(status_path, raw)
            item.update(
                semantic_checksum="sha256:"
                + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
                next_attempt=snapshot.next_attempt,
                skipped=invalid,
                allocation_floor={
                    "run_id": run.name,
                    "task_id": task.name,
                    "next_attempt": snapshot.next_attempt,
                },
            )
            yield item, snapshot, raw


_Signature = tuple[int, int, int, int, int]
_RawValidator = Callable[[JsonObject], None]
_DIAGNOSTIC_LIMIT = 100
_RAW_REASONS = frozenset(
    {
        "raw_schema_invalid",
        "raw_payload_hash_mismatch",
        "raw_received_at_required",
        "raw_identity_mismatch",
    }
)
_RECORD_REASONS = _RAW_REASONS | {
    "raw_identity_invalid",
    "raw_project_ref_invalid",
    "event_id_required",
    "json_nonfinite_number",
    "json_duplicate_key",
    "json_encoding_invalid",
    "json_invalid",
    "json_nesting_invalid",
    "record_not_object",
}


def _check_links(path: Path, code: str) -> None:
    """Reject symlinks and Windows reparse points in an explicit path."""
    absolute = path.absolute()
    for part in (absolute, *absolute.parents):
        try:
            value = part.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise MaintenanceError(code) from None
        if stat.S_ISLNK(value.st_mode) or (
            getattr(value, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise MaintenanceError(code)


def _stat_signature(value: os.stat_result) -> _Signature:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _signature(path: Path) -> _Signature:
    _check_links(path, "migration_source_symlink")
    try:
        value = path.stat()
    except OSError:
        raise MaintenanceError("migration_source_unavailable") from None
    if not stat.S_ISREG(value.st_mode):
        raise MaintenanceError("migration_source_not_regular")
    return _stat_signature(value)


def _snapshot(path: Path) -> JsonObject:
    before = _signature(path)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            # On Windows stat/fstat can expose different ctime semantics. Compare
            # common handle fields here, then the full path signature below.
            if _stat_signature(os.fstat(source.fileno()))[:4] != before[:4]:
                raise MaintenanceError("migration_source_changed")
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
            if _stat_signature(os.fstat(source.fileno()))[:4] != before[:4]:
                raise MaintenanceError("migration_source_changed")
    except OSError:
        raise MaintenanceError("migration_source_unavailable") from None
    if _signature(path) != before:
        raise MaintenanceError("migration_source_changed")
    return {
        "path": str(path),
        "signature": list(before),
        "sha256": digest.hexdigest(),
    }


def _reject_constant(_value: str) -> Any:
    raise ValueError("json_nonfinite_number")


def _object(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("json_duplicate_key")
        result[key] = value
    return result


def _json_bytes(value: JsonObject) -> bytes:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return encoded.encode("utf-8")


def _decode(line: bytes) -> JsonObject:
    try:
        record = json.loads(
            line.decode("utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_object,
        )
    except UnicodeError:
        raise ValueError("json_encoding_invalid") from None
    except json.JSONDecodeError:
        raise ValueError("json_invalid") from None
    except RecursionError:
        raise ValueError("json_nesting_invalid") from None
    if not isinstance(record, dict):
        raise ValueError("record_not_object")
    try:
        _json_bytes(record)
    except UnicodeError:
        raise ValueError("json_encoding_invalid") from None
    except ValueError:
        raise ValueError("json_nonfinite_number") from None
    except RecursionError:
        raise ValueError("json_nesting_invalid") from None
    return record


def _same_project(value: object, project: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return Path(value).expanduser().resolve() == project
    except (OSError, RuntimeError, ValueError):
        raise ValueError("raw_project_ref_invalid") from None


def _validate_native_record(record: JsonObject) -> None:
    """Use the existing pure native identity primitives without loading Host."""
    from pf_runtime.raw_ingress_kernel import (
        NativeAgentEvent,
        raw_event_id,
        raw_payload_hash,
        stable_native_identity_key,
    )

    if record.get("schema_version") != 1 or not isinstance(
        record.get("raw_payload"), dict
    ):
        raise ValueError("raw_schema_invalid")
    if record.get("raw_payload_hash") != raw_payload_hash(record["raw_payload"]):
        raise ValueError("raw_payload_hash_mismatch")
    # Legacy v1 did not persist these controls. Test the same finite set as the
    # existing migration; never manufacture a replacement identity.
    scopes = (
        [record["native_id_scope"]]
        if "native_id_scope" in record
        else ("provider", "adapter", "session", "project")
    )
    stable_values = (
        [record["native_event_id_stable"]]
        if "native_event_id_stable" in record
        else (True, False)
    )
    fields: JsonObject = {
        key: record.get(key)
        for key in (
            "provider",
            "adapter",
            "native_event_type",
            "raw_payload",
            "payload_version",
            "native_event_id",
            "source_session_id",
            "source_project_ref",
        )
    }
    for scope in scopes:
        for stable in stable_values:
            event = NativeAgentEvent(
                **fields,
                native_id_scope=scope,
                native_event_id_stable=stable,
            )
            if raw_event_id(event) == record.get(
                "raw_event_id"
            ) and stable_native_identity_key(event) == record.get(
                "native_identity_key"
            ):
                if not isinstance(record.get("received_at"), str):
                    raise ValueError("raw_received_at_required")
                return
    raise ValueError("raw_identity_mismatch")


def _new_report() -> JsonObject:
    return {
        "sources": [],
        "events_rows": 0,
        "raw_rows": 0,
        "unique_events": 0,
        "unique_raw": 0,
        "invalid": 0,
        "blocked": False,
        "other_project_raw": 0,
        "diagnostics": [],
        "read_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "skipped_rows": 0,
        "duplicate_rows": 0,
        "duplicate_events": 0,
        "duplicate_raw": 0,
        "blank_rows": 0,
        "filtered_rows": 0,
        "quarantine": {"status": "not_requested", "records": 0},
    }


def _exclusive_bytes(path: Path, data: bytes) -> None:
    """Write a new evidence file or verify identical bytes without replacement."""
    _check_links(path, "quarantine_path_unsafe")
    try:
        with path.open("xb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError:
        try:
            before = _signature(path)
            with path.open("rb") as existing:
                if _stat_signature(os.fstat(existing.fileno()))[:4] != before[:4]:
                    raise MaintenanceError("quarantine_evidence_conflict")
                if existing.read() != data:
                    raise MaintenanceError("quarantine_evidence_conflict")
            if _signature(path) != before:
                raise MaintenanceError("quarantine_evidence_conflict")
        except OSError:
            raise MaintenanceError("quarantine_evidence_unavailable") from None
    except OSError:
        raise MaintenanceError("quarantine_evidence_unavailable") from None


class _Quarantine:
    """Own deterministic evidence files for one fully exhausted scan."""

    def __init__(self, directory: Path, project: Path) -> None:
        _check_links(directory, "quarantine_path_unsafe")
        self.directory = directory.absolute()
        self.project = project
        self.records: list[JsonObject] = []
        try:
            (self.directory / "records").mkdir(parents=True, exist_ok=True)
        except OSError:
            raise MaintenanceError("quarantine_evidence_unavailable") from None
        _check_links(self.directory / "records", "quarantine_path_unsafe")

    def add(self, metadata: JsonObject, line: bytes) -> None:
        identifier = hashlib.sha256(_json_bytes(metadata)).hexdigest()
        member = f"records/{identifier}.bin"
        _exclusive_bytes(self.directory / member, line)
        self.records.append({**metadata, "file": member})

    def finish(
        self,
        sources: list[JsonObject],
        *,
        complete: bool = True,
        failure: str | None = None,
    ) -> JsonObject:
        for record in self.records:
            try:
                snapshot = _snapshot(self.directory / record["file"])
            except MaintenanceError:
                raise MaintenanceError("quarantine_evidence_conflict") from None
            if (
                snapshot["sha256"] != record["sha256"]
                or snapshot["signature"][2] != record["length"]
            ):
                raise MaintenanceError("quarantine_evidence_conflict")
        manifest = {
            "schema_version": 1,
            "contract": "processforge.journal-quarantine.v1",
            "project": str(self.project),
            "sources": sources,
            "records": self.records,
        }
        if not complete:
            manifest.update(scan_complete=False, scan_failure=failure)
        data = _json_bytes(manifest) + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        # An aborted later pass must not replace a completed earlier manifest.
        filename = "manifest.json" if complete else f"manifest.incomplete-{digest}.json"
        path = self.directory / filename
        _exclusive_bytes(path, data)
        receipt = {
            "status": "verified" if complete else "incomplete",
            "manifest": str(path),
            "sha256": digest,
            "records": len(self.records),
        }
        if not complete:
            receipt.update(scan_complete=False, records_verified=True)
        return receipt


def _identity(
    index: sqlite3.Connection, kind: SourceKind, record: JsonObject, report: JsonObject
) -> None:
    identifier = (
        (record.get("event_id") or record.get("id"))
        if kind == "events"
        else record["raw_event_id"]
    )
    digest = (
        hashlib.sha256(_json_bytes(record)).hexdigest()
        if kind == "events"
        else record["raw_payload_hash"]
    )
    old = index.execute(
        "SELECT digest FROM identities WHERE kind=? AND id=?", (kind, identifier)
    ).fetchone()
    if old and old[0] != digest:
        raise MaintenanceError("migration_event_id_conflict")
    if old:
        report["duplicate_rows"] += 1
        report["duplicate_" + kind] += 1
    else:
        index.execute(
            "INSERT INTO identities VALUES (?,?,?)", (kind, identifier, digest)
        )
        report["unique_" + kind] += 1
    native = record.get("native_identity_key") if kind == "raw" else None
    if native:
        old = index.execute(
            "SELECT digest FROM native WHERE id=?", (native,)
        ).fetchone()
        if old and old[0] != digest:
            raise MaintenanceError("migration_native_identity_conflict")
        index.execute("INSERT OR IGNORE INTO native VALUES (?,?)", (native, digest))


class JournalScanService:
    """Discover and scan journals using operation-local reports and indexes.

    Construction performs no I/O. The optional validator owns only raw identity
    validation; the default reuses the pure native ingress primitives. All mutable
    scan state belongs to an individual exhausted ``rows`` or ``preflight`` call.
    """

    def __init__(
        self,
        raw_validator: _RawValidator | None = None,
        *,
        driver: SQLiteDriver | None = None,
    ) -> None:
        """Keep a narrow raw identity validator without opening any resources."""
        self._driver = driver
        self._raw_validator = (
            _validate_native_record if raw_validator is None else raw_validator
        )

    def discover(
        self, project: Path, workplace: Path
    ) -> tuple[Path, list[JournalSource]]:
        """Return the existing flow root and sorted, deduplicated legacy sources.

        Use the established flow-root reader. Workplace-wide raw sources precede
        older project-local raw sources; filtering by project happens per record.
        Symlink/reparse sources and parent directories are refused.
        """
        from ..work.consistency import RunTaskInputReader

        _check_links(project, "migration_source_symlink")
        _check_links(workplace, "migration_source_symlink")
        project, workplace = project.resolve(), workplace.resolve()
        flow = RunTaskInputReader().require_flow_root(project)
        events = flow / "runtime/events/events.ndjson"
        raw = workplace / "runtime/agent-events/raw/v1"
        local = flow / "runtime/agent-events/raw/v1"
        for root in (events, raw, local):
            _check_links(root, "migration_source_symlink")
        sources: list[JournalSource] = [("events", events)] if events.is_file() else []
        sources.extend(("raw", path) for path in sorted(raw.rglob("*.ndjson")))
        known = {path.resolve() for _kind, path in sources}
        sources.extend(
            ("raw", path)
            for path in sorted(local.rglob("*.ndjson"))
            if path.resolve() not in known
        )
        for _kind, path in sources:
            _signature(path)
        return flow, sources

    def _record(
        self, kind: SourceKind, line: bytes, project: Path
    ) -> JsonObject | None:
        record = _decode(line)
        if kind == "events":
            identifier = record.get("event_id") or record.get("id")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("event_id_required")
        else:
            if not _same_project(record.get("source_project_ref"), project):
                return None
            try:
                self._raw_validator(record)
            except (ValueError, TypeError, KeyError) as exc:
                code = str(exc)
                raise ValueError(
                    code if code in _RAW_REASONS else "raw_identity_invalid"
                ) from None
        return record

    def rows(
        self,
        sources: list[JournalSource],
        project: Path,
        report: JsonObject,
        *,
        skip_invalid: bool = False,
        quarantine_dir: Path | None = None,
    ) -> Iterator[JournalRow]:
        """Yield validated rows and fill a report after full iterator exhaustion.

        ``read_rows`` counts physical lines, partitioned into ``valid_rows``,
        ``invalid_rows``, ``blank_rows`` and ``filtered_rows``. Valid counts include
        duplicates; ``skipped_rows`` counts invalid rows only with explicit skip.
        Without skip, corruption sets ``blocked`` while scanning continues to
        preserve all invalid evidence. Consumers must honor that flag. Identity
        conflicts, source drift and evidence failures always raise MaintenanceError.

        Existing ``report['sources']`` can pin a preceding pass. Scanner-owned
        fields are reset per call; unrelated report fields are retained. Source
        manifests include full hashes and must also be compared between passes
        when the caller uses separate reports. Closing an unfinished iterator
        releases its index but does not certify a completed scan. With explicit
        quarantine, an aborted pass preserves verified incomplete provenance.
        """
        project = project.resolve()
        sources = list(sources)
        expected = report.get("sources")
        report.update(_new_report())
        for kind, _path in sources:
            if kind not in ("events", "raw"):
                raise MaintenanceError("migration_source_kind_invalid")
        baseline = [_snapshot(path) for _kind, path in sources]
        if expected and expected != baseline:
            raise MaintenanceError("migration_source_changed")
        quarantine = (
            _Quarantine(quarantine_dir, project) if quarantine_dir is not None else None
        )
        if quarantine is not None:
            report["quarantine"] = {
                "status": "requested",
                "directory": str(quarantine.directory),
            }
        # Empty filename creates a disk-backed temporary SQLite index removed
        # on close. Neither identities nor native keys grow an in-memory set.
        try:
            with closing(
                (
                    self._driver
                    if self._driver is not None
                    else DatabaseFactory.resolve_driver()
                )._connect("")
            ) as index:
                index.execute("PRAGMA cache_size=-2048")
                index.execute(
                    "CREATE TABLE identities(kind TEXT, id TEXT, digest TEXT, "
                    "PRIMARY KEY(kind,id))"
                )
                index.execute("CREATE TABLE native(id TEXT PRIMARY KEY, digest TEXT)")
                for (kind, path), snapshot in zip(sources, baseline, strict=True):
                    yield from self._source_rows(
                        kind,
                        path,
                        project,
                        snapshot,
                        index,
                        report,
                        skip_invalid,
                        quarantine,
                    )
                    report["sources"].append(snapshot)
                # Recheck earlier files after later sources, including full hashes.
                if [_snapshot(path) for _kind, path in sources] != baseline:
                    raise MaintenanceError("migration_source_changed")
        except BaseException as error:
            if quarantine is not None:
                failure = (
                    error.code
                    if isinstance(error, MaintenanceError)
                    else "scan_interrupted"
                )
                report["quarantine"] = quarantine.finish(
                    baseline, complete=False, failure=failure
                )
            raise
        if quarantine is not None:
            report["quarantine"] = quarantine.finish(report["sources"])

    def _source_rows(
        self,
        kind: SourceKind,
        path: Path,
        project: Path,
        snapshot: JsonObject,
        index: sqlite3.Connection,
        report: JsonObject,
        skip_invalid: bool,
        quarantine: _Quarantine | None,
    ) -> Iterator[JournalRow]:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as source:
                if (
                    list(_stat_signature(os.fstat(source.fileno()))[:4])
                    != snapshot["signature"][:4]
                ):
                    raise MaintenanceError("migration_source_changed")
                offset = 0
                for line_number, line in enumerate(source, 1):
                    digest.update(line)
                    start = offset
                    offset += len(line)
                    report["read_rows"] += 1
                    if not line.strip():
                        report["blank_rows"] += 1
                        continue
                    try:
                        record = self._record(kind, line, project)
                    except (ValueError, TypeError, KeyError, RecursionError) as exc:
                        code = str(exc)
                        reason = code if code in _RECORD_REASONS else "record_invalid"
                        metadata = {
                            "source": str(path),
                            "kind": kind,
                            "line": line_number,
                            "offset": start,
                            "length": len(line),
                            "sha256": hashlib.sha256(line).hexdigest(),
                            "code": reason,
                        }
                        report["invalid"] += 1
                        report["invalid_rows"] += 1
                        if skip_invalid:
                            report["skipped_rows"] += 1
                        else:
                            report["blocked"] = True
                        if len(report["diagnostics"]) < _DIAGNOSTIC_LIMIT:
                            report["diagnostics"].append(metadata)
                        if quarantine is not None:
                            quarantine.add(metadata, line)
                        continue
                    if record is None:
                        report["other_project_raw"] += 1
                        report["filtered_rows"] += 1
                        continue
                    _identity(index, kind, record, report)
                    report[kind + "_rows"] += 1
                    report["valid_rows"] += 1
                    yield kind, record, f"{path}:{start}"
                if (
                    list(_stat_signature(os.fstat(source.fileno()))[:4])
                    != snapshot["signature"][:4]
                ):
                    raise MaintenanceError("migration_source_changed")
        except OSError:
            raise MaintenanceError("migration_source_unavailable") from None
        if (
            list(_signature(path)) != snapshot["signature"]
            or digest.hexdigest() != snapshot["sha256"]
        ):
            raise MaintenanceError("migration_source_changed")

    def preflight(
        self,
        project: Path,
        workplace: Path,
        *,
        skip_invalid: bool = False,
        evidence_dir: Path | None = None,
    ) -> JsonObject:
        """Exhaust a scan, check discovery stability and return its observations.

        No database destination or journal source is modified. Explicit evidence
        requests create or verify quarantine files even when corruption blocks
        import. ``status`` is ``blocked`` or ``planned``; it never claims import.
        """
        project, workplace = Path(project), Path(workplace)
        _flow, sources = self.discover(project, workplace)
        report = _new_report()
        for _row in self.rows(
            sources,
            project,
            report,
            skip_invalid=skip_invalid,
            quarantine_dir=evidence_dir,
        ):
            pass
        if self.discover(project, workplace)[1] != sources:
            raise MaintenanceError("migration_source_changed")
        report.update(
            status="blocked" if report["blocked"] else "planned", applied=False
        )
        return report
