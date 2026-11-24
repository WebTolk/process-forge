"""Prove selected journal admission and Runtime owner classification."""

from __future__ import annotations

import errno
import io
import json
import os
import runpy
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import patch

from processforge_core.maintenance import project_event_coordinator as online
from processforge_core.maintenance import project_event_maintenance as selected
from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.contracts import (
    MaintenanceError,
    MigrationSafety,
    StorageMigrationContext,
    StoreTarget,
)
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.runtime import execution_admission as registry
from processforge_core.runtime import process_identity
from processforge_core.runtime_service_state import (
    PROJECT_EVENT_MAINTENANCE_CAPABILITY,
    PROJECT_EVENT_RUNTIME_IDENTITY,
    runtime_process_identity,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

_SOURCE = Path(__file__).resolve().parents[2]
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_RELATIVE_TARGET = "runtime/events/events.sqlite3"
_REQUEST = {"kind": "events", "scope": "project"}
_BUSY = "storage_project_event_maintenance_busy"
_RUNTIME_UNKNOWN = "storage_project_event_runtime_unknown"
_CHILD = "import sys; print('ready', flush=True); sys.stdin.read()"
_GUARD_CHILD = """
import sys
from pathlib import Path
from processforge_core.runtime.execution_admission import registry_file_lock

with registry_file_lock(Path(sys.argv[1])):
    print('ready', flush=True)
    sys.stdin.read()
"""


@contextmanager
def _child(script: str, *args: str) -> Iterator[subprocess.Popen[str]]:
    env = dict(os.environ, PYTHONPATH=str(_SOURCE / "src"))
    with subprocess.Popen(
        [sys.executable, "-B", "-c", script, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        creationflags=_CREATE_NO_WINDOW,
        env=env,
    ) as child:
        try:
            assert child.stdout is not None
            with ThreadPoolExecutor(max_workers=1) as pool:
                line = pool.submit(child.stdout.readline)
                try:
                    assert line.result(timeout=10).strip() == "ready"
                except BaseException:
                    child.kill()
                    raise
            yield child
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)


def _stop(child: subprocess.Popen[str]) -> None:
    assert child.stdin is not None
    child.stdin.close()
    child.stdin = None
    child.wait(timeout=10)


def _marker(gate: Path) -> Path:
    return gate.with_name(f".{gate.name}.lock")


def _owner(pid: int, **overrides: Any) -> dict[str, Any]:
    return {
        "pid": pid,
        "host": socket.gethostname(),
        "token": "fixture-owner",
        "created_at": "2000-01-01T00:00:00Z",
        **overrides,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class ProjectEventAdmissionTests(unittest.TestCase):
    _cli: ClassVar[Callable[[list[str]], int]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.enterClassContext(patch.object(sys, "path", sys.path.copy()))
        native = sys.modules.get("pf_native_control")

        def restore_native() -> None:
            if native is None:
                sys.modules.pop("pf_native_control", None)
            else:
                sys.modules["pf_native_control"] = native

        cls.addClassCleanup(restore_native)
        entry = runpy.run_path(str(_SOURCE / "tools/migrate-storage.py"))
        cls._cli = entry["main"]

    def setUp(self) -> None:
        scratch = TemporaryDirectory(prefix="event-admission-")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.project = self.root / "project-a"
        self.sibling = self.root / "project-b"
        self.workplace = self.root / "workplace"
        self.flow = self.project / ".pf"
        self.device = self.root / "device.yaml"
        manifest = self.workplace / "workplace.yaml"
        _write(manifest, {"workplace": {"id": "world"}})
        for project in (self.project, self.sibling):
            _write(
                project / ".pf/process-forge.yaml", {"project": {"id": project.name}}
            )
            _write(
                project / ".pf/process-forge.local.yaml",
                {"workplace": {"manifest": str(manifest)}},
            )
        self.target = StoreTarget(
            "events",
            self.flow / _RELATIVE_TARGET,
            _RELATIVE_TARGET,
            "project",
            self.project.name,
        )
        self.gate = migration.storage_identity_gate(self.flow)
        self.intent = selected._intent(self.flow)
        self.context = StorageMigrationContext(
            self.project, self.workplace, self.device, (self.target,)
        )
        self._runtime(os.getpid())
        self.assertEqual(
            ProcessEventJournal().append_many(
                self.target.target,
                [
                    {
                        "event_id": "evt_original",
                        "event_type": "fixture.event",
                        "time": "2025-01-01T00:00:00Z",
                        "data": {"value": 7},
                    }
                ],
            ),
            1,
        )

    def _runtime(self, pid: int) -> None:
        digest = runtime_process_identity(pid)
        self.assertIsNotNone(digest)
        root = self.workplace / "runtime/pf-runtime"
        state = {"pid": pid, "instance_id": "fixture-instance"}
        _write(root / "runtime.lock", state)
        _write(
            root / "service.json",
            {
                **state,
                "status": "ready",
                "workplace_root": str(self.workplace),
                "capabilities": {PROJECT_EVENT_MAINTENANCE_CAPABILITY: 1},
                PROJECT_EVENT_RUNTIME_IDENTITY: digest,
            },
        )

    def _invoke(self, operation: str) -> tuple[int, dict[str, Any]]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = type(self)._cli(
                [
                    "--project-root",
                    str(self.project),
                    "--workplace-root",
                    str(self.workplace),
                    "--device-config",
                    str(self.device),
                    "--project-events",
                    f"--{operation}",
                    "--json",
                ]
            )
        return code, json.loads(output.getvalue())

    def _bound_target_wait(self) -> None:
        # Only the full wait for the contested target needs a short test budget.
        # Keep the CLI's ordinary deadlines for admission and plan publication.
        original = online.wait_registry_file_lock

        def bounded_wait(
            path: Path, *, deadline: float, stale_after_seconds: float
        ) -> AbstractContextManager[None]:
            if path == self.gate:
                deadline = min(deadline, time.monotonic() + 0.5)
            return original(
                path, deadline=deadline, stale_after_seconds=stale_after_seconds
            )

        self.enterContext(patch.object(online, "wait_registry_file_lock", bounded_wait))

    def _blocked(self, operation: str, code: str, *, retryable: bool) -> None:
        status, report = self._invoke(operation)
        self.assertEqual(status, 1, report)
        self.assertTrue(report["blocked"])
        self.assertEqual(report["error"], {"code": code})
        self.assertIs(report["retryable"], retryable)
        self.assertEqual(report["requested_target"], _REQUEST)
        self.assertEqual(
            report["selected_target"],
            {
                **_REQUEST,
                "owner_id": self.project.name,
                "target_relative_path": _RELATIVE_TARGET,
            },
        )

    def _pending(self) -> tuple[Path, bytes]:
        with patch.object(
            online._Coordinator,
            "create_backup",
            side_effect=MaintenanceError("fixture_interrupted_backup"),
        ):
            self._blocked("apply", "fixture_interrupted_backup", retryable=False)
        selector = migration.StorageMigrationService._selector(self.flow, self.target)
        return selector, selector.read_bytes()

    def _service(self) -> migration.StorageMigrationService:
        return migration.StorageMigrationService(
            backup=selected.ProjectEventBackupService(),
            admission=registry.ExecutionAdmission(),
            registry_lock=selected.selected_storage_lock,
            safety=lambda _: MigrationSafety("unknown", "", ()),
        )

    def test_one_shot_and_real_os_contention(self) -> None:
        owner = registry.prepare_registry_owner()
        for hold, result in (
            (_child(_GUARD_CHILD, str(self.gate)), "guard_busy"),
            (None, "owner_marker"),
        ):
            with self.subTest(result=result):
                with (
                    patch.object(
                        registry,
                        "_registry_lock_read_owner",
                        side_effect=AssertionError,
                    ),
                    patch.object(
                        registry,
                        "_selected_registry_owner_alive",
                        side_effect=AssertionError,
                    ),
                    patch.object(
                        registry, "_registry_lock_stale", side_effect=AssertionError
                    ),
                    patch.object(
                        registry, "_registry_guard_signal", side_effect=AssertionError
                    ),
                    patch.object(
                        registry, "prepare_registry_owner", side_effect=AssertionError
                    ),
                    patch.object(registry, "time") as clock,
                    patch.object(
                        registry,
                        "_registry_lock_try_os_lock",
                        wraps=registry._registry_lock_try_os_lock,
                    ) as os_try,
                    patch.object(
                        registry,
                        "_registry_create_marker",
                        wraps=registry._registry_create_marker,
                    ) as create,
                ):
                    if hold is not None:
                        with (
                            hold,
                            registry.try_registry_file_lock(
                                self.gate, owner=owner
                            ) as acquired,
                        ):
                            self.assertEqual(acquired, result)
                        create.assert_not_called()
                    else:
                        self.gate.parent.mkdir(parents=True, exist_ok=True)
                        _marker(self.gate).write_bytes(b"malformed")
                        with registry.try_registry_file_lock(
                            self.gate, owner=owner
                        ) as acquired:
                            self.assertEqual(acquired, result)
                        create.assert_called_once_with(_marker(self.gate))
                    os_try.assert_called_once()
                    clock.sleep.assert_not_called()

    def test_full_probe_releases_workplace_and_project_admission(self) -> None:
        service = self._service()
        entered, release = threading.Event(), threading.Event()
        original = registry._selected_registry_owner_alive

        def hold(owner: dict[str, Any]) -> bool | None:
            self.assertFalse(registry.ExecutionAdmission.held(None, self.workplace))
            self.assertFalse(registry.ExecutionAdmission.held(self.project, None))
            entered.set()
            self.assertTrue(release.wait(10))
            return original(owner)

        def a() -> None:
            with (
                selected._bind_selected_target(self.gate, self.workplace),
                service._admitted_gate(self.context, self.flow, time.monotonic() + 12),
            ):
                self.assertTrue(
                    registry.ExecutionAdmission.held(self.project, self.workplace)
                )

        def b() -> None:
            with registry.ExecutionAdmission().start(self.sibling, self.workplace):
                self.assertTrue(
                    registry.ExecutionAdmission.held(self.sibling, self.workplace)
                )
                (self.sibling / "completed").touch()

        with _child(_CHILD) as owner:
            _stop(owner)
            _write(_marker(self.gate), _owner(owner.pid))
            with (
                patch.object(registry, "_selected_registry_owner_alive", hold),
                ThreadPoolExecutor(max_workers=2) as pool,
            ):
                future_a = pool.submit(a)
                try:
                    self.assertTrue(entered.wait(10))
                    pool.submit(b).result(timeout=5)
                    self.assertTrue((self.sibling / "completed").is_file())
                    self.assertFalse(future_a.done())
                finally:
                    release.set()
                future_a.result(timeout=10)
            self.assertFalse(_marker(self.gate).exists())

    def test_millisecond_floor_and_inherited_admission(self) -> None:
        _write(_marker(self.gate), _owner(os.getpid(), host="remote.invalid"))
        service = self._service()
        with selected._bind_selected_target(self.gate, self.workplace):
            with (
                self.assertRaisesRegex(
                    MaintenanceError, "storage_project_event_target_owner_unknown"
                ),
                selected.selected_storage_lock(self.gate, timeout_seconds=0.001),
            ):
                self.fail("unexpected target acquisition")
            with (
                registry.ExecutionAdmission().start(self.project, self.workplace),
                patch.object(
                    registry, "_registry_lock_read_owner", side_effect=AssertionError
                ),
                patch.object(
                    selected, "wait_registry_file_lock", side_effect=AssertionError
                ),
                self.assertRaisesRegex(MaintenanceError, "storage_activity_unknown"),
                service._admitted_gate(self.context, self.flow, None),
            ):
                self.fail("unexpected target acquisition")

    def test_timeout_retains_assessment_when_probe_uses_remaining_budget(self) -> None:
        marker = _marker(self.gate)
        _write(marker, _owner(os.getpid()))
        fake_time = 20.0

        def probe(owner: dict[str, Any]) -> bool:
            nonlocal fake_time
            self.assertEqual(owner["token"], "fixture-owner")
            fake_time += 1
            return True

        def replace_marker() -> None:
            _write(marker, _owner(os.getpid(), host="changed.invalid"))

        with (
            patch.object(registry.time, "monotonic", side_effect=lambda: fake_time),
            patch.object(registry, "_selected_registry_owner_alive", probe),
            self.assertRaises(registry.RegistryLockTimeout) as caught,
            registry.wait_registry_file_lock(
                self.gate, deadline=20.5, on_contention=replace_marker
            ),
        ):
            self.fail("unexpected target acquisition")
        self.assertEqual(
            (caught.exception.phase, caught.exception.assessment),
            ("owner", "owner_live"),
        )
        self.assertEqual(json.loads(marker.read_bytes())["host"], "changed.invalid")

    def test_public_refuses_project_only_admission_before_waiting(self) -> None:
        self._pending()
        with (
            registry.ExecutionAdmission().project(self.project),
            patch.object(
                online, "project_event_operation_intent", side_effect=AssertionError
            ) as intent,
            patch.object(
                registry.ExecutionAdmission, "start", side_effect=AssertionError
            ) as start,
        ):
            self.assertTrue(registry.ExecutionAdmission.held(self.project, None))
            self.assertFalse(registry.ExecutionAdmission.held(None, self.workplace))
            for operation in ("apply", "resume"):
                with self.subTest(operation=operation):
                    self._blocked(operation, "storage_activity_unknown", retryable=True)
        intent.assert_not_called()
        start.assert_not_called()

    def test_public_rendering_uses_attempt_assessment(self) -> None:
        self._pending()
        self._bound_target_wait()
        for gate in (self.intent, self.gate):
            owner = selected if gate == self.intent else online
            original = owner.wait_registry_file_lock

            @contextmanager
            def change_marker_after_wait(path: Path, **options: Any) -> Iterator[None]:
                try:
                    with original(path, **options):
                        yield
                except registry.RegistryLockTimeout:
                    _write(_marker(path), _owner(os.getpid(), host="changed.invalid"))
                    raise

            marker = _marker(gate)
            _write(marker, _owner(os.getpid()))
            with (
                self.subTest(gate=gate.name),
                patch.object(
                    owner, "wait_registry_file_lock", change_marker_after_wait
                ),
            ):
                self._blocked("resume", _BUSY, retryable=True)
                self.assertEqual(
                    json.loads(marker.read_bytes())["host"], "changed.invalid"
                )
            marker.unlink()

    def test_expired_retry_retains_only_the_same_owner_observation(self) -> None:
        self._pending()
        original_open = Path.open
        owner = _owner(os.getpid())
        for gate, unknown in (
            (self.intent, "storage_project_event_intent_unknown"),
            (self.gate, "storage_project_event_target_owner_unknown"),
        ):
            marker = _marker(gate)
            for replacement in (
                None,
                {**owner, "host": "changed.invalid"},
                {**owner, "pid": float(owner["pid"])},
            ):
                _write(marker, owner)
                now = 0.0

                def open_marker(
                    path: Path, mode: str = "r", *args: Any, **kwargs: Any
                ) -> Any:
                    nonlocal now
                    if path == marker and mode in {"r", "rb"} and now:
                        now = 2.0
                        if replacement is not None:
                            _write(marker, replacement)
                    return original_open(path, mode, *args, **kwargs)

                def sleep(delay: float) -> None:
                    nonlocal now
                    now += delay

                with (
                    self.subTest(gate=gate.name, replacement=replacement),
                    self._fixed_lock_deadline(gate),
                    patch.object(registry, "time", wraps=time) as clock,
                    patch.object(Path, "open", open_marker),
                    patch.object(
                        registry,
                        "_selected_registry_owner_alive",
                        wraps=registry._selected_registry_owner_alive,
                    ) as probe,
                ):
                    clock.monotonic.side_effect = lambda: now
                    clock.sleep.side_effect = sleep
                    self._blocked(
                        "resume",
                        _BUSY if replacement is None else unknown,
                        retryable=replacement is None,
                    )
                    probe.assert_called_once_with(owner)
            marker.unlink()

    def _fixed_lock_deadline(
        self, gate: Path, *, timeouts: list[registry.RegistryLockTimeout] | None = None
    ) -> AbstractContextManager[Any]:
        owner = selected if gate == self.intent else online
        original = owner.wait_registry_file_lock

        @contextmanager
        def fixed_wait(path: Path, **options: Any) -> Iterator[None]:
            if path == gate:
                options["deadline"] = 1.0
            try:
                with original(path, **options):
                    yield
            except registry.RegistryLockTimeout as error:
                if path == gate and timeouts is not None:
                    timeouts.append(error)
                raise

        return patch.object(owner, "wait_registry_file_lock", fixed_wait)

    def test_public_death_proven_after_deadline_preserves_marker(self) -> None:
        self._pending()
        original_probe = registry._selected_registry_owner_alive
        with _child(_CHILD) as child:
            _stop(child)
            owner = _owner(child.pid)
            for gate in (self.intent, self.gate):
                marker = _marker(gate)
                _write(marker, owner)
                initial = marker.read_bytes()
                now = 0.0
                timeouts: list[registry.RegistryLockTimeout] = []

                def probe(observed: dict[str, Any]) -> bool:
                    nonlocal now
                    self.assertIs(original_probe(observed), False)
                    now = 2.0
                    return False

                with (
                    self.subTest(gate=gate.name),
                    self._fixed_lock_deadline(gate, timeouts=timeouts),
                    patch.object(registry, "time", wraps=time) as clock,
                    patch.object(registry, "_selected_registry_owner_alive", probe),
                ):
                    clock.monotonic.side_effect = lambda: now
                    self._blocked("resume", "storage_deadline_exceeded", retryable=True)
                    self.assertEqual(
                        [(error.phase, error.assessment) for error in timeouts],
                        [("owner", "owner_dead")],
                    )
                    self.assertEqual(marker.read_bytes(), initial)
                marker.unlink()

    def test_expired_full_wait_unwinds_without_entering(self) -> None:
        owner = registry.prepare_registry_owner()
        original_lock = registry._registry_lock_try_os_lock
        original_fsync = os.fsync
        for boundary in ("entry", "acquisition", "publication"):
            gate = self.flow / "locks" / boundary
            now = 1.0 if boundary == "entry" else 0.0

            def lock(fd: int) -> bool:
                nonlocal now
                locked = original_lock(fd)
                self.assertTrue(locked)
                if boundary == "acquisition":
                    now = 1.0
                return locked

            def fsync(fd: int) -> None:
                nonlocal now
                original_fsync(fd)
                if boundary == "publication":
                    now = 1.0

            with self.subTest(boundary=boundary):
                with (
                    patch.object(registry, "time", wraps=time) as clock,
                    patch.object(registry, "_registry_lock_try_os_lock", lock),
                    patch.object(os, "fsync", side_effect=fsync) as sync,
                    self.assertRaises(registry.RegistryLockTimeout) as caught,
                ):
                    clock.monotonic.side_effect = lambda: now
                    with registry.wait_registry_file_lock(gate, deadline=1.0):
                        self.fail("unexpected lease after deadline")
                self.assertEqual(caught.exception.assessment, "deadline_expired")
                self.assertEqual(sync.call_count, int(boundary == "publication"))
                self.assertFalse(_marker(gate).exists())
                if boundary == "entry":
                    self.assertFalse(gate.parent.exists())
                with registry.try_registry_file_lock(gate, owner=owner) as acquired:
                    self.assertEqual(acquired, "acquired")

    def test_unreadable_or_disappeared_marker_evidence(self) -> None:
        marker = _marker(self.gate)
        _write(marker, _owner(os.getpid()))
        original = Path.open
        for cause in (PermissionError, FileNotFoundError):

            def unavailable(
                path: Path, mode: str = "r", *args: Any, **kwargs: Any
            ) -> Any:
                if path == marker and mode in {"r", "rb"}:
                    raise cause()
                return original(path, mode, *args, **kwargs)

            with (
                self.subTest(cause=cause),
                patch.object(Path, "open", unavailable),
                self.assertRaises(registry.RegistryLockTimeout) as caught,
                registry.wait_registry_file_lock(
                    self.gate, deadline=time.monotonic() + 0.02
                ),
            ):
                self.fail("unexpected target acquisition")
            self.assertEqual(caught.exception.assessment, "owner_unknown")
            self.assertTrue(marker.is_file())

    def test_backend_and_marker_publication_failures(self) -> None:
        fd = os.open(self.target.target, os.O_RDONLY)
        os.close(fd)
        with self.assertRaises(OSError) as invalid_descriptor:
            registry._registry_lock_try_os_lock(fd)
        self.assertEqual(invalid_descriptor.exception.errno, errno.EBADF)
        owner = registry.prepare_registry_owner()
        for name in ("_registry_lock_try_os_lock", "_registry_create_marker"):
            with (
                self.subTest(name=name),
                patch.object(registry, name, side_effect=OSError(errno.EIO, "fixture")),
                self.assertRaises(OSError) as caught,
                registry.try_registry_file_lock(self.gate, owner=owner),
            ):
                self.fail("unexpected target acquisition")
            self.assertEqual(caught.exception.errno, errno.EIO)
        with (
            patch.object(
                registry,
                "_registry_lock_try_os_lock",
                side_effect=OSError(errno.EIO, "fixture"),
            ),
            self.assertRaises(OSError) as full_wait,
            registry.wait_registry_file_lock(self.gate, deadline=time.monotonic() + 1),
        ):
            self.fail("unexpected target acquisition")
        self.assertEqual(full_wait.exception.errno, errno.EIO)
        with (
            patch.object(
                registry.os, "fsync", side_effect=OSError(errno.EIO, "fixture")
            ),
            self.assertRaises(OSError),
            registry.try_registry_file_lock(self.gate, owner=owner),
        ):
            self.fail("unexpected target acquisition")
        self.assertFalse(_marker(self.gate).exists())
        with registry.try_registry_file_lock(self.gate, owner=owner) as acquired:
            self.assertEqual(acquired, "acquired")

    def test_public_apply_and_resume_report_guards_and_marker_ownership(self) -> None:
        self._pending()
        elapsed = 0.0
        clock = self.enterContext(patch.object(registry, "time", wraps=time))
        clock.monotonic.side_effect = lambda: elapsed

        def advance(seconds: float) -> None:
            nonlocal elapsed
            elapsed += seconds

        clock.sleep.side_effect = advance
        owners = (
            ("live", _owner(os.getpid())),
            ("foreign", _owner(os.getpid(), host="foreign.invalid")),
            ("host", _owner(os.getpid(), host=123)),
            ("token", _owner(os.getpid(), token="  ")),
            ("pid", _owner(True)),
            ("birth", _owner(os.getpid(), linux_identity={})),
            ("invalid-json", None),
        )
        for gate, unknown in (
            (self.intent, "storage_project_event_intent_unknown"),
            (self.gate, "storage_project_event_target_owner_unknown"),
        ):
            self.enterContext(self._fixed_lock_deadline(gate))
            with _child(_GUARD_CHILD, str(gate)):
                for operation in ("apply", "resume"):
                    elapsed = 0.0
                    self._blocked(operation, _BUSY, retryable=True)
            for operation in ("apply", "resume"):
                for name, owner in owners:
                    with self.subTest(gate=gate.name, operation=operation, owner=name):
                        marker = _marker(gate)
                        if owner is None:
                            marker.write_bytes(b"incomplete")
                        else:
                            _write(marker, owner)
                        try:
                            elapsed = 0.0
                            self._blocked(
                                operation,
                                _BUSY if name == "live" else unknown,
                                retryable=name == "live",
                            )
                            self.assertTrue(marker.is_file())
                        finally:
                            marker.unlink(missing_ok=True)

    def test_public_reclaims_dead_markers_and_resumes_same_plan(self) -> None:
        selector, initial = self._pending()
        pin_path = self.flow / "data/storage-identities.json"
        pending = json.loads(pin_path.read_bytes())["slots"][0]
        self.assertEqual(pending["state"], "pending")
        plan_path = (
            migration.StorageMigrationService._journal(
                self.flow, pending["plan_checksum"]
            )
            / "plan.json"
        )
        self.assertEqual(plan_path.read_bytes(), initial)
        self.assertEqual(json.loads(initial)["migration_id"], online.MIGRATION_ID)
        self.assertEqual(
            json.loads(initial)["descriptor_checksum"],
            online._hash(online._online_descriptor()),
        )
        with _child(_CHILD) as owner:
            _stop(owner)
            for gate in (self.gate, self.intent):
                _write(_marker(gate), _owner(owner.pid))
            status, report = self._invoke("resume")
        self.assertEqual(status, 0, report)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(selector.read_bytes(), initial)
        self.assertEqual(plan_path.read_bytes(), initial)
        ready = json.loads(pin_path.read_bytes())["slots"][0]
        self.assertEqual(ready["state"], "ready")
        for key in ("store_id", "plan_checksum"):
            self.assertEqual(ready[key], pending[key])
        self.assertFalse(_marker(self.gate).exists())
        self.assertFalse(_marker(self.intent).exists())

    def test_public_owner_selected_by_host_remains_pinned(self) -> None:
        manifest = self.flow / "process-forge.yaml"
        original = manifest.read_bytes()
        selector = migration.StorageMigrationService._selector(self.flow, self.target)
        pin = self.flow / "data/storage-identities.json"
        run = online.run_online_project_event_migration

        def change_binding(**options: Any) -> dict[str, Any]:
            _write(manifest, {"project": {"id": "replacement-owner"}})
            return run(**options)

        def evidence() -> dict[Path, bytes]:
            return {
                path: path.read_bytes() for path in (selector, pin) if path.is_file()
            }

        for operation in ("apply", "resume"):
            with self.subTest(operation=operation):
                if operation == "resume":
                    self._pending()
                previous = evidence()
                try:
                    with patch.object(
                        online, "run_online_project_event_migration", change_binding
                    ):
                        self._blocked(
                            operation, "storage_enrollment_conflict", retryable=False
                        )
                    self.assertEqual(evidence(), previous)
                finally:
                    manifest.write_bytes(original)

    def test_public_unimported_history_refuses_before_publication(self) -> None:
        code = "storage_project_event_import_required"
        path = self.target.target.with_suffix(".ndjson")
        source = path.with_name("fixture-history")
        _write(
            source,
            {
                "event_id": "evt_legacy",
                "event_type": "fixture.event",
                "time": "2025-01-01T00:00:00Z",
                "data": {"original": True},
            },
        )
        with closing(sqlite3.connect(self.target.target)) as connection, connection:
            connection.execute(
                "DELETE FROM journal_metadata WHERE key='legacy_imported'"
            )

        source.rename(path)
        self._blocked("apply", code, retryable=False)
        path.rename(source)
        selector = migration.StorageMigrationService._selector(self.flow, self.target)
        self.assertFalse(selector.exists())

        authorize = online._Coordinator.authorize

        def add_history_at_publication(coordinator: online._Coordinator) -> None:
            authorize(coordinator)
            source.rename(path)

        with patch.object(online._Coordinator, "authorize", add_history_at_publication):
            self._blocked("apply", code, retryable=False)
        self.assertFalse(selector.exists())
        path.rename(source)

        selector, plan = self._pending()
        pin = self.flow / "data/storage-identities.json"
        identity = pin.read_bytes()
        source.rename(path)
        self._blocked("resume", code, retryable=False)
        self.assertEqual(selector.read_bytes(), plan)
        self.assertEqual(pin.read_bytes(), identity)

    def test_public_runtime_capability_and_missing_plan_refusals(self) -> None:
        self._blocked("resume", "storage_project_event_plan_missing", retryable=False)
        control = self.workplace / "runtime/pf-runtime/service.json"
        state = json.loads(control.read_bytes())
        state["capabilities"] = {}
        _write(control, state)
        for operation in ("apply", "resume"):
            self._blocked(
                operation, "storage_project_event_runtime_unsupported", retryable=False
            )

    @unittest.skipUnless(sys.platform == "win32", "native Windows required")
    def test_windows_exited_runtime_with_handle_retained(self) -> None:
        with _child(_CHILD) as child:
            self._runtime(child.pid)
            selected.require_compatible_runtime(self.workplace)
            _stop(child)
            for operation in ("apply", "resume"):
                self._blocked(operation, _RUNTIME_UNKNOWN, retryable=True)

    def test_linux_parser_accepts_only_positive_live_states(self) -> None:
        pid = 1455
        for state in ("R", "S", "D", "T", "t", "P", "I", "Z", "X", "x", "?", "bad"):
            stat = f"{pid} (comm with ) space) {state} " + "0 " * 18 + "123456"
            with (
                self.subTest(state=state),
                patch.object(
                    Path,
                    "read_text",
                    side_effect=("fixture-boot", stat, "fixture-boot", stat),
                ),
            ):
                birth = process_identity._linux_identity(pid, "fixture-host", None)
                live = process_identity._linux_identity(
                    pid, "fixture-host", None, require_running=True
                )
            self.assertIsNotNone(birth)
            self.assertEqual(
                live, birth if state in {"R", "S", "D", "T", "t", "P", "I"} else None
            )

    @unittest.skipUnless(sys.platform.startswith("linux"), "native Linux required")
    def test_linux_unknown_state_and_unreaped_runtime(self) -> None:
        with _child(_CHILD) as child:
            self._runtime(child.pid)
            selected.require_compatible_runtime(self.workplace)
            stat = Path(f"/proc/{child.pid}/stat")
            original = Path.read_text

            def unknown_state(path: Path, *args: Any, **kwargs: Any) -> str:
                raw = original(path, *args, **kwargs)
                if path == stat:
                    state = raw.rindex(")") + 2
                    return raw[:state] + "?" + raw[state + 1 :]
                return raw

            with patch.object(Path, "read_text", unknown_state):
                self.assertIsNotNone(process_identity.capture_process(child.pid))
                for operation in ("apply", "resume"):
                    self._blocked(operation, _RUNTIME_UNKNOWN, retryable=True)

            assert child.stdin is not None
            child.stdin.close()
            child.stdin = None
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                raw = stat.read_text(encoding="ascii")
                if raw[raw.rindex(")") + 2] == "Z":
                    break
                time.sleep(0.01)
            else:
                self.fail("child did not reach zombie state before reaping")
            for operation in ("apply", "resume"):
                self._blocked(operation, _RUNTIME_UNKNOWN, retryable=True)
