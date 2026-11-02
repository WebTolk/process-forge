"""Real journal scans, SQLite change witnesses and physical admission isolation."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.runtime.execution_admission import (
    ExecutionAdmission,
    registry_file_lock,
)

from .test_storage_uuid import StorageHarness


@pytest.fixture
def storage(tmp_path: Path) -> StorageHarness:
    fixture = StorageHarness(tmp_path / "storage")
    (fixture.workplace / "workplace.yaml").write_text(
        "id: fixture-workplace\n", encoding="utf-8"
    )
    fixture.context = replace(fixture.context, workplace_root=fixture.workplace)

    @contextmanager
    def physical_lock(
        path: Path, *, timeout_seconds: float, stale_after_seconds: float
    ) -> Iterator[None]:
        with registry_file_lock(
            path,
            timeout_seconds=timeout_seconds,
            stale_after_seconds=stale_after_seconds,
        ):
            fixture.gates.append(path.name)
            try:
                yield
            finally:
                assert fixture.gates.pop() == path.name

    fixture.service.registry_lock = physical_lock
    fixture.service.admission = ExecutionAdmission(physical_lock)
    return fixture


def independent_admission(storage: StorageHarness) -> None:
    candidate = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(candidate / "src"), str(candidate / "tools")]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys,time
from pathlib import Path
from processforge_core.runtime.execution_admission import ExecutionAdmission
with ExecutionAdmission().start(Path(sys.argv[1]),Path(sys.argv[2]),deadline=time.monotonic()+.5):
    print('independent-admission')
""",
            str(storage.project),
            str(storage.workplace),
        ],
        cwd=candidate,
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "independent-admission"


def seed_history(storage: StorageHarness) -> None:
    storage.create()
    with sqlite3.connect(storage.target.target) as connection:
        for index in range(4096):
            event_id = f"history-{index}"
            connection.execute(
                "INSERT INTO admissions VALUES(?,?,?)", (index + 2, event_id, "opaque")
            )
            connection.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    index + 2,
                    event_id,
                    "fixture.history",
                    "",
                    "",
                    "",
                    "",
                    "",
                    json.dumps({"event_id": event_id, "body": "x" * 4096}),
                ),
            )


@pytest.mark.parametrize("state", ["unknown", "active"])
def test_ordinary_large_legacy_write_defers_before_any_history_scan(
    storage: StorageHarness, monkeypatch: pytest.MonkeyPatch, state: Any
) -> None:
    seed_history(storage)
    storage.state = state
    monkeypatch.setattr(
        migration,
        "_parity",
        lambda *_: pytest.fail("ordinary deferred write scanned historical rows"),
    )
    host = migration.StorageMigrationHost(
        storage.context, storage.service, _automatic=True
    )
    journal = ProcessEventJournal(storage_host=host)
    assert journal.append(storage.target.target, {"event_id": "ordinary-new-event"})
    assert journal.contains(storage.target.target, "ordinary-new-event")
    assert not storage.slot
    assert not (storage.owner / "maintenance/storage-migrations").exists()


@pytest.mark.parametrize("new_store", [False, True])
def test_real_proven_integrity_and_parity_run_outside_global_admission(
    storage: StorageHarness, monkeypatch: pytest.MonkeyPatch, new_store: bool
) -> None:
    if not new_store:
        storage.create()
    original = migration._parity
    calls: list[int] = []

    def checked(
        connection: sqlite3.Connection, deadline: float | None
    ) -> dict[str, Any]:
        assert not migration._admission_held(storage.context)
        if not calls:
            independent_admission(storage)
        result = original(connection, deadline)
        calls.append(len(result))
        return result

    monkeypatch.setattr(migration, "_parity", checked)
    if new_store:
        with storage.service.new_store_identity(
            storage.context, storage.target
        ) as identity:
            assert identity is not None
            storage.create()
            with sqlite3.connect(storage.target.target) as connection:
                connection.execute("BEGIN IMMEDIATE")
                migration.add_store_identity(connection, storage.target, identity)
    else:
        assert storage.ensure()["status"] == "ready"
    assert calls and storage.slot["state"] == "ready"


def test_scan_witness_detects_wal_only_commit_after_read_transaction_ends(
    storage: StorageHarness,
) -> None:
    storage.create()
    descriptor = migration._descriptor()
    with storage.service._scan_target(
        storage.context, storage.owner, storage.target, descriptor, None
    ) as scan:
        assert not scan.connection.in_transaction
        original_main_file = storage.target.target.read_bytes()
        with sqlite3.connect(storage.target.target, isolation_level=None) as writer:
            writer.execute("UPDATE admissions SET payload_hash='changed-in-wal'")
            assert storage.target.target.read_bytes() == original_main_file
            with storage.service._admitted_gate(storage.context, storage.owner, None):
                with pytest.raises(MaintenanceError, match="storage_source_changed"):
                    scan.revalidate(descriptor, None)
    assert not storage.slot


