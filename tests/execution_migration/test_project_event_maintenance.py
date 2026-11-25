"""Exercise migration and context isolation with two projects on one Runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from queue import Empty, Queue
from typing import Any

import pytest
import smoke_long_lived_runtime as runtime
import smoke_worker_run_shell as worker
from pf_runtime.service import http_json

from processforge_core.agents.hook_outbox import delivery_key
from processforge_core.agents.process_events import ProcessEventRecorder
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.raw_hook_journal import RawHookJournal
from processforge_core.runtime_service_state import runtime_process_identity

SOURCE = Path(__file__).resolve().parents[2]
EVENT_PATH = Path(".pf/runtime/events/events.sqlite3")
MIGRATOR = SOURCE / "tools/migrate-storage.py"
EVENT_TYPE = "fixture.journal.appended"
TARGET = "journal-target"
ConfirmedEvent = tuple[float, str, dict[str, Any]]

HOLD_DURING_BACKUP = """
import os, runpy, sys, time
from functools import partial
from pathlib import Path

tool, held, release, *arguments = sys.argv[1:]
entry = runpy.run_path(tool)
from processforge_core.maintenance import project_event_coordinator as coordinator
from processforge_core.maintenance.backup import SQLiteBackupService

# This child waits for unrelated CLI probes while intentionally paused.
coordinator.run_online_project_event_migration = partial(
    coordinator.run_online_project_event_migration, deadline=time.monotonic() + 180
)

verify_backup = SQLiteBackupService.verify
def hold_backup(self, bundle):
    Path(held).touch()
    deadline = time.monotonic() + 120
    while not Path(release).is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("test did not release migration")
        time.sleep(0.025)
    return verify_backup(self, bundle)

SQLiteBackupService.verify = hold_backup
if "--apply" in arguments:
    apply_identity = coordinator._Coordinator.apply_identity
    def crash_after_apply(self, *args, **kwargs):
        apply_identity(self, *args, **kwargs)
        os._exit(77)
    coordinator._Coordinator.apply_identity = crash_after_apply
raise SystemExit(entry["main"](arguments))
"""

INTERRUPT_BACKUP_COPY = """
import os, runpy, sys
tool, *arguments = sys.argv[1:]
entry = runpy.run_path(tool)
from processforge_core.maintenance import backup
def interrupt_copy(source, destination, *args, **kwargs):
    destination.write_bytes(b"interrupted fixture backup")
    os._exit(76)
