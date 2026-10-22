"""Scan legacy journals, verify identities and preserve exact corrupt bytes."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

from .contracts import (
    JournalRow,
    JournalSource,
    JsonObject,
    MaintenanceError,
    SourceKind,
)

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

    def __init__(self, raw_validator: _RawValidator | None = None) -> None:
        """Keep a narrow raw identity validator without opening any resources."""
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
            with closing(sqlite3.connect("")) as index:
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