@pytest.mark.parametrize("phase", ["source", "final"])
def test_changed_scan_never_publishes_plan_or_ready(
    storage: StorageHarness, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    storage.create()
    original = storage.service._scan_target
    count = 0

    @contextmanager
    def changed(*args: Any, **kwargs: Any) -> Iterator[Any]:
        nonlocal count
        with original(*args, **kwargs) as scan:
            count += 1
            if count == (1 if phase == "source" else 2):
                assert not scan.connection.in_transaction
                with sqlite3.connect(storage.target.target) as writer:
                    writer.execute(
                        "UPDATE admissions SET payload_hash='concurrent-change'"
                    )
            yield scan

    monkeypatch.setattr(storage.service, "_scan_target", changed)
    result = storage.ensure()
    assert result["blocked"] and result["error"]["code"] == "storage_source_changed"
    if phase == "source":
        assert not storage.slot
    else:
        assert storage.slot["state"] == "pending"
        identity = storage.slot["store_id"]
        assert storage.service.resume(storage.context)["blocked"]
        assert (
            storage.slot["state"] == "pending" and storage.slot["store_id"] == identity
        )


def test_changed_physical_path_cannot_use_old_open_connection(
    storage: StorageHarness,
) -> None:
    storage.create()
    descriptor = migration._descriptor()
    path = storage.target.target
    try:
        with storage.service._scan_target(
            storage.context, storage.owner, storage.target, descriptor, None
        ) as scan:
            replacement = path.with_name("replacement.sqlite3")
            replacement.write_bytes(path.read_bytes())
            try:
                os.replace(replacement, path)
            except PermissionError:
                # Windows may enforce the stronger physical exclusion at the open
                # SQLite handle itself; the original identity must remain intact.
                assert (
                    path.stat().st_dev,
                    path.stat().st_ino,
                ) == scan.physical_identity
                return
            with storage.service._admitted_gate(storage.context, storage.owner, None):
                scan.revalidate(descriptor, None)
    except MaintenanceError as error:
        assert error.code in {"storage_source_changed", "storage_target_changed"}
    else:
        pytest.fail("replaced physical path reused an old open connection")


@pytest.mark.parametrize("state", ["unknown", "proven"])
def test_inherited_global_gate_never_starts_a_proven_history_scan(
    storage: StorageHarness, monkeypatch: pytest.MonkeyPatch, state: Any
) -> None:
    storage.create()
    storage.state = state
    monkeypatch.setattr(
        migration,
        "_parity",
        lambda *_: pytest.fail("inherited admission scanned history"),
    )
    with storage.service.admission.start(storage.project, storage.workplace):
        result = storage.ensure()
    assert result["blocked"] and not storage.slot
    if state == "unknown":
        assert result["targets"][0]["legacy_allowed"] is True
    else:
        assert result["error"]["code"] == "storage_activity_unknown"
        assert not result["targets"]


def test_busy_target_wait_releases_global_and_inherited_busy_refuses(
    storage: StorageHarness,
) -> None:
    entered, release, waiting = threading.Event(), threading.Event(), threading.Event()
    errors: list[BaseException] = []
    original_lock = storage.service.registry_lock

    @contextmanager
    def watched(path: Path, **kwargs: Any) -> Iterator[Any]:
        if path.name == "storage-identity" and kwargs.get("timeout_seconds") == 0.001:
            waiting.set()
        with original_lock(path, **kwargs) as held:
            yield held

    storage.service.registry_lock = watched

    def holder() -> None:
        try:
            with storage.service._gate(storage.owner, None):
                entered.set()
                assert release.wait(timeout=10)
        except BaseException as error:
            errors.append(error)

    def competitor() -> None:
        try:
            with storage.service._admitted_gate(
                storage.context, storage.owner, time.monotonic() + 5
            ):
                pass
        except BaseException as error:
            errors.append(error)

    held_thread, competing_thread = (
        threading.Thread(target=holder),
        threading.Thread(target=competitor),
    )
    held_thread.start()
    assert entered.wait(timeout=5)
    competing_thread.start()
    try:
        assert waiting.wait(timeout=5)
        independent_admission(storage)
        before = time.monotonic()
        with storage.service.admission.start(storage.project, storage.workplace):
            with pytest.raises(MaintenanceError, match="storage_activity_unknown"):
                with storage.service._admitted_gate(
                    storage.context, storage.owner, None
                ):
                    pytest.fail("inherited global admission acquired a busy target")
        assert time.monotonic() - before < 1
    finally:
        release.set()
        held_thread.join(timeout=10)
        competing_thread.join(timeout=10)
    assert not held_thread.is_alive() and not competing_thread.is_alive()
    assert not errors, errors


def test_inherited_adapter_access_refuses_busy_target_without_long_global_wait(
    storage: StorageHarness,
) -> None:
    storage.create()
    entered, release = threading.Event(), threading.Event()
    errors: list[BaseException] = []

    def holder() -> None:
        try:
            with storage.service._gate(storage.owner, None):
                entered.set()
                assert release.wait(timeout=10)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=holder)
    thread.start()
    assert entered.wait(timeout=5)
    try:
        before = time.monotonic()
        with storage.service.admission.start(storage.project, storage.workplace):
            with pytest.raises(MaintenanceError, match="storage_activity_unknown"):
                with migration.storage_identity_access(
                    storage.context,
                    storage.target,
                    registry_lock=storage.service.registry_lock,
                ):
                    pytest.fail("inherited adapter admission acquired a busy target")
        assert time.monotonic() - before < 1
        independent_admission(storage)
    finally:
        release.set()
        thread.join(timeout=10)
    assert not thread.is_alive()
    assert not errors, errors
