"""Exercise online migration against one actual Runtime and two project journals."""

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
from contextlib import closing, contextmanager
from pathlib import Path
from queue import Empty, Queue
from typing import Any

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
from pathlib import Path

tool, held, release, *arguments = sys.argv[1:]
entry = runpy.run_path(tool)
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.storage_migration import StorageMigrationService

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
    apply_target = StorageMigrationService._apply_target
    def crash_after_apply(self, *args, **kwargs):
        apply_target(self, *args, **kwargs)
        os._exit(77)
    StorageMigrationService._apply_target = crash_after_apply
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
        status, response = request_event(endpoint, token, project, event_id, number)
        assert status == 200 and response.get("event_id") == event_id, response
        assert response.get("duplicate") is False, response
        record = journal.get(project / EVENT_PATH, event_id)
        assert record is not None and record["data"] == {
            "value": number,
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
    assert event_id.startswith("evt_live_append_"), summary
    journal = ProcessEventRecorder().event_journal_for_project(sibling, workplace)
    assert journal.get(sibling / EVENT_PATH, event_id) is not None


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
    runtime.start_runtime(workplace)
    try:
        initial = runtime.service_state(workplace)
        instance = initial["instance_id"]
        endpoint = str(initial["endpoint"]).rstrip("/")
        token = runtime.token(workplace)
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
                    # Finish its last write before deliberately triggering a
                    # second observation of B's own journal in the compound tick.
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
                    blocked, continuing = tick["projects"]
                    assert blocked["storage_error"]["retryable"] is True
                    assert (
                        continuing["inspector"] == "tick"
                        and "storage_error" not in continuing
                    )
                    assert continuing["inspector_result"]["failed"] == 0
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
        status, reply = request_event(endpoint, token, project, "evt_after_ready", 2)
        assert status == 200 and reply["duplicate"] is False, reply
        a = ProcessEventRecorder().event_journal_for_project(project, workplace)
        assert a.get(project / EVENT_PATH, "evt_refused") is None
        assert a.get(project / EVENT_PATH, "evt_refused_during_recovery") is None
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
        # Cross-check both ID uniqueness and the exact committed payload for each ack.
        for root, events in ((project, original), (sibling, observed)):
            with closing(sqlite3.connect(root / EVENT_PATH)) as sql:
                rows = sql.execute("SELECT event_id, record FROM events").fetchall()
            relevant = [
                (event_id, json.loads(body))
                for event_id, body in rows
                if event_id in events
            ]
            assert len(relevant) == len(events) and dict(relevant) == events
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