backup._backup = interrupt_copy
raise SystemExit(entry["main"](arguments))
"""


def arguments(project: Path, workplace: Path, operation: str) -> list[str]:
    return [
        "--project-root",
        str(project),
        "--workplace-root",
        str(workplace),
        "--device-config",
        str(workplace.parent / "device.yaml"),
        "--project-events",
        operation,
        "--json",
    ]


def migrate(args: list[str], expected: int = 0) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-B", str(MIGRATOR), *args],
        cwd=SOURCE,
        capture_output=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    return json.loads(result.stdout)


def interrupt_backup(args: list[str]) -> None:
    child = subprocess.run(
        [sys.executable, "-B", "-c", INTERRUPT_BACKUP_COPY, str(MIGRATOR), *args],
        cwd=SOURCE,
        capture_output=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert child.returncode == 76, child.stdout + child.stderr


@contextmanager
def held_migration(
    args: list[str], root: Path, phase: str
) -> Iterator[tuple[subprocess.Popen[str], Path]]:
    held, release = root / f"{phase}.held", root / f"{phase}.release"
    with subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            HOLD_DURING_BACKUP,
            str(MIGRATOR),
            str(held),
            str(release),
            *args,
        ],
        cwd=SOURCE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    ) as child:
        try:
            deadline = time.monotonic() + 60
            while not held.is_file():
                if child.poll() is not None:
                    out, err = child.communicate(timeout=5)
                    raise AssertionError(out + err)
                assert time.monotonic() < deadline, "migration did not reach held phase"
                time.sleep(0.05)
            yield child, release
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)


def slot(project: Path) -> dict[str, Any]:
    pin = json.loads((project / ".pf/data/storage-identities.json").read_bytes())
    return next(row for row in pin["slots"] if row["kind"] == "events")


def request_event(
    endpoint: str, token: str, project: Path, event_id: str, value: int
) -> tuple[int, dict[str, object]]:
    return http_json(
        "POST",
        endpoint + "/event",
        token=token,
        payload={
            "schema_version": 1,
            "event_id": event_id,
            "event_type": EVENT_TYPE,
            "project_root": str(project),
            "source": {"adapter": "generic", "agent": "journal-test"},
            "payload": {"value": value, "text": "Журнал"},
        },
        timeout=20.0,
    )


def confirm_event(
    endpoint: str,
    token: str,
    project: Path,
    journal: ProcessEventJournal,
    event_id: str,
    value: int,
) -> dict[str, Any]:
    status, response = request_event(endpoint, token, project, event_id, value)
    assert status == 200 and response.get("event_id") == event_id, response
    assert response.get("duplicate") is False, response
    record = journal.get(project / EVENT_PATH, event_id)
    assert record is not None and record["data"] == {
        "value": value,
        "text": "Журнал",
    }
    key = delivery_key(event_id, TARGET)
    receipt = json.loads(
        (project / ".pf/runtime/hooks/results" / f"{key}.json").read_bytes()
    )
    envelope = (project / receipt["outbox"]).read_bytes()
    assert receipt["event_id"] == event_id and receipt["target_id"] == TARGET
    assert hashlib.sha256(envelope).hexdigest() == receipt["payload_sha256"]
    assert json.loads(envelope)["event"] == record
    return record


def append_stream(
    endpoint: str,
    token: str,
    project: Path,
    workplace: Path,
    stop: threading.Event,
    observed: Queue[ConfirmedEvent],
) -> None:
    journal = ProcessEventRecorder().event_journal_for_project(project, workplace)
    number = 0
    while not stop.is_set():
        event_id = f"evt_live_append_{number}"
        started = time.monotonic()
        record = confirm_event(endpoint, token, project, journal, event_id, number)
        observed.put((started, event_id, record))
        number += 1
        stop.wait(0.15)


def await_events(
    queue: Queue[ConfirmedEvent],
    stream: Future[None],
    observed: dict[str, dict[str, Any]],
    *,
    after: float = 0.0,
    count: int = 3,
) -> None:
    deadline = time.monotonic() + 30.0
    try:
        while count:
            started, event_id, record = queue.get(
                timeout=max(0.0, deadline - time.monotonic())
            )
            observed[event_id] = record
            if started >= after:
                count -= 1
    except Empty:
        if stream.done():
            stream.result()
        raise AssertionError(
            f"sibling project did not acknowledge {count} new events before the phase deadline"
        ) from None


def assert_sibling_visible(
    endpoint: str, token: str, instance: object, sibling: Path, workplace: Path
) -> None:
    status, view = http_json("GET", endpoint + "/status", token=token, timeout=15.0)
    assert status == 200 and view["instance_id"] == instance
    summary = view["last_event"]
    assert isinstance(summary, dict), view
    event_id = summary["event_id"]
    # A real supervisor tick may follow the stream's last acknowledged append.
    assert summary["project_id"] == sibling.name, summary
    journal = ProcessEventRecorder().event_journal_for_project(sibling, workplace)
    record = journal.get(sibling / EVENT_PATH, event_id)
    assert record is not None and record["event_type"] == summary["event_type"], summary


def onboard(project: Path, workplace: Path) -> None:
    runtime.pf(
        "project-onboard",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--type",
        "generic-software-project",
        "--apply",
    )


@pytest.mark.parametrize("busy_resource", ["journal", "main"])
def test_event_waits_for_project_reader_outside_workplace_admission(
    tmp_path, monkeypatch, busy_resource
):
    from pf_runtime import host

    from processforge_core.database import SQLiteDriver
    from processforge_core.maintenance import project_event_maintenance
    from processforge_core.runtime.execution_admission import ExecutionAdmission

    project, workplace = tmp_path / "fresh", tmp_path / "workplace"
    project.mkdir()
    runtime.pf("workplace-init", "--workplace", str(workplace), "--apply")
    runtime.pf(
        "config",
        "update",
        "--workplace",
        str(workplace),
        "--key",
        "runtime.garage_hooks",
        "--value",
        "true",
    )
    onboard(project, workplace)
    raw = {
        "event_type": EVENT_TYPE,
        "project_root": str(project),
        "source": {"adapter": "generic"},
    }
    host.ingest_event(dict(raw, event_id="evt_warm"), workplace, runtime.processforge)
    path = project / EVENT_PATH
    journal = ProcessEventRecorder().event_journal_for_project(project, workplace)
    before_write, reading, contended = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    original_derive = host._ingest_derived_event
    original_lock = project_event_maintenance.registry_file_lock
    original_connect = SQLiteDriver._connect
    main_path = project / ".pf/data/pf.sqlite3"

    def observe_connect(driver, database, **kwargs):
        if reading.is_set() and database == main_path.as_uri() + "?mode=ro":
            contended.set()
        return original_connect(driver, database, **kwargs)

    def derive(*args, **kwargs):
        before_write.set()
        assert reading.wait(10)
        return original_derive(*args, **kwargs)

    def observe_lock(path, *, on_contention=None, **kwargs):
        def observe():
            contended.set()
            if on_contention is not None:
                on_contention()

        return original_lock(path, on_contention=observe, **kwargs)

    monkeypatch.setattr(host, "_ingest_derived_event", derive)
    if busy_resource == "journal":
        monkeypatch.setattr(
            project_event_maintenance, "registry_file_lock", observe_lock
        )
    else:
        monkeypatch.setattr(SQLiteDriver, "_connect", observe_connect)
    pin = slot(project)
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(
            host.ingest_event,
            dict(raw, event_id="evt_contended"),
            workplace,
            runtime.processforge,
        )
        assert before_write.wait(10)
        with ExitStack() as held:
            if busy_resource == "journal":
                held.enter_context(
                    journal.connection(
                        path, driver=journal.driver, storage_host=journal.storage_host
                    )
                )
            else:
                db = held.enter_context(closing(sqlite3.connect(main_path)))
                assert db.execute("PRAGMA locking_mode=EXCLUSIVE").fetchone() == (
                    "exclusive",
                )
                db.execute("BEGIN EXCLUSIVE")
            reading.set()
            assert contended.wait(10)
            with ExecutionAdmission().workplace(
                workplace, deadline=time.monotonic() + 5
            ):
                assert not result.done()
        assert result.result(timeout=10)["duplicate"] is False
    assert slot(project) == pin
    assert journal.get(path, "evt_contended") is not None
    assert (
        host.ingest_event(
            dict(raw, event_id="evt_contended"), workplace, runtime.processforge
        )["deduplicated"]
        is True
    )


def test_project_migration_preserves_running_runtime_and_sibling_work(tmp_path: Path):
    project, sibling = tmp_path / "legacy-a", tmp_path / "fresh-b"
    workplace = tmp_path / "workplace"
    project.mkdir()
    sibling.mkdir()
    (project / ".pf").mkdir()
    (project / ".pf/process-forge.yaml").write_text(
        "schema_version: 1\nproject: {id: legacy-a}\n", encoding="utf-8"
    )
    legacy = ProcessEventJournal()
    original = {
        f"evt_original_{number}": {
            "event_id": f"evt_original_{number}",
            "event_type": "fixture.old",
            "time": "2025-01-01T00:00:00Z",
            "data": {"value": number, "text": "Перенос"},
        }
        for number in range(120)
    }
    event_source = tmp_path / "historical-events.sqlite3"
    assert legacy.append_many(event_source, original.values()) == len(original)
    runtime.pf("workplace-init", "--workplace", str(workplace), "--apply")
    runtime.pf(
        "config",
        "update",
        "--workplace",
        str(workplace),
        "--key",
        "runtime.garage_hooks",
        "--value",
        "true",
    )
    # Model a historically enrolled project with its raw and execution stores
    # already qualified. The event database is the only remaining legacy store.
    (project / ".pf/process-forge.local.yaml").write_text(
        json.dumps({"workplace": {"manifest": str(workplace / "workplace.yaml")}}),
        encoding="utf-8",
    )
    with RawHookJournal.connection(
        project / ".pf/runtime/agent-events/hooks.sqlite3", writable=True
    ):
        pass
    offline = arguments(project, workplace, "--apply")
    offline.remove("--project-events")
    assert migrate([*offline, "--offline-confirmed"])["status"] == "ready"
    (project / EVENT_PATH).parent.mkdir(parents=True, exist_ok=True)
    event_source.replace(project / EVENT_PATH)
    onboard(sibling, workplace)
    (sibling / ".pf/hooks.yaml").write_text(
        json.dumps(
            {
                "hooks": {
                    "targets": [
                        {
                            "id": TARGET,
                            "type": "outbox",
                            "enabled": True,
                            "event_types": [EVENT_TYPE],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    inspect = arguments(project, workplace, "--inspect")
    apply = arguments(project, workplace, "--apply")
    resume = arguments(project, workplace, "--resume")
    selected = migrate(inspect)
    assert [
        (row["kind"], row["scope"], row["state"]) for row in selected["targets"]
    ] == [("events", "project", "legacy")], selected
    unknown = migrate(apply, expected=1)
    assert unknown["error"]["code"] == "storage_project_event_runtime_unknown"
    assert unknown["selected_target"]["scope"] == "project"
    runtime.pf(
        "runtime-host",
        "init",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--project-root",
        str(sibling),
    )
    runtime.pf(
        "run-create",
        "--project-root",
        str(sibling),
        "--id",
        worker.RUN_ID,
        "--title",
        "Workers during sibling migration",
        "--process",
        "task-batch-execution",
        "--apply",
    )
    names = ("before-migration", "during-migration")
    for name in names:
        worker.create_task(sibling, name, title=name)
    driver = worker.driver_yaml_path(sibling, "migration-probe", sleep_seconds=180)
    no_runtime = migrate(
        [*arguments(project, workplace, "--apply"), "--offline-confirmed"],
        expected=1,
    )
    assert no_runtime["error"] == {"code": "storage_project_event_runtime_unknown"}
    runtime.start_runtime(workplace)
    try:
        initial = runtime.service_state(workplace)
        instance = initial["instance_id"]
        endpoint = str(initial["endpoint"]).rstrip("/")
        token = runtime.token(workplace)
        # The unfenced legacy journal already refuses ordinary event writes.
        status, response = request_event(
            endpoint, token, project, "evt_refused_before_migration", 0
        )
        assert (status, response) == (400, {"error": "storage_activity_unknown"})
        worker.start_task(names[0], sibling, driver=driver)
        first_worker = worker.wait_status(sibling, names[0], "running")["pid"]
        stop = threading.Event()
        queue: Queue[ConfirmedEvent] = Queue()
        observed: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=1) as threads:
            stream = threads.submit(
                append_stream, endpoint, token, sibling, workplace, stop, queue
            )
            try:
                await_events(queue, stream, observed)
                unplanned = migrate(resume, expected=1)
                assert (
                    unplanned["error"]["code"] == "storage_project_event_plan_missing"
                )
                interrupt_backup(apply)
                interrupted = slot(project)
                assert interrupted["state"] == "pending"
                evidence_root = project / ".pf/data/storage-migrations/r02-storage-v1"
                plan = evidence_root / interrupted["plan_checksum"][7:]
                assert not (plan / "backup").exists()
                assert (
                    len(list(plan.glob(".backup-stage-*/backup/database.sqlite3"))) == 1
                )
                await_events(queue, stream, observed, after=time.monotonic())
                with held_migration(apply, tmp_path, "apply") as (child, release):
                    pending = slot(project)
                    assert pending == interrupted
                    # The target is fenced while its backup is being verified.
                    refused = migrate(apply, expected=1)
                    assert (
                        refused["error"]["code"]
                        == "storage_project_event_maintenance_busy"
                    )
                    status, response = request_event(
                        endpoint, token, project, "evt_refused", 1
                    )
                    assert status == 409 and response.get("retryable") is True
                    assert response.get("error") == (
                        "storage_project_event_maintenance_busy"
                    ), response
                    await_events(
                        queue, stream, observed, after=time.monotonic(), count=3
                    )
                    assert child.poll() is None
                    assert (
                        worker.wait_status(sibling, names[0], "running")["pid"]
                        == first_worker
                    )
                    worker.start_task(names[1], sibling, driver=driver)
                    worker.wait_status(sibling, names[1], "running")
                    await_events(queue, stream, observed, after=time.monotonic())
                    assert_sibling_visible(
                        endpoint, token, instance, sibling, workplace
                    )
                    release.touch()
                    out, err = child.communicate(timeout=30)
                    assert child.returncode == 77, out + err
                assert slot(project) == pending
                status, response = request_event(
                    endpoint, token, project, "evt_refused_during_recovery", 2
                )
                assert status == 409 and response == {
                    "error": "storage_resume_required",
                    "retryable": True,
                }
                await_events(queue, stream, observed, after=time.monotonic())
                assert_sibling_visible(endpoint, token, instance, sibling, workplace)
                with held_migration(resume, tmp_path, "resume") as (child, release):
                    assert slot(project) == pending
                    await_events(
                        queue, stream, observed, after=time.monotonic(), count=3
                    )
                    assert child.poll() is None
                    assert_sibling_visible(
                        endpoint, token, instance, sibling, workplace
                    )
                    assert (
                        worker.wait_status(sibling, names[0], "running")["pid"]
                        == first_worker
                    )
                    # The continuous stream has already crossed each held phase.
                    # Join the writer before explicitly requesting Inspector so
                    # both operations do not contend for B's own journal.
                    stop.set()
                    stream.result(timeout=25)
                    tick_status, tick = http_json(
                        "POST",
                        endpoint + "/tick",
                        token=token,
                        payload={
                            "project_roots": [str(project), str(sibling)],
                            "inspector": True,
                        },
                        timeout=20.0,
                    )
                    assert tick_status == 500 and len(tick["projects"]) == 2, tick
                    by_project = {row["project_id"]: row for row in tick["projects"]}
                    assert by_project.keys() == {project.name, sibling.name}, tick
                    blocked = by_project[project.name]
                    continuing = by_project[sibling.name]
                    assert blocked["storage_error"]["retryable"] is True
                    assert (
                        continuing["inspector"] == "tick"
                        and "storage_error" not in continuing
                    )
                    inspector = continuing["inspector_result"]
                    assert inspector["failed"] == [], inspector
                    assert names[0] in inspector["observed"] + inspector["running"], (
                        inspector
                    )
                    assert child.poll() is None
                    release.touch()
                    out, err = child.communicate(timeout=30)
                    assert child.returncode == 0, out + err
                    assert json.loads(out)["status"] == "ready"
            finally:
                stop.set()
                stream.result(timeout=25)
                while not queue.empty():
                    _, event_id, record = queue.get_nowait()
                    observed[event_id] = record
        assert slot(project) == {**pending, "state": "ready"}
        assert migrate(inspect)["targets"][0]["state"] == "ready"
        code, view = http_json("GET", endpoint + "/status", token=token, timeout=15.0)
        assert code == 200 and view["instance_id"] == instance
        after_ready = "evt_after_ready"
        status, reply = request_event(endpoint, token, project, after_ready, 2)
        assert status == 200 and reply["event_id"] == after_ready, reply
        assert reply["duplicate"] is False, reply
        a = ProcessEventRecorder().event_journal_for_project(project, workplace)
        reopened = a.get(project / EVENT_PATH, after_ready)
        assert reopened is not None and reopened["data"] == {
            "value": 2,
            "text": "Журнал",
        }
        for event_id in (
            "evt_refused_before_migration",
            "evt_refused",
            "evt_refused_during_recovery",
        ):
            assert a.get(project / EVENT_PATH, event_id) is None
        runtime.pf(
            "project-context-refresh",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--apply",
        )
        checked = runtime.pf(
            "project-context-check",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
        )
        assert "STATUS: fresh" in checked.stdout
        for event_id, expected in original.items():
            assert a.get(project / EVENT_PATH, event_id) == expected
        # Compare every fixture event in both journals, including the reopened A
        # event. Extra rows from refused requests or cross-project writes fail parity.
        for root, events in (
            (project, {**original, after_ready: reopened}),
            (sibling, observed),
        ):
            with closing(sqlite3.connect(root / EVENT_PATH)) as sql:
                rows = sql.execute(
                    "SELECT event_id, record FROM events WHERE event_type IN (?, ?)",
                    ("fixture.old", EVENT_TYPE),
                ).fetchall()
            assert len(rows) == len(events)
            assert {event_id: json.loads(body) for event_id, body in rows} == events
    finally:
        try:
            for name in names:
                worker.stop_if_running(sibling, name)
                worker.ensure_stopped(sibling, name)
        finally:
            runtime.stop_runtime(workplace)


def check_context(
    project: Path, workplace: Path, *, expected: int = 0
) -> dict[str, Any]:
    result = runtime.pf(
        "project-context-check",
        "--project-root",
        str(project),
        "--workplace",
        str(workplace),
        "--json",
        "--strict",
        expect=expected,
    )
    return json.loads(result.stdout)


def test_stale_project_context_preserves_fresh_sibling_work(tmp_path: Path) -> None:
    project, sibling = tmp_path / "project-a", tmp_path / "project-b"
    workplace = tmp_path / "workplace"
    runtime.pf("workplace-init", "--workplace", str(workplace), "--apply")
    runtime.pf(
        "config",
        "update",
        "--workplace",
        str(workplace),
        "--key",
        "runtime.garage_hooks",
        "--value",
        "true",
    )
    for root in (project, sibling):
        root.mkdir()
        onboard(root, workplace)
    (sibling / ".pf/hooks.yaml").write_text(
        json.dumps(
            {
                "hooks": {
                    "targets": [
                        {
                            "id": TARGET,
                            "type": "outbox",
                            "enabled": True,
                            "event_types": [EVENT_TYPE],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    runtime.pf(
        "runtime-host",
        "init",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--project-root",
        str(sibling),
    )
    runtime.pf(
        "run-create",
        "--project-root",
        str(sibling),
        "--id",
        worker.RUN_ID,
        "--title",
        "Workers during sibling context staleness",
        "--process",
        "task-batch-execution",
        "--apply",
    )
    names = ("before-stale", "while-stale")
    for name in names:
        worker.create_task(sibling, name, title=name)
    driver = worker.driver_yaml_path(
        sibling, "stale-context-probe", sleep_seconds=180, timeout_seconds=240
    )

    baseline = {}
    for root in (project, sibling):
        runtime.pf(
            "project-context-refresh",
            "--project-root",
            str(root),
            "--workplace",
            str(workplace),
            "--apply",
        )
        checked = check_context(root, workplace)
        assert checked["status"] == "fresh", checked
        assert checked["policy_action"] == "continue", checked
        baseline[root] = checked["snapshot_id"]

    runtime.start_runtime(workplace)
    try:
        initial = runtime.service_state(workplace)
        instance = initial["instance_id"]
        assert isinstance(instance, str) and instance
        endpoint = str(initial["endpoint"]).rstrip("/")
        token = runtime.token(workplace)
        journal = ProcessEventRecorder().event_journal_for_project(sibling, workplace)

        worker.start_task(names[0], sibling, driver=driver)
        first_worker = worker.wait_status(sibling, names[0], "running")["pid"]
        assert first_worker > 0
        confirm_event(endpoint, token, sibling, journal, "evt_before_stale", 0)

        subject = "fixture.project-a"
        reason = "readiness isolation fixture marked project A stale"
        runtime.pf(
            "project-context-mark-stale",
            "--project-root",
            str(project),
            "--subject",
            subject,
            "--reason",
            reason,
        )

        def assert_selected_contexts() -> None:
            stale = check_context(project, workplace, expected=1)
            assert stale["status"] == "stale", stale
            assert stale["snapshot_id"] == baseline[project], stale
            assert {"id": subject, "reason": reason} in stale["stale_resources"], stale
            fresh = check_context(sibling, workplace)
            assert fresh["status"] == "fresh", fresh
            assert fresh["policy_action"] == "continue", fresh
            assert fresh["snapshot_id"] == baseline[sibling], fresh

        assert_selected_contexts()
        confirm_event(endpoint, token, sibling, journal, "evt_while_stale", 1)
        worker.start_task(names[1], sibling, driver=driver)
        second_worker = worker.wait_status(sibling, names[1], "running")["pid"]
        assert second_worker > 0 and second_worker != first_worker
        assert worker.wait_status(sibling, names[0], "running")["pid"] == first_worker
        status, view = http_json("GET", endpoint + "/status", token=token, timeout=15.0)
        assert status == 200 and view["instance_id"] == instance, view
        assert_selected_contexts()
    finally:
        try:
            for name in names:
                worker.stop_if_running(sibling, name)
                worker.ensure_stopped(sibling, name)
        finally:
            runtime.stop_runtime(workplace)


def test_exited_runtime_cannot_supply_live_owner_identity():
    with subprocess.Popen([sys.executable, "-B", "-c", "pass"]) as child:
        if sys.platform.startswith("linux"):
            proc = Path(f"/proc/{child.pid}/stat")
            deadline = time.monotonic() + 5
            while proc.read_text(encoding="ascii").rsplit(")", 1)[1].split()[0] != "Z":
                assert time.monotonic() < deadline, "child did not exit"
                time.sleep(0.01)
        else:
            child.wait(timeout=5)
        assert runtime_process_identity(child.pid) is None
