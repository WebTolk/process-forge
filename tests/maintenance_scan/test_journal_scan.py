"""Behavior and failure checks for the Core legacy journal scanner."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from processforge_core.maintenance import journal_scan
from processforge_core.maintenance.contracts import (
    JournalRow,
    JournalSource,
    JsonObject,
    MaintenanceError,
)
from processforge_core.maintenance.journal_scan import JournalScanService


def _line(record: JsonObject) -> bytes:
    encoded = json.dumps(record, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return encoded + b"\n"


def _event(identifier: str = "event-1", **values: Any) -> JsonObject:
    return {"event_id": identifier, **values}


def _source(tmp_path: Path, data: bytes, name: str = "events.ndjson") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _scan(
    path: Path,
    *,
    kind: str = "events",
    project: Path | None = None,
    skip_invalid: bool = False,
    evidence: Path | None = None,
) -> tuple[list[JournalRow], JsonObject]:
    report: JsonObject = {}
    sources: list[JournalSource] = [("events" if kind == "events" else "raw", path)]
    rows = list(
        JournalScanService().rows(
            sources,
            project or path.parent,
            report,
            skip_invalid=skip_invalid,
            quarantine_dir=evidence,
        )
    )
    return rows, report


def _assert_incomplete(report: JsonObject, damage: bytes) -> JsonObject:
    receipt = report["quarantine"]
    assert receipt["status"] == "incomplete"
    assert receipt["scan_complete"] is False and receipt["records_verified"] is True
    path = Path(receipt["manifest"])
    assert path.name.startswith("manifest.incomplete-")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["sha256"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["scan_complete"] is False
    assert len(manifest["records"]) == 1
    record = manifest["records"][0]
    assert record["line"] == 1 and record["offset"] == 0
    assert record["length"] == len(damage)
    assert record["sha256"] == hashlib.sha256(damage).hexdigest()
    assert record["code"] == "json_invalid"
    assert (path.parent / record["file"]).read_bytes() == damage
    return manifest


@pytest.mark.parametrize("skip_invalid", [False, True])
def test_corruption_then_identity_conflict_retains_incomplete_provenance(
    tmp_path: Path, skip_invalid: bool
) -> None:
    damage = b"{broken\x00\r\n"
    source = _source(
        tmp_path,
        damage + _line(_event("same", value=1)) + _line(_event("same", value=2)),
    )
    original = source.read_bytes()
    report: JsonObject = {}
    with pytest.raises(MaintenanceError, match="migration_event_id_conflict"):
        list(
            JournalScanService().rows(
                [("events", source)],
                tmp_path,
                report,
                skip_invalid=skip_invalid,
                quarantine_dir=tmp_path / "evidence",
            )
        )
    manifest = _assert_incomplete(report, damage)
    assert manifest["scan_failure"] == "migration_event_id_conflict"
    assert Path(manifest["sources"][0]["path"]) == source
    assert source.read_bytes() == original


@pytest.mark.parametrize("complete_before", [False, True])
def test_corruption_then_source_drift_retains_incomplete_provenance(
    tmp_path: Path, complete_before: bool
) -> None:
    damage = b"{broken\x00\r\n"
    source = _source(tmp_path, damage + _line(_event("first")))
    evidence = tmp_path / "evidence"
    complete: bytes | None = None
    if complete_before:
        _scan(source, skip_invalid=True, evidence=evidence)
        complete = (evidence / "manifest.json").read_bytes()
    report: JsonObject = {}
    iterator = JournalScanService().rows(
        [("events", source)],
        tmp_path,
        report,
        skip_invalid=True,
        quarantine_dir=evidence,
    )
    assert next(iterator)[1]["event_id"] == "first"
    source.write_bytes(source.read_bytes() + _line(_event("late")))
    with pytest.raises(MaintenanceError, match="migration_source_changed"):
        list(iterator)
    manifest = _assert_incomplete(report, damage)
    assert manifest["scan_failure"] == "migration_source_changed"
    if complete is not None:
        assert (evidence / "manifest.json").read_bytes() == complete


def test_closing_after_captured_corruption_retains_incomplete_provenance(
    tmp_path: Path,
) -> None:
    damage = b"{broken\n"
    source = _source(tmp_path, damage + _line(_event("first")))
    report: JsonObject = {}
    iterator = JournalScanService().rows(
        [("events", source)],
        tmp_path,
        report,
        skip_invalid=True,
        quarantine_dir=tmp_path / "evidence",
    )
    next(iterator)
    iterator.close()
    assert _assert_incomplete(report, damage)["scan_failure"] == "scan_interrupted"


def _raw(
    project: Path,
    *,
    native_id: str = "native-1",
    value: int = 1,
    scope: str = "provider",
    stable: bool = True,
) -> JsonObject:
    from pf_runtime.raw_ingress_kernel import (
        NativeAgentEvent,
        raw_event_id,
        raw_payload_hash,
        stable_native_identity_key,
    )

    event = NativeAgentEvent(
        provider="codex",
        adapter="native",
        native_event_type="message",
        raw_payload={"value": value},
        native_event_id=native_id,
        native_id_scope=scope,
        native_event_id_stable=stable,
        source_session_id="session-1",
        source_project_ref=str(project.resolve()),
    )
    return {
        "schema_version": 1,
        "provider": event.provider,
        "adapter": event.adapter,
        "native_event_type": event.native_event_type,
        "raw_payload": event.raw_payload,
        "payload_version": event.payload_version,
        "native_event_id": event.native_event_id,
        "native_id_scope": event.native_id_scope,
        "native_event_id_stable": event.native_event_id_stable,
        "source_session_id": event.source_session_id,
        "source_project_ref": event.source_project_ref,
        "raw_payload_hash": raw_payload_hash(event.raw_payload),
        "raw_event_id": raw_event_id(event),
        "native_identity_key": stable_native_identity_key(event),
        "received_at": "2026-10-22T12:00:00Z",
    }


def _layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    project, workplace = tmp_path / "project", tmp_path / "workplace"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    workplace.mkdir()
    (flow / "process-forge.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return project, workplace, flow


def _manifest(report: JsonObject) -> JsonObject:
    path = Path(report["quarantine"]["manifest"])
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == report["quarantine"]["sha256"]
    return json.loads(data)


def test_exact_corrupt_bytes_offsets_and_explicit_skip(tmp_path: Path) -> None:
    first = _line(_event(message="Привет"))
    blank = b" \t\r\n"
    corrupt = b'\x00\x00{"secret":"do-not-report"}\r\n'
    last = b'\xff{"unfinished":'
    original = first + blank + corrupt + last
    path = _source(tmp_path, original)
    signature = path.stat()
    evidence = tmp_path / "evidence"

    rows, report = _scan(path, evidence=evidence)

    assert [row[1]["event_id"] for row in rows] == ["event-1"]
    assert rows[0][2] == f"{path}:0"
    assert report["blocked"] is True
    assert report["read_rows"] == 4
    assert report["valid_rows"] == report["events_rows"] == 1
    assert report["invalid"] == report["invalid_rows"] == 2
    assert report["blank_rows"] == 1
    assert report["skipped_rows"] == 0
    manifest = _manifest(report)
    assert len(manifest["records"]) == report["quarantine"]["records"] == 2
    for entry, expected, number, offset in zip(
        manifest["records"],
        (corrupt, last),
        (3, 4),
        (len(first + blank), len(first + blank + corrupt)),
        strict=True,
    ):
        assert (evidence / entry["file"]).read_bytes() == expected
        assert entry["source"] == str(path)
        assert entry["line"] == number
        assert entry["offset"] == offset
        assert entry["length"] == len(expected)
        assert entry["sha256"] == hashlib.sha256(expected).hexdigest()
        assert entry["code"] in {"json_invalid", "json_encoding_invalid"}
    assert "do-not-report" not in json.dumps(report)
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == signature.st_mtime_ns

    manifest_bytes = (evidence / "manifest.json").read_bytes()
    manifest_stat = (evidence / "manifest.json").stat()
    skipped_rows, skipped = _scan(path, skip_invalid=True, evidence=evidence)
    assert skipped_rows == rows
    assert skipped["blocked"] is False
    assert skipped["skipped_rows"] == 2
    assert (evidence / "manifest.json").read_bytes() == manifest_bytes
    assert (evidence / "manifest.json").stat().st_mtime_ns == manifest_stat.st_mtime_ns
    assert path.read_bytes() == original


def test_evidence_is_optional_and_diagnostics_are_bounded(tmp_path: Path) -> None:
    path = _source(tmp_path, b"{broken\x00}\n" * 105)
    _rows, report = _scan(path)
    assert report["invalid_rows"] == 105
    assert len(report["diagnostics"]) == 100
    assert report["quarantine"] == {"status": "not_requested", "records": 0}
    assert sorted(item.name for item in tmp_path.iterdir()) == [path.name]


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b'{"event_id":"a","value":NaN}\n', "json_nonfinite_number"),
        (b'{"event_id":"a","value":Infinity}\n', "json_nonfinite_number"),
        (b'{"event_id":"a","nested":{"value":-Infinity}}\n', "json_nonfinite_number"),
        (b'{"event_id":"a","value":1e400}\n', "json_nonfinite_number"),
        (b'{"event_id":"a","event_id":"b"}\n', "json_duplicate_key"),
        (b'{"event_id":"a","value":"\\ud800"}\n', "json_encoding_invalid"),
        ('{"event_id":"a"}\n'.encode("utf-16"), "json_encoding_invalid"),
        (b"[]\n", "record_not_object"),
        (b"{}\n", "event_id_required"),
    ],
)
def test_strict_json_never_becomes_a_valid_record(
    tmp_path: Path, data: bytes, code: str
) -> None:
    rows, report = _scan(_source(tmp_path, data), skip_invalid=True)
    assert rows == []
    assert report["invalid"] >= 1
    assert report["valid_rows"] == 0
    assert report["diagnostics"][0]["code"] == code


def test_legacy_event_id_and_semantic_duplicates(tmp_path: Path) -> None:
    data = b'{"id":"legacy","value":1}\n{"value":1,"id":"legacy"}\n' + _line(
        _event("other")
    )
    rows, report = _scan(_source(tmp_path, data))
    assert len(rows) == report["events_rows"] == report["valid_rows"] == 3
    assert report["unique_events"] == 2
    assert report["duplicate_events"] == report["duplicate_rows"] == 1
    assert report["duplicate_raw"] == 0


@pytest.mark.parametrize("skip_invalid", [False, True])
def test_event_conflict_is_never_skippable(tmp_path: Path, skip_invalid: bool) -> None:
    path = _source(tmp_path, _line(_event(value=1)) + _line(_event(value=2)))
    with pytest.raises(MaintenanceError, match="^migration_event_id_conflict$"):
        _scan(path, skip_invalid=skip_invalid)


def test_raw_filtering_legacy_controls_dedup_and_counts(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    record = _raw(project)
    legacy = dict(record)
    del legacy["native_id_scope"]
    del legacy["native_event_id_stable"]
    foreign = _raw(tmp_path / "other")
    foreign["raw_payload_hash"] = "foreign-schema-is-not-validated"
    path = _source(
        tmp_path,
        _line(record) + _line(legacy) + _line(foreign) + b"\n",
        "raw.ndjson",
    )

    rows, report = _scan(path, kind="raw", project=project)

    assert len(rows) == report["raw_rows"] == report["valid_rows"] == 2
    assert report["unique_raw"] == 1
    assert report["duplicate_raw"] == report["duplicate_rows"] == 1
    assert report["other_project_raw"] == report["filtered_rows"] == 1
    assert report["blank_rows"] == 1
    assert report["read_rows"] == 4
    assert report["invalid"] == 0


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("raw_payload_hash", "sha256:wrong", "raw_payload_hash_mismatch"),
        ("raw_event_id", "raw_wrong", "raw_identity_mismatch"),
        ("native_identity_key", "native_wrong", "raw_identity_mismatch"),
        ("received_at", None, "raw_received_at_required"),
        ("raw_payload", [], "raw_schema_invalid"),
        ("schema_version", 2, "raw_schema_invalid"),
    ],
)
def test_raw_validation_uses_existing_native_primitives(
    tmp_path: Path, field: str, value: Any, code: str
) -> None:
    record = _raw(tmp_path)
    record[field] = value
    rows, report = _scan(_source(tmp_path, _line(record)), kind="raw")
    assert rows == []
    assert report["blocked"] is True
    assert report["diagnostics"][0]["code"] == code


def test_raw_nonfinite_metadata_is_rejected_before_project_filter(
    tmp_path: Path,
) -> None:
    data = _line(_raw(tmp_path)).replace(
        b'"schema_version": 1', b'"schema_version": NaN'
    )
    rows, report = _scan(_source(tmp_path, data), kind="raw")
    assert rows == []
    assert report["invalid"] == 1
    assert report["diagnostics"][0]["code"] == "json_nonfinite_number"


def test_native_identity_conflict_is_not_a_skippable_corrupt_line(
    tmp_path: Path,
) -> None:
    first, second = _raw(tmp_path, value=1), _raw(tmp_path, value=2)
    assert first["raw_event_id"] != second["raw_event_id"]
    assert first["native_identity_key"] == second["native_identity_key"]
    path = _source(tmp_path, _line(first) + _line(second))
    with pytest.raises(MaintenanceError, match="^migration_native_identity_conflict$"):
        _scan(path, kind="raw", skip_invalid=True)


def test_validator_failure_never_exposes_payload_in_diagnostics(tmp_path: Path) -> None:
    def invalid(_record: JsonObject) -> None:
        raise ValueError("private-payload-should-never-appear")

    source = _source(tmp_path, _line({"source_project_ref": str(tmp_path.resolve())}))
    report: JsonObject = {}
    assert (
        list(JournalScanService(invalid).rows([("raw", source)], tmp_path, report))
        == []
    )
    assert report["diagnostics"][0]["code"] == "raw_identity_invalid"
    assert "private-payload" not in json.dumps(report)


@pytest.mark.parametrize("scope", ["provider", "adapter", "session", "project"])
@pytest.mark.parametrize("stable", [False, True])
def test_legacy_raw_identity_controls_are_matched_without_rewriting(
    tmp_path: Path, scope: str, stable: bool
) -> None:
    record = _raw(tmp_path, scope=scope, stable=stable)
    del record["native_id_scope"]
    del record["native_event_id_stable"]
    data = _line(record)
    path = _source(tmp_path, data)
    rows, report = _scan(path, kind="raw")
    assert rows[0][1] == record
    assert report["invalid"] == 0
    assert "native_id_scope" not in rows[0][1]
    assert "native_event_id_stable" not in rows[0][1]
    assert path.read_bytes() == data


def test_discovery_order_local_fallback_and_no_double_import(tmp_path: Path) -> None:
    project, workplace, flow = _layout(tmp_path)
    events = _source(flow, _line(_event()), "runtime/events/events.ndjson")
    raw_b = _source(
        workplace,
        _line(_raw(project, native_id="b")),
        "runtime/agent-events/raw/v1/b.ndjson",
    )
    raw_a = _source(
        workplace,
        _line(_raw(project, native_id="a")),
        "runtime/agent-events/raw/v1/a.ndjson",
    )
    local = _source(
        flow,
        _line(_raw(project, native_id="c")),
        "runtime/agent-events/raw/v1/c.ndjson",
    )
    scanner = JournalScanService()
    actual_flow, sources = scanner.discover(project, workplace)
    assert actual_flow == flow
    assert sources == [
        ("events", events),
        ("raw", raw_a),
        ("raw", raw_b),
        ("raw", local),
    ]
    assert scanner.discover(project, flow)[1] == [("events", events), ("raw", local)]


def test_preflight_blocks_and_preserves_without_mutating_sources(
    tmp_path: Path,
) -> None:
    project, workplace, flow = _layout(tmp_path)
    data = _line(_event()) + b"\x00broken\r\n"
    source = _source(flow, data, "runtime/events/events.ndjson")
    scanner = JournalScanService()
    report = scanner.preflight(project, workplace, evidence_dir=tmp_path / "evidence")
    assert report["status"] == "blocked"
    assert report["applied"] is False
    assert _manifest(report)["records"][0]["offset"] == len(_line(_event()))
    skipped = scanner.preflight(project, workplace, skip_invalid=True)
    assert skipped["status"] == "planned"
    assert skipped["skipped_rows"] == 1
    assert source.read_bytes() == data
    assert not list(flow.rglob("*.sqlite3"))


@pytest.mark.parametrize("member", ["record", "manifest"])
def test_conflicting_evidence_is_never_overwritten(tmp_path: Path, member: str) -> None:
    source = _source(tmp_path, b"\x00broken\r\n")
    evidence = tmp_path / "evidence"
    _rows, report = _scan(source, evidence=evidence)
    manifest = _manifest(report)
    target = (
        evidence / manifest["records"][0]["file"]
        if member == "record"
        else evidence / "manifest.json"
    )
    target.write_bytes(b"tampered-evidence")
    with pytest.raises(MaintenanceError, match="^quarantine_evidence_conflict$"):
        _scan(source, evidence=evidence)
    assert target.read_bytes() == b"tampered-evidence"
    assert source.read_bytes() == b"\x00broken\r\n"


def test_evidence_tampering_during_a_scan_is_detected(tmp_path: Path) -> None:
    source = _source(tmp_path, b"\x00bad\n" + _line(_event()))
    evidence = tmp_path / "evidence"
    report: JsonObject = {}
    rows = JournalScanService().rows(
        [("events", source)], tmp_path, report, quarantine_dir=evidence
    )
    assert next(rows)[1]["event_id"] == "event-1"
    target = next((evidence / "records").glob("*.bin"))
    target.write_bytes(b"tamper")
    with pytest.raises(MaintenanceError, match="^quarantine_evidence_conflict$"):
        list(rows)
    assert report["quarantine"]["status"] != "verified"


def test_source_drift_during_iteration_is_detected(tmp_path: Path) -> None:
    source = _source(tmp_path, _line(_event("first")) + _line(_event("second")))
    report: JsonObject = {}
    rows = JournalScanService().rows([("events", source)], tmp_path, report)
    assert next(rows)[1]["event_id"] == "first"
    with source.open("ab") as target:
        target.write(_line(_event("third")))
    with pytest.raises(MaintenanceError, match="^migration_source_changed$"):
        list(rows)


def test_full_hash_detects_same_size_and_frozen_stat_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, _line(_event("first")) + _line(_event("second")))
    original_signature = journal_scan._signature(source)

    def frozen_path(_path: Path) -> tuple[int, int, int, int, int]:
        return original_signature

    def frozen_file(value: os.stat_result) -> tuple[int, int, int, int, int]:
        assert value.st_size == original_signature[2]
        return original_signature

    monkeypatch.setattr(journal_scan, "_signature", frozen_path)
    monkeypatch.setattr(journal_scan, "_stat_signature", frozen_file)
    report: JsonObject = {}
    rows = JournalScanService().rows([("events", source)], tmp_path, report)
    next(rows)
    original_stat = source.stat()
    source.write_bytes(source.read_bytes().replace(b"second", b"SECOND"))
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    with pytest.raises(MaintenanceError, match="^migration_source_changed$"):
        list(rows)


def test_preceding_pass_manifest_is_enforced(tmp_path: Path) -> None:
    source = _source(tmp_path, _line(_event("first")))
    _rows, report = _scan(source)
    source.write_bytes(_line(_event("other")))
    with pytest.raises(MaintenanceError, match="^migration_source_changed$"):
        list(JournalScanService().rows([("events", source)], tmp_path, report))


def test_handle_ctime_can_differ_from_path_ctime_without_false_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, _line(_event()))
    real_fstat = journal_scan.os.fstat
    real_signature = journal_scan._stat_signature
    handle_stats: list[os.stat_result] = []

    def handle_stat(descriptor: int) -> os.stat_result:
        result = real_fstat(descriptor)
        handle_stats.append(result)
        return result

    def signature(value: os.stat_result) -> tuple[int, int, int, int, int]:
        result = real_signature(value)
        if any(value is item for item in handle_stats):
            return (*result[:4], result[4] + 1)
        return result

    monkeypatch.setattr(journal_scan.os, "fstat", handle_stat)
    monkeypatch.setattr(journal_scan, "_stat_signature", signature)
    rows, report = _scan(source)
    assert len(rows) == 1
    expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["sources"][0]["sha256"] == expected_hash


def test_earlier_source_changed_while_scanning_later_file(tmp_path: Path) -> None:
    first = _source(tmp_path, _line(_event("first")), "first.ndjson")
    second = _source(tmp_path, _line(_event("second")), "second.ndjson")
    report: JsonObject = {}
    rows = JournalScanService().rows(
        [("events", first), ("events", second)], tmp_path, report
    )
    assert next(rows)[1]["event_id"] == "first"
    assert next(rows)[1]["event_id"] == "second"
    first.write_bytes(_line(_event("other")))
    with pytest.raises(MaintenanceError, match="^migration_source_changed$"):
        list(rows)


def test_discovery_addition_during_preflight_is_detected(tmp_path: Path) -> None:
    project, workplace, flow = _layout(tmp_path)
    _source(flow, _line(_raw(project)), "runtime/agent-events/raw/v1/a.ndjson")

    def validate(record: JsonObject) -> None:
        journal_scan._validate_native_record(record)
        _source(
            flow,
            _line(_raw(project, native_id="b")),
            "runtime/agent-events/raw/v1/b.ndjson",
        )

    with pytest.raises(MaintenanceError, match="^migration_source_changed$"):
        JournalScanService(validate).preflight(project, workplace)


def test_symlink_sources_and_evidence_directories_are_refused(tmp_path: Path) -> None:
    source = _source(tmp_path, b"\x00broken\n")
    link = tmp_path / "linked.ndjson"
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    evidence = tmp_path / "evidence"
    try:
        link.symlink_to(source)
        evidence.symlink_to(target_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this environment")
    with pytest.raises(MaintenanceError, match="^migration_source_symlink$"):
        _scan(link)
    with pytest.raises(MaintenanceError, match="^quarantine_path_unsafe$"):
        _scan(source, evidence=evidence)
    assert not list(target_dir.iterdir())


def test_nonregular_and_missing_sources_are_not_empty_success(tmp_path: Path) -> None:
    with pytest.raises(MaintenanceError, match="^migration_source_not_regular$"):
        _scan(tmp_path)
    with pytest.raises(MaintenanceError, match="^migration_source_unavailable$"):
        _scan(tmp_path / "missing.ndjson")


def test_duplicate_index_is_temporary_disk_backed_and_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect = journal_scan.sqlite3.connect
    connections: list[sqlite3.Connection] = []

    def capture(database: str) -> sqlite3.Connection:
        assert database == ""
        connection = connect(database)
        connections.append(connection)
        return connection

    monkeypatch.setattr(journal_scan.sqlite3, "connect", capture)
    path = _source(tmp_path, _line(_event()) * 3000)
    _rows, report = _scan(path)
    assert report["unique_events"] == 1
    assert report["duplicate_rows"] == 2999
    assert len(connections) == 1
    with pytest.raises(journal_scan.sqlite3.ProgrammingError):
        connections[0].execute("SELECT 1")


def test_closing_partial_iterator_releases_index_without_certifying_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connect = journal_scan.sqlite3.connect
    connections: list[sqlite3.Connection] = []

    def capture(database: str) -> sqlite3.Connection:
        connection = connect(database)
        connections.append(connection)
        return connection

    monkeypatch.setattr(journal_scan.sqlite3, "connect", capture)
    path = _source(tmp_path, _line(_event("a")) + _line(_event("b")))
    report: JsonObject = {}
    iterator = JournalScanService().rows([("events", path)], tmp_path, report)
    next(iterator)
    assert isinstance(iterator, Generator)
    iterator.close()
    assert report["sources"] == []
    with pytest.raises(journal_scan.sqlite3.ProgrammingError):
        connections[0].execute("SELECT 1")


def test_import_and_construction_do_not_load_main_host_or_do_io(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    code = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            f"sys.path[:0] = [{str(root / 'src')!r}, {str(root / 'tools')!r}]",
            "from processforge_core.maintenance.journal_scan import JournalScanService",
            "def deny_io(*args, **kwargs): raise AssertionError('constructor I/O')",
            "Path.open = deny_io",
            "Path.stat = deny_io",
            "JournalScanService()",
            "assert 'processforge' not in sys.modules",
            "assert 'pf_runtime.host' not in sys.modules",
            "assert 'pf_runtime.raw_ingress_kernel' not in sys.modules",
            "print('cold scanner import and construction: ok')",
        ]
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "cold scanner import and construction: ok"
