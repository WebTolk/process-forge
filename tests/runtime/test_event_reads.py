"""Runtime event summaries retain the allowlist and isolate failed project reads."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from pf_runtime import service
from smoke_runtime_scheduler_failure_isolation import pf

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.process_event_journal import ProcessEventJournal


def test_last_event_isolates_corrupt_project_and_keeps_public_allowlist(
    tmp_path: Path,
) -> None:
    roots = [tmp_path / name for name in ("bad", "good", "absent")]
    for project in roots:
        write_yaml_file(
            project / ".pf/process-forge.yaml", {"project": {"id": project.name}}
        )
    bad = roots[0] / ".pf/runtime/events/events.sqlite3"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"corrupt store")
    good = roots[1] / ".pf/runtime/events/events.sqlite3"
    ProcessEventJournal().append(
        good,
        {
            "event_id": "intended",
            "event_type": "fixture.observed",
            "time": "2026-11-16T00:00:00Z",
            "payload": {"private": "must not escape summary"},
        },
    )
    with closing(sqlite3.connect(good)) as connection:
        assert (
            connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
        )
    before = {
        p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()
    }
    runtime = SimpleNamespace(
        core=SimpleNamespace(project_id=lambda root: root.name),
        workplace_root=None,
        _project_errors={},
    )
    assert service.RuntimeProcess.last_event(
        cast(service.RuntimeProcess, runtime), roots
    ) == {
        "project_id": "good",
        "event_id": "intended",
        "event_type": "fixture.observed",
        "time": "2026-11-16T00:00:00Z",
    }
    assert list(runtime._project_errors) == [str(roots[0])]
    assert "journal_database_error" in runtime._project_errors[str(roots[0])]
    assert {
        p: p.read_bytes() for root in roots for p in root.rglob("*") if p.is_file()
    } == before


def test_fresh_cli_to_runtime_public_status_and_bound_refusal(tmp_path: Path) -> None:
    """Use real onboarding and IPC; no native, migration or identity guard patches."""
    workplace = tmp_path / "workplace"
    pf("workplace-init", "--workplace", str(workplace), "--apply")
    projects = [tmp_path / name for name in ("bad-project", "good-project")]
    for project in projects:
        project.mkdir()
        pf(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )
        pf(
            "project-mode",
            "set",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--mode",
            "simple",
        )
    pf(
        "runtime-host",
        "init",
        "--workplace",
        str(workplace),
        "--project-root",
        str(projects[0]),
        "--project-root",
        str(projects[1]),
    )
    started = False
    try:
        pf(
            "runtime",
            "start",
            "--workplace",
            str(workplace),
            "--interval",
            "60",
            "--json",
        )
        started = True
        admitted = []
        for project in projects:
            request = tmp_path / (project.name + ".json")
            request.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "event_id": project.name + "-event",
                        "event_type": "fixture.observed",
                        "project_root": str(project),
                        "source": {"adapter": "generic", "agent": "event-read-fixture"},
                        "payload": {"private": "must not escape the event summary"},
                    }
                ),
                encoding="utf-8",
            )
            admitted.append(
                json.loads(
                    pf(
                        "runtime",
                        "event",
                        "--workplace",
                        str(workplace),
                        "--input",
                        str(request),
                        "--json",
                    )
                )
            )
        status = json.loads(
            pf("runtime", "status", "--workplace", str(workplace), "--json")
        )
        assert status["health"] == "ready", status
        summary = status["last_event"]
        assert summary["event_id"] == admitted[1]["event_id"]
        assert summary["project_id"] == admitted[1]["project_id"]
        assert set(summary) == {"project_id", "event_id", "event_type", "time"}
        bad = projects[0]
        pin = bad / ".pf/data/storage-identities.json"
        pins = json.loads(pin.read_text(encoding="utf-8"))
        event_slot = next(slot for slot in pins["slots"] if slot["kind"] == "events")
        event_slot["store_id"] = "f" * 32
        pin.write_text(json.dumps(pins), encoding="utf-8")
        journal = bad / ".pf/runtime/events/events.sqlite3"
        before = (journal.read_bytes(), pin.read_bytes())
        refused = json.loads(
            pf("runtime", "status", "--workplace", str(workplace), "--json")
        )
        assert refused["health"] == "degraded", refused
        assert refused["last_event"] == summary
        assert "storage_identity_conflict" in str(refused["project_errors"])
        assert (journal.read_bytes(), pin.read_bytes()) == before
    finally:
        if started:
            pf("runtime", "stop", "--workplace", str(workplace), "--timeout", "30")
