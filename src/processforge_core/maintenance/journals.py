"""Order explicit legacy journal imports, backups and recovery evidence.

JournalMaintenanceService composes the existing journal owners with narrow
backup and scanner ports. It performs no transport or task lifecycle work.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from processforge_core.maintenance.contracts import (
    BackupPort,
    JournalRow,
    JournalScanPort,
    JournalSource,
    JsonObject,
    MaintenanceError,
)
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import (
    JournalError,
    metadata,
    set_metadata,
    transaction,
)


def _scan_report() -> JsonObject:
    return {
        "events_rows": 0,
        "raw_rows": 0,
        "other_project_raw": 0,
        "invalid": 0,
        "blocked": False,
        "diagnostics": [],
        "sources": [],
        "read_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "skipped_rows": 0,
        "duplicate_rows": 0,
    }


def _safe_path(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise MaintenanceError("migration_unsafe_path")


def _signature(path: Path) -> tuple[int, int, int, int, int]:
    _safe_path(path)
    value = path.stat()
    if not path.is_file():
        raise MaintenanceError("migration_source_not_file")
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _database_identity(path: Path) -> tuple[int, int] | None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        _safe_path(path.with_name(path.name + suffix))
    try:
        value = path.stat()
    except FileNotFoundError:
        return None
    if not path.is_file():
        raise MaintenanceError("migration_destination_not_file")
    return value.st_dev, value.st_ino


def _encoded(record: JsonObject) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _evidence(directory: Path | None, name: str, report: JsonObject) -> None:
    if directory is None:
        return
    path = directory / (name + ".json")
    _safe_path(path)
    content = (
        json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    # Each phase is exclusive and durable; interrupted writes cannot replace
    # earlier recovery facts or claim to be a completed report.
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    report["evidence"].append(
        {"path": str(path), "sha256": hashlib.sha256(content).hexdigest()}
    )


def _failure_code(error: BaseException) -> str:
    if isinstance(error, MaintenanceError):
        return error.code
    if isinstance(error, JournalError):
        return str(error).split(":", 1)[0]
    if isinstance(error, OSError):
        return "migration_io_failed"
    if isinstance(error, sqlite3.Error):
        return "migration_database_error"
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        return "migration_interrupted"
    return "migration_failed"


class JournalMaintenanceService:
    """Migrate journals with explicit backups, validation and durable barriers."""

    def __init__(
        self,
        backup: BackupPort | None = None,
        scan: JournalScanPort | None = None,
    ) -> None:
        """Bind operation ports without reading files or opening databases.

        Args:
            backup: Verified SQLite backup owner; defaults to SQLiteBackupService.
            scan: Legacy scan/quarantine owner; defaults to JournalScanService.
        """
        if backup is None:
            from processforge_core.maintenance.backup import SQLiteBackupService

            backup = SQLiteBackupService()
        if scan is None:
            from processforge_core.maintenance.journal_scan import JournalScanService

            scan = JournalScanService()
        self._backup = backup
        self._scan = scan

    def migrate(
        self,
        project_root: Path,
        workplace: Path,
        *,
        apply: bool = False,
        skip_invalid: bool = False,
        evidence_dir: Path | None = None,
    ) -> JsonObject:
        """Plan or explicitly apply an import without changing legacy sources.

        Args:
            project_root: Explicit project containing the existing PF manifest.
            workplace: Explicit root containing shared legacy raw journals.
            apply: Permit database mutations after successful preflight/backups.
            skip_invalid: Explicitly permit skipping quarantined invalid rows.
            evidence_dir: Optional evidence base. Applying creates an exclusive
                operation directory; planning writes only requested scan evidence.

        Returns:
            A JSON report with counts, backups, verification and private evidence
            paths. Invalid input returns blocked unless skipping was explicit.

        Raises:
            MaintenanceError: A safety or verification requirement failed.
            JournalError: An existing journal owner refused an operation.
            OSError: Required I/O or recovery evidence could not be committed.

        An interrupted import retains data and importing barriers for an explicit
        retry. Backups are independent database snapshots, not a global snapshot.
        """
        project, workplace = Path(project_root).absolute(), Path(workplace).absolute()
        _safe_path(project)
        _safe_path(workplace)
        project, workplace = project.resolve(), workplace.resolve()
        flow, sources = self._scan.discover(project, workplace)
        _safe_path(flow)
        event_path = flow / "runtime/events/events.sqlite3"
        raw_path = flow / "runtime/agent-events/hooks.sqlite3"
        for path in (event_path, raw_path):
            _database_identity(path)
        operation: Path | None = None
        if apply:
            base = (
                Path(evidence_dir).absolute()
                if evidence_dir is not None
                else flow / "runtime/journal-maintenance"
            )
            _safe_path(base)
            operation = base / ("operation-" + uuid4().hex)
            operation.mkdir(parents=True, exist_ok=False)
        report: JsonObject = {
            **_scan_report(),
            "applied": False,
            "status": "planned",
            "migration_state": "not_started",
            "backups": [],
            "evidence": [],
            "evidence_dir": str(operation) if operation else None,
            "backup_consistency": "per_database",
            "imported_counts": {"events": 0, "raw": 0},
            "already_present_counts": {"events": 0, "raw": 0},
        }
        barriers: list[
            tuple[ProcessEventJournal | RawHookJournal, Path, tuple[int, int] | None]
        ] = []
        events, raw = ProcessEventJournal(), RawHookJournal()
        scan_evidence = operation / "quarantine" if operation else evidence_dir
        preflight_complete = False
        try:
            report.update(
                self._scan.preflight(
                    project,
                    workplace,
                    skip_invalid=skip_invalid,
                    evidence_dir=scan_evidence,
                )
            )
            preflight_complete = True
            report["evidence_dir"] = str(operation) if operation else None
            report["status"] = "blocked" if report["blocked"] else "planned"
            self._counts(report, skip_invalid)
            self._unchanged(project, workplace, flow, sources, report)
            _evidence(operation, "preflight", report)
            if not apply or report["blocked"]:
                _evidence(operation, "result", report)
                return report

            destinations = self._backups(event_path, raw_path, operation, report)
            _evidence(operation, "backups", report)
            # Backup waits may have allowed a legacy writer to change a source.
            self._unchanged(project, workplace, flow, sources, report)
            self._same_destinations(destinations)
            for owner, path in ((events, event_path), (raw, raw_path)):
                if _database_identity(path) != destinations[path]:
                    raise MaintenanceError("migration_destination_changed")
                # Initialization may commit a barrier before context exit fails.
                barriers.append((owner, path, destinations[path]))
                with owner.connection(
                    path, writable=True, migrating=True
                ) as connection:
                    destinations[path] = _database_identity(path)
                    barriers[-1] = (owner, path, destinations[path])
                    with transaction(connection):
                        set_metadata(connection, "migration_state", "importing")
            report["migration_state"] = "importing"
            before = self._statistics(events, raw, event_path, raw_path)
            report["before_counts"] = before
            _evidence(operation, "importing", report)

            imported = _scan_report()
            batch: list[JournalRow] = []
            for row in self._scan.rows(
                sources,
                project,
                imported,
                skip_invalid=skip_invalid,
                quarantine_dir=scan_evidence,
            ):
                batch.append(row)
                if len(batch) >= 500:
                    self._flush(batch, events, raw, event_path, raw_path, report)
            self._flush(batch, events, raw, event_path, raw_path, report)
            self._same_scan(report, imported)
            self._same_destinations(destinations)
            self._unchanged(project, workplace, flow, sources, report)

            replay = _scan_report()
            with events.connection(event_path, migrating=True) as event_connection:
                with raw.connection(raw_path, migrating=True) as raw_connection:
                    for kind, record, _location in self._scan.rows(
                        sources,
                        project,
                        replay,
                        skip_invalid=skip_invalid,
                        quarantine_dir=scan_evidence,
                    ):
                        if kind == "events":
                            self._verify_event(event_connection, record)
                        else:
                            self._verify_raw(raw_connection, record)
            self._same_scan(report, replay)
            self._same_destinations(destinations)
            after = self._statistics(events, raw, event_path, raw_path)
            for kind in ("events", "raw"):
                if (
                    after[kind] != before[kind] + report["imported_counts"][kind]
                    or after[kind] < report["unique_" + kind]
                ):
                    raise MaintenanceError("migration_count_mismatch")
            self._unchanged(project, workplace, flow, sources, report)
            for owner, path in ((events, event_path), (raw, raw_path)):
                with owner.connection(
                    path, writable=True, migrating=True
                ) as connection:
                    with transaction(connection):
                        set_metadata(
                            connection,
                            "legacy_source_manifest",
                            json.dumps(report["sources"], sort_keys=True),
                        )
            report["stored_counts"] = after
            report["verification"] = {
                "integrity": {"events": "ok", "raw": "ok"},
                "source_hashes": "verified",
                "valid_id_counts": {
                    "events": report["unique_events"],
                    "raw": report["unique_raw"],
                },
                "semantic_replay": {
                    "status": "verified",
                    "checked_rows": replay["events_rows"] + replay["raw_rows"],
                    "inserted": 0,
                },
            }
            self._counts(report, skip_invalid)
            _evidence(operation, "verified", report)
            events.finish_migration(event_path)
            raw.finish_migration(raw_path)
            for owner, path in ((events, event_path), (raw, raw_path)):
                with owner.connection(path) as connection:
                    if (
                        metadata(connection, "migration_state") != "ready"
                        or metadata(connection, "legacy_imported") != "1"
                    ):
                        raise MaintenanceError("migration_state_mismatch")
            self._unchanged(project, workplace, flow, sources, report)
            self._same_destinations(destinations)
            report.update(applied=True, status="ready", migration_state="ready")
            _evidence(operation, "result", report)
            return report
        except BaseException as error:
            if scan_evidence is not None and not preflight_complete:
                report["quarantine"] = {
                    "status": "incomplete",
                    "directory": str(scan_evidence),
                    "scan_complete": False,
                }
                report["scan_complete"] = False
            # Cross-database completion is not atomic. Reassert both barriers if
            # a later finish/evidence write fails; never restore or delete data.
            states: JsonObject = {}
            for owner, path, identity in barriers:
                try:
                    current = _database_identity(path)
                    if current is None:
                        states[path.name] = "missing"
                        continue
                    if identity is None or current != identity:
                        raise MaintenanceError("migration_destination_changed")
                    with owner.connection(
                        path, writable=True, migrating=True
                    ) as connection:
                        with transaction(connection):
                            set_metadata(connection, "migration_state", "importing")
                    states[path.name] = "importing"
                except (
                    MaintenanceError,
                    JournalError,
                    OSError,
                    sqlite3.Error,
                ) as barrier_error:
                    states[path.name] = {
                        "status": "unavailable",
                        "error": _failure_code(barrier_error),
                    }
            report.update(
                applied=False,
                status="failed",
                error=_failure_code(error),
                migration_state="incomplete" if barriers else "not_started",
                recovery={
                    "destination_states": states,
                    "source_mutation_by_service": False,
                    "source_integrity": "unverified_after_failure",
                    "automatic_restore": False,
                    "retry": "explicit_import",
                },
            )
            self._counts(report, skip_invalid)
            _evidence(operation, "failure", report)
            raise

    def _backups(
        self,
        event_path: Path,
        raw_path: Path,
        operation: Path | None,
        report: JsonObject,
    ) -> dict[Path, tuple[int, int] | None]:
        if operation is None:
            raise MaintenanceError("migration_evidence_required")
        (operation / "backups").mkdir()
        identities = {}
        for kind, path in (("events", event_path), ("raw", raw_path)):
            identities[path] = _database_identity(path)
            if identities[path] is None:
                report["backups"].append(
                    {"kind": kind, "status": "missing", "database": str(path)}
                )
                continue
            bundle = operation / "backups" / kind
            receipt: JsonObject = {
                "kind": kind,
                "status": "not_verified",
                "database": str(path),
                "bundle": str(bundle),
            }
            report["backups"].append(receipt)
            created = self._backup.create(path, bundle)
            receipt.update(status="created", created=created)
            verified = self._backup.verify(bundle)
            receipt["verification"] = verified
            if (
                created.get("status") not in ("ok", "ready", "verified")
                or verified.get("status") not in ("ok", "ready", "verified")
                or verified.get("integrity_check") != "ok"
                or verified.get("verified") is False
            ):
                raise MaintenanceError("migration_backup_unverified")
            receipt["status"] = "verified"
        return identities

    @staticmethod
    def _same_destinations(identities: dict[Path, tuple[int, int] | None]) -> None:
        if any(
            _database_identity(path) != identity
            for path, identity in identities.items()
        ):
            raise MaintenanceError("migration_destination_changed")

    def _unchanged(
        self,
        project: Path,
        workplace: Path,
        flow: Path,
        sources: list[JournalSource],
        report: JsonObject,
    ) -> None:
        actual_flow, actual_sources = self._scan.discover(project, workplace)
        if actual_flow != flow or actual_sources != sources:
            raise MaintenanceError("migration_source_changed")
        observations = report["sources"]
        if [item["path"] for item in observations] != [
            str(path) for _kind, path in sources
        ]:
            raise MaintenanceError("migration_source_changed")
        try:
            for item, (_kind, path) in zip(observations, sources, strict=True):
                before = _signature(path)
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if (
                    before != _signature(path)
                    or before != tuple(item["signature"])
                    or digest != item["sha256"]
                ):
                    raise MaintenanceError("migration_source_changed")
        except FileNotFoundError as error:
            raise MaintenanceError("migration_source_changed") from error

    @staticmethod
    def _same_scan(expected: JsonObject, actual: JsonObject) -> None:
        if (
            any(
                expected[key] != actual[key]
                for key in (
                    "sources",
                    "invalid",
                    "events_rows",
                    "raw_rows",
                    "other_project_raw",
                )
            )
            or actual["blocked"]
        ):
            raise MaintenanceError("migration_source_changed")

    @staticmethod
    def _counts(report: JsonObject, skip_invalid: bool) -> None:
        valid = report["events_rows"] + report["raw_rows"]
        report["counts"] = {
            "read": report.get(
                "read_rows", valid + report["invalid"] + report["other_project_raw"]
            ),
            "valid": valid,
            "imported": sum(report["imported_counts"].values()),
            "already_present": sum(report["already_present_counts"].values()),
            "skipped": (report["invalid"] if skip_invalid else 0)
            + report["other_project_raw"],
            "corrupted": report["invalid"],
        }

    @staticmethod
    def _flush(
        batch: list[JournalRow],
        events: ProcessEventJournal,
        raw: RawHookJournal,
        event_path: Path,
        raw_path: Path,
        report: JsonObject,
    ) -> None:
        for kind, owner, path in (
            ("events", events, event_path),
            ("raw", raw, raw_path),
        ):
            items = [
                (record, location)
                for item_kind, record, location in batch
                if item_kind == kind
            ]
            if not items:
                continue
            inserted = 0
            with owner.connection(path, writable=True, migrating=True) as connection:
                with transaction(connection):
                    for record, location in items:
                        if kind == "events":
                            inserted += events._append(
                                connection,
                                record,
                                lambda item: item.get("event_id") or item["id"],
                                True,
                                True,
                            )
                        else:
                            exists = connection.execute(
                                "SELECT 1 FROM raw_events WHERE raw_event_id = ?",
                                (record["raw_event_id"],),
                            ).fetchone()
                            # The existing journal owner has an untyped batch admission.
                            result = raw._accept(  # type: ignore[no-untyped-call]
                                connection,
                                path,
                                record,
                                retain_raw=True,
                                legacy_location=location,
                            )
                            if not result["accepted"]:
                                raise JournalError("migration_existing_raw_conflict")
                            inserted += exists is None
            report["imported_counts"][kind] += inserted
            report["already_present_counts"][kind] += len(items) - inserted
        batch.clear()

    @staticmethod
    def _verify_event(connection: sqlite3.Connection, record: JsonObject) -> None:
        identifier = record.get("event_id") or record["id"]
        row = connection.execute(
            "SELECT a.payload_hash, e.record FROM admissions a "
            "JOIN events e ON e.seq = a.seq AND e.event_id = a.event_id "
            "WHERE a.event_id = ?",
            (identifier,),
        ).fetchone()
        encoded = _encoded(record)
        if (
            row is None
            or row["payload_hash"]
            != hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            or _encoded(json.loads(row["record"])) != encoded
        ):
            raise MaintenanceError("migration_record_mismatch")

    @staticmethod
    def _verify_raw(connection: sqlite3.Connection, record: JsonObject) -> None:
        from pf_runtime.raw_ingress_kernel import raw_payload_hash

        row = connection.execute(
            "SELECT r.raw_payload_hash, h.record FROM receipts r "
            "JOIN raw_events h ON h.raw_event_id = r.raw_event_id "
            "WHERE r.raw_event_id = ?",
            (record["raw_event_id"],),
        ).fetchone()
        if row is None or row["raw_payload_hash"] != record["raw_payload_hash"]:
            raise MaintenanceError("migration_record_mismatch")
        stored = json.loads(row["record"])
        # Dedup is based on ID/payload, not received_at or other observation data.
        if (
            not isinstance(stored, dict)
            or stored.get("raw_event_id") != record["raw_event_id"]
            or stored.get("raw_payload_hash") != record["raw_payload_hash"]
            or not isinstance(stored.get("raw_payload"), dict)
            or raw_payload_hash(stored["raw_payload"]) != record["raw_payload_hash"]
        ):
            raise MaintenanceError("migration_record_mismatch")

    @staticmethod
    def _statistics(
        events: ProcessEventJournal,
        raw: RawHookJournal,
        event_path: Path,
        raw_path: Path,
    ) -> dict[str, int]:
        counts = {}
        for kind, owner, path, query in (
            (
                "events",
                events,
                event_path,
                "SELECT COUNT(*), COUNT(DISTINCT event_id) FROM events",
            ),
            (
                "raw",
                raw,
                raw_path,
                "SELECT COUNT(*), COUNT(DISTINCT raw_event_id) FROM raw_events",
            ),
        ):
            with owner.connection(path, migrating=True) as connection:
                integrity = [
                    row[0] for row in connection.execute("PRAGMA integrity_check")
                ]
                if integrity != ["ok"]:
                    raise MaintenanceError("migration_integrity_failed")
                count, unique = connection.execute(query).fetchone()
                if (
                    count != unique
                    or int(metadata(connection, "history_count") or 0) != count
                ):
                    raise MaintenanceError("migration_count_mismatch")
                if metadata(connection, "migration_state") != "importing":
                    raise MaintenanceError("migration_state_mismatch")
                counts[kind] = count
        return counts
