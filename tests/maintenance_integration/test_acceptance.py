"""Exercise the operator's complete maintenance flow through real entrypoints."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pf_runtime.raw_ingress_kernel import (
    NativeAgentEvent,
    RawIngressKernel,
    raw_event_id,
    raw_payload_hash,
    stable_native_identity_key,
)

ROOT = Path(__file__).resolve().parents[2]
CORRUPT = b'{"event_id":"invalid","private":"never-print-this"}\x00\r\n'


def _cli(
    scratch: Path, *arguments: str, expected: int = 0, legacy: bool = False
) -> dict[str, Any]:
    native_tmp = scratch / "native-tmp"
    native_tmp.mkdir(exist_ok=True)
    environment = dict(
        os.environ,
        PYTHONDONTWRITEBYTECODE="1",
        TEMP=str(native_tmp),
        TMP=str(native_tmp),
        TMPDIR=str(native_tmp),
    )
    entrypoint = ROOT / ("tools/migrate-hook-journals.py" if legacy else "bin/pf.py")
    command = [sys.executable, "-B", "-X", "utf8", str(entrypoint)]
    if not legacy:
        command.append("journal-maintenance")
    result = subprocess.run(
        [*command, *arguments],
        cwd=scratch,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    assert "never-print-this" not in result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert isinstance(report, dict)
    return report


def _legacy_sources(scratch: Path) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    project = scratch / "Проект с пробелами"
    workplace = scratch / "Рабочая область"
    flow = project / ".pf"
    flow.mkdir(parents=True)
    (flow / "process-forge.yaml").write_text(
        "schema_version: 1\nproject: {id: maintenance-test}\n", encoding="utf-8"
    )
    events = flow / "runtime/events/events.ndjson"
    events.parent.mkdir(parents=True)
    event = {
        "event_id": "evt_acceptance",
        "event_type": "decision",
        "data": {"text": "Сохранить без изменений"},
    }
    line = json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n"
    events.write_bytes(line + line + CORRUPT)
    raw = workplace / "runtime/agent-events/raw/v1/2026/10/22/01.ndjson"
    raw.parent.mkdir(parents=True)
    native = NativeAgentEvent(
        "test",
        "adapter",
        "reply",
        {"answer": "accepted"},
        native_id_scope="session",
        native_event_id_stable=False,
        source_session_id="maintenance-session",
        source_project_ref=str(project),
    )
    record = RawIngressKernel(workplace)._raw_record(
        native,
        raw_event_id(native),
        raw_payload_hash(native.raw_payload),
        stable_native_identity_key(native),
        datetime.now(timezone.utc),
    )
    other_project = dict(record, source_project_ref=str(scratch / "another-project"))
    raw.write_bytes(
        b"\n".join(json.dumps(row).encode() for row in (record, other_project)) + b"\n"
    )
    return project, workplace, events, raw, event


def test_cli_backups_include_committed_wal_and_restore_exclusively(
    tmp_path: Path,
) -> None:
    source = tmp_path / "live.sqlite3"
    bundle = tmp_path / "согласованный backup"
    destination = tmp_path / "restored.sqlite3"
    with sqlite3.connect(source) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT)")
        writer.executemany(
            "INSERT INTO evidence(value) VALUES (?)", [("alpha",), ("beta",)]
        )
        writer.commit()
        assert source.with_name(source.name + "-wal").stat().st_size > 0
        _cli(
            tmp_path,
            "backup",
            "--database",
            str(source),
            "--output",
            str(bundle),
            "--json",
        )
        _cli(tmp_path, "verify", "--backup", str(bundle), "--json")
        _cli(
            tmp_path,
            "restore",
            "--backup",
            str(bundle),
            "--destination",
            str(destination),
            "--json",
        )
        with sqlite3.connect(destination) as restored:
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute(
                "SELECT value FROM evidence ORDER BY id"
            ).fetchall() == [
                ("alpha",),
                ("beta",),
            ]
        original = destination.read_bytes()
        _cli(
            tmp_path,
            "restore",
            "--backup",
            str(bundle),
            "--destination",
            str(destination),
            "--json",
            expected=1,
        )
        assert destination.read_bytes() == original
        writer.execute("INSERT INTO evidence(value) VALUES ('after-backup')")
        writer.commit()
        with sqlite3.connect(destination) as restored:
            assert restored.execute("SELECT count(*) FROM evidence").fetchone()[0] == 2
    snapshot = bundle / "database.sqlite3"
    snapshot.write_bytes(snapshot.read_bytes() + b"tamper")
    _cli(tmp_path, "verify", "--backup", str(bundle), "--json", expected=1)
    refused = tmp_path / "must-not-exist.sqlite3"
    _cli(
        tmp_path,
        "restore",
        "--backup",
        str(bundle),
        "--destination",
        str(refused),
        "--json",
        expected=1,
    )
    assert not refused.exists()


def test_cli_refusal_quarantine_explicit_skip_replay_and_legacy_entrypoint(
    tmp_path: Path,
) -> None:
    project, workplace, events, raw, event = _legacy_sources(tmp_path)
    originals = events.read_bytes(), raw.read_bytes()
    event_db = project / ".pf/runtime/events/events.sqlite3"
    raw_db = project / ".pf/runtime/agent-events/hooks.sqlite3"
    arguments = ["--project-root", str(project), "--workplace", str(workplace)]
    plan = _cli(tmp_path, "inspect", *arguments, "--json", expected=1)
    assert plan["invalid"] == 1 and plan["other_project_raw"] == 1
    assert plan["unique_events"] == 1 and plan["unique_raw"] == 1
    assert not event_db.exists() and not raw_db.exists()
    planned = _cli(tmp_path, "import", *arguments, "--skip-invalid", "--json")
    assert planned["status"] == "planned" and not planned["applied"]
    assert not event_db.exists() and not raw_db.exists()
    assert not (project / ".pf/runtime/journal-maintenance").exists()
    refusal = tmp_path / "refusal-evidence"
    blocked = _cli(
        tmp_path,
        "import",
        *arguments,
        "--apply",
        "--evidence-dir",
        str(refusal),
        "--json",
        expected=1,
    )
    assert blocked["blocked"] and blocked["invalid"] == 1
    assert not event_db.exists() and not raw_db.exists()
    preserved = [
        path
        for path in refusal.rglob("*")
        if path.is_file() and path.read_bytes() == CORRUPT
    ]
    assert preserved, (
        "Refusing invalid import must still preserve the exact corrupt bytes."
    )
    manifests = [path for path in refusal.rglob("*.json") if path.is_file()]
    assert any(
        hashlib.sha256(CORRUPT).hexdigest() in path.read_text(encoding="utf-8")
        for path in manifests
    )
    quarantine_manifest = Path(blocked["quarantine"]["manifest"])
    quarantine = json.loads(quarantine_manifest.read_text(encoding="utf-8"))
    assert len(quarantine["records"]) == 1
    record = quarantine["records"][0]
    assert Path(record["source"]) == events
    assert record["line"] == 3
    assert record["offset"] == len(originals[0]) - len(CORRUPT)
    assert record["length"] == len(CORRUPT)
    assert record["sha256"] == hashlib.sha256(CORRUPT).hexdigest()
    assert (quarantine_manifest.parent / record["file"]).read_bytes() == CORRUPT
    first = _cli(
        tmp_path,
        "import",
        *arguments,
        "--apply",
        "--skip-invalid",
        "--evidence-dir",
        str(tmp_path / "first-import-evidence"),
        "--json",
    )
    assert first["status"] == "ready" and first["stored_counts"] == {
        "events": 1,
        "raw": 1,
    }
    assert first["counts"] == {
        "read": 5,
        "valid": 3,
        "imported": 2,
        "already_present": 1,
        "skipped": 2,
        "corrupted": 1,
    }
    from processforge_core.process_event_journal import ProcessEventJournal
    from processforge_core.raw_hook_journal import RawHookJournal

    assert ProcessEventJournal().get(event_db, event["event_id"]) == event
    assert RawHookJournal().count(raw_db) == 1
    replay = _cli(tmp_path, *arguments, "--apply", "--skip-invalid", legacy=True)
    assert replay["stored_counts"] == first["stored_counts"]
    assert replay["counts"]["imported"] == 0
    assert replay["counts"]["already_present"] == 3
    assert replay["verification"]["semantic_replay"]["inserted"] == 0
    assert len(replay["backups"]) == 2
    for backup in replay["backups"]:
        assert backup["status"] == "verified"
        bundle = backup["bundle"]
        _cli(tmp_path, "verify", "--backup", bundle, "--json")
        restored = tmp_path / ("restored-" + backup["kind"] + ".sqlite3")
        _cli(
            tmp_path,
            "restore",
            "--backup",
            bundle,
            "--destination",
            str(restored),
            "--json",
        )
        if backup["kind"] == "events":
            assert ProcessEventJournal().get(restored, event["event_id"]) == event
        else:
            assert RawHookJournal().count(restored) == 1
    assert (
        ProcessEventJournal().count(event_db) == 1
        and RawHookJournal().count(raw_db) == 1
    )
    assert (events.read_bytes(), raw.read_bytes()) == originals
    for database in (event_db, raw_db):
        with sqlite3.connect(database) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_library_import_and_construction_do_not_load_main_or_start_services(
    tmp_path: Path,
) -> None:
    script = """
