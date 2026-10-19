#!/usr/bin/env python3
"""Temporary, explicit NDJSON -> project SQLite migration. Originals stay intact."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import processforge as core
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.sqlite_storage import JournalError, set_metadata, transaction
from pf_runtime.raw_ingress_kernel import (
    NativeAgentEvent, raw_event_id, raw_payload_hash, stable_native_identity_key,
)


def _signature(path: Path):
    if path.is_symlink():
        raise JournalError("migration_source_symlink")
    value = path.stat()
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _sources(project: Path, workplace: Path):
    from processforge_core.work.consistency import RunTaskInputReader

    flow = RunTaskInputReader().require_flow_root(project)
    events = flow / "runtime/events/events.ndjson"
    raw_root = workplace / "runtime/agent-events"
    sources = [("events", events)] if events.is_file() else []
    sources.extend(("raw", path) for path in sorted((raw_root / "raw/v1").rglob("*.ndjson")))
    # Also support an older project-local raw layout, without importing it twice.
    local = flow / "runtime/agent-events/raw/v1"
    known = {path.resolve() for _kind, path in sources}
    sources.extend(("raw", path) for path in sorted(local.rglob("*.ndjson")) if path.resolve() not in known)
    return flow, sources


def _same_project(value, project: Path) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return Path(value).expanduser().resolve() == project


def _validate_raw(record):
    if record.get("schema_version") != 1 or not isinstance(record.get("raw_payload"), dict):
        raise ValueError("raw_schema_invalid")
    if record.get("raw_payload_hash") != raw_payload_hash(record["raw_payload"]):
        raise ValueError("raw_payload_hash_mismatch")
    # Legacy v1 did not store these two identity controls. Validate its existing
    # IDs against the finite set of supported controls, never invent new IDs.
    scopes = [record["native_id_scope"]] if "native_id_scope" in record else ("provider", "adapter", "session", "project")
    stable_values = [record["native_event_id_stable"]] if "native_event_id_stable" in record else (True, False)
    for scope in scopes:
        for stable in stable_values:
            event = NativeAgentEvent(**{key: record.get(key) for key in (
                "provider", "adapter", "native_event_type", "raw_payload", "payload_version",
                "native_event_id", "source_session_id", "source_project_ref")},
                native_id_scope=scope, native_event_id_stable=stable)
            if raw_event_id(event) == record.get("raw_event_id") and stable_native_identity_key(event) == record.get("native_identity_key"):
                if not isinstance(record.get("received_at"), str):
                    raise ValueError("raw_received_at_required")
                return
    raise ValueError("raw_identity_mismatch")


def _rows(sources, project, report, *, skip_invalid):
    """Stream with byte offsets; malformed data is never silently discarded."""
    for kind, path in sources:
        digest = hashlib.sha256()
        before = _signature(path)
        with path.open("rb") as source:
            offset = 0
            for line_number, line in enumerate(source, 1):
                digest.update(line)
                location = f"{path}:{offset}"
                offset += len(line)
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("record_not_object")
                    if kind == "events":
                        if not isinstance(record.get("event_id") or record.get("id"), str) or not (record.get("event_id") or record.get("id")):
                            raise ValueError("event_id_required")
                        # Reject NaN/Infinity, including values accepted by json.loads.
                        json.dumps(record, allow_nan=False)
                    else:
                        if not _same_project(record.get("source_project_ref"), project):
                            report["other_project_raw"] += 1
                            continue
                        _validate_raw(record)
                except (ValueError, TypeError, KeyError) as exc:
                    report["invalid"] += 1
                    if len(report["diagnostics"]) < 100:
                        report["diagnostics"].append({"source": str(path), "line": line_number, "code": str(exc)})
                    if not skip_invalid:
                        report["blocked"] = True
                    continue
                report[kind + "_rows"] += 1
                yield kind, record, location
        if before != _signature(path):
            raise JournalError("migration_source_changed")
        report["sources"].append({"path": str(path), "signature": before, "sha256": digest.hexdigest()})


def _report():
    return {"events_rows": 0, "raw_rows": 0, "other_project_raw": 0, "invalid": 0,
            "blocked": False, "diagnostics": [], "sources": []}


def _preflight(sources, project, *, skip_invalid):
    report = _report()
    # Empty filename is an automatically removed temporary SQLite database,
    # so duplicate detection stays bounded even for very large source files.
    with closing(sqlite3.connect("")) as index:
        index.execute("CREATE TABLE identities(kind TEXT, id TEXT, digest TEXT, PRIMARY KEY(kind,id))")
        index.execute("CREATE TABLE native(id TEXT PRIMARY KEY, digest TEXT)")
        for kind, record, _location in _rows(sources, project, report, skip_invalid=skip_invalid):
            identifier = (record.get("event_id") or record.get("id")) if kind == "events" else record["raw_event_id"]
            digest = (hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()
                      if kind == "events" else record["raw_payload_hash"])
            old = index.execute("SELECT digest FROM identities WHERE kind=? AND id=?", (kind, identifier)).fetchone()
            if old and old[0] != digest:
                raise JournalError("migration_event_id_conflict")
            index.execute("INSERT OR IGNORE INTO identities VALUES (?,?,?)", (kind, identifier, digest))
            native = record.get("native_identity_key") if kind == "raw" else None
            if native:
                old = index.execute("SELECT digest FROM native WHERE id=?", (native,)).fetchone()
                if old and old[0] != digest:
                    raise JournalError("migration_native_identity_conflict")
                index.execute("INSERT OR IGNORE INTO native VALUES (?,?)", (native, digest))
        report["unique_events"] = index.execute("SELECT COUNT(*) FROM identities WHERE kind='events'").fetchone()[0]
        report["unique_raw"] = index.execute("SELECT COUNT(*) FROM identities WHERE kind='raw'").fetchone()[0]
    return report


def migrate(project_root: Path, workplace: Path, *, apply=False, skip_invalid=False):
    project, workplace = Path(project_root).resolve(), Path(workplace).resolve()
    flow, sources = _sources(project, workplace)
    report = _preflight(sources, project, skip_invalid=skip_invalid)
    report.update(applied=False, status="blocked" if report["blocked"] else "planned")
    if not apply or report["blocked"]:
        return report
    events, raw = ProcessEventJournal(), RawHookJournal()
    event_path, raw_path = flow / "runtime/events/events.sqlite3", flow / "runtime/agent-events/hooks.sqlite3"
    # Commit a barrier in BOTH owners before any import. Failed imports remain
    # inaccessible to normal readers/writers and may be resumed explicitly.
    for owner, path in ((events, event_path), (raw, raw_path)):
        with owner.connection(path, writable=True, migrating=True) as connection:
            with transaction(connection):
                set_metadata(connection, "migration_state", "importing")
    imported = _report()
    batch = []

    def flush():
        for kind, owner, path in (("events", events, event_path), ("raw", raw, raw_path)):
            items = [(record, location) for item_kind, record, location in batch if item_kind == kind]
            if not items:
                continue
            with owner.connection(path, writable=True, migrating=True) as connection:
                with transaction(connection):
                    for record, location in items:
                        if kind == "events":
                            owner._append(connection, record, lambda item: item.get("event_id") or item["id"], True, True)
                        else:
                            result = owner._accept(connection, path, record, retain_raw=True, legacy_location=location)
                            if not result["accepted"]:
                                raise JournalError("migration_existing_raw_conflict")
        batch.clear()

    for row in _rows(sources, project, imported, skip_invalid=skip_invalid):
        batch.append(row)
        if len(batch) >= 500:
            flush()
    flush()
    if imported["sources"] != report["sources"] or imported["invalid"] != report["invalid"] or _sources(project, workplace)[1] != sources:
        raise JournalError("migration_source_changed")
    if any(tuple(item["signature"]) != _signature(Path(item["path"])) for item in imported["sources"]):
        raise JournalError("migration_source_changed")
    counts = {}
    for kind, owner, path, table in (("events", events, event_path, "events"), ("raw", raw, raw_path, "raw_events")):
        with owner.connection(path, writable=True, migrating=True) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise JournalError("migration_integrity_failed")
            counts[kind] = connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            if counts[kind] < report["unique_" + kind]:
                raise JournalError("migration_count_mismatch")
            with transaction(connection):
                set_metadata(connection, "legacy_source_manifest", json.dumps(report["sources"], sort_keys=True))
    events.finish_migration(event_path)
    raw.finish_migration(raw_path)
    report.update(applied=True, status="ready", stored_counts=counts)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workplace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-invalid", action="store_true", help="explicitly accept reported invalid legacy rows")
    args = parser.parse_args()
    try:
        report = migrate(args.project_root, args.workplace, apply=args.apply, skip_invalid=args.skip_invalid)
    except (JournalError, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