import importlib.abc
import sys
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[1]) / 'src'), str(Path(sys.argv[1]) / 'tools')]
class BlockHost(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'processforge' or fullname.startswith(('pf_host', 'pf_runtime.app_server')):
            raise AssertionError('Unexpected Host import: ' + fullname)
sys.meta_path.insert(0, BlockHost())
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.journal_scan import JournalScanService
from processforge_core.maintenance.journals import JournalMaintenanceService
def audit(event, args):
    if event in ('sqlite3.connect', 'socket.connect', 'subprocess.Popen', 'os.mkdir'):
        raise AssertionError('Constructor I/O: ' + event)
sys.addaudithook(audit)
SQLiteBackupService()
JournalScanService()
JournalMaintenanceService()
assert 'processforge' not in sys.modules
print('cold-core-ok')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", script, str(ROOT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "cold-core-ok"


def test_windows_junctions_are_refused_by_all_maintenance_operations(
    tmp_path: Path,
) -> None:
    """Exercise real Windows reparse points without requiring symlink privilege."""
    if os.name != "nt":
        pytest.skip("Windows junction behavior is specific to NTFS.")
    project, workplace, events, raw, _event = _legacy_sources(tmp_path)
    source = project / "live.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence(value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('preserved')")
    bundle = project / "bundle"
    _cli(tmp_path, "backup", "--database", str(source), "--output", str(bundle))
    original_source = source.read_bytes()
    originals = events.read_bytes(), raw.read_bytes()
    junction = tmp_path / "project-junction"
    script = tmp_path / "create-junction.ps1"
    script.write_text(
        "param([string] $JunctionPath, [string] $JunctionTarget)\n"
        "$ErrorActionPreference = 'Stop'\n"
        "New-Item -ItemType Junction -Path $JunctionPath "
        "-Target $JunctionTarget | Out-Null\n",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
            "-JunctionPath",
            str(junction),
            "-JunctionTarget",
            str(project),
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert junction.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    cases = (
        (
            "backup",
            "--database",
            str(junction / "live.sqlite3"),
            "--output",
            str(tmp_path / "unintended-bundle"),
        ),
        ("verify", "--backup", str(junction / "bundle")),
        (
            "restore",
            "--backup",
            str(bundle),
            "--destination",
            str(junction / "restored.sqlite3"),
        ),
        (
            "inspect",
            "--project-root",
            str(junction),
            "--workplace",
            str(workplace),
        ),
        (
            "import",
            "--project-root",
            str(junction),
            "--workplace",
            str(workplace),
            "--apply",
            "--skip-invalid",
        ),
    )
    for arguments in cases:
        report = _cli(tmp_path, *arguments, "--json", expected=1)
        assert report["status"] == "failed"
    assert source.read_bytes() == original_source
    assert (events.read_bytes(), raw.read_bytes()) == originals
    assert not (project / "restored.sqlite3").exists()
    assert not (tmp_path / "unintended-bundle").exists()
    assert not (project / ".pf/runtime/journal-maintenance").exists()
