"""Native SQLite and guard coverage for isolated selected online migration."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Literal
from unittest.mock import patch

from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.maintenance import project_event_coordinator as online
from processforge_core.maintenance import storage_migration as v1
from processforge_core.maintenance.contracts import JsonObject, StoreTarget
from processforge_core.maintenance.execution_migration import _hash
from processforge_core.maintenance.project_event_owner import (
    project_event_binding_path,
    project_event_binding_writer_guard,
)
from processforge_core.process_event_journal import (
    APPLICATION_ID,
    SCHEMA,
    ProcessEventJournal,
)
from processforge_core.runtime import execution_admission
from processforge_core.runtime.execution_admission import ExecutionAdmission
from processforge_core.runtime_service_state import (
    PROJECT_EVENT_MAINTENANCE_CAPABILITY,
    PROJECT_EVENT_RUNTIME_IDENTITY,
    runtime_process_identity,
)

SOURCE = Path(__file__).resolve().parents[2]
_RELATIVE = "runtime/events/events.sqlite3"
_ORIGINAL = {
    "event_id": "first",
    "event_type": "log",
    "data": {"text": "é/ё", "value": 7},
}
_NEW = {"event_id": "second", "event_type": "log", "data": {"text": "after ready"}}

# Use the real producer's host and frozen transform. Only the interruption
# boundary is injected. The child creates its own selector, journal and pin.
_V1_PRODUCER = """
import os
import sys
from pathlib import Path

source, project, workplace, device = map(Path, sys.argv[1:5])
selected = sys.argv[5] == "selected"
checkpoint = sys.argv[6]
sys.path[:0] = [str(source / "src"), str(source / "tools"), str(source)]
from processforge_core.composition import build_storage_migration_host
from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.maintenance import storage_migration as engine

kwargs = {"project_events_only": True} if selected else {"offline_confirmed": True}
host = build_storage_migration_host(
    project_root=project, workplace_root=workplace, device_config_path=device,
    configuration=ConfigurationProvider.pinned(PFConfig()), **kwargs,
)

def interrupt(*args, **kwargs):
    os._exit(77)

if checkpoint == "pending":
    engine.StorageMigrationService._apply_target = interrupt
elif checkpoint == "importing":
    engine.add_store_identity = interrupt
else:
    raise AssertionError(checkpoint)
if selected:
    from processforge_core.maintenance.project_event_maintenance import (
        run_project_event_migration,
    )
    print(run_project_event_migration(host, operation="apply", offline_confirmed=False))
else:
    context = host.context
    targets = engine.validate_storage_context(context)
    target = next(t for t in targets if t.scope == "project" and t.kind == "events")
    print(host.service._target(context, target, engine._descriptor(), None))
"""


class Interrupted(BaseException):
    """Leave the recoverable checkpoint in place while Python unwinds guards."""


class CoordinatorTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = self.enterContext(tempfile.TemporaryDirectory(prefix="pf-history-"))
        self.root = Path(scratch).resolve()
        self.project = self.root / "project-a"
        self.neighbor = self.root / "project-b"
        self.workplace = self.root / "workplace"
        self.device = self.root / "device.yaml"
        self.flow = self.project / ".pf"
        self.flow.mkdir(parents=True)
        (self.neighbor / ".pf").mkdir(parents=True)
        self.runtime = self.workplace / "runtime/pf-runtime"
        self.runtime.mkdir(parents=True)
        (self.workplace / "workplace.yaml").write_text(
            "workplace:\n  id: test-workplace\n", encoding="utf-8"
        )
        manifest = self.workplace / "workplace.yaml"
        enrollment = {"workplace": {"manifest": manifest.as_posix()}}
        self.write(self.flow / "process-forge.local.yaml", enrollment)
        self.set_owner("history-a")
        self.path = self.flow / _RELATIVE
        self.path.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA application_id=" + str(APPLICATION_ID))
            connection.execute("PRAGMA user_version=1")
            connection.execute(
                "CREATE TABLE journal_metadata("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            for statement in SCHEMA:
                connection.execute(statement)
            connection.executemany(
                "INSERT INTO journal_metadata VALUES (?, ?)",
                [("migration_state", "ready"), ("legacy_imported", "1")],
            )
            self.append(connection, _ORIGINAL)
        self.target = StoreTarget(
            "events", self.path, _RELATIVE, "project", "history-a"
        )
        self.selector = v1.StorageMigrationService._selector(self.flow, self.target)
        self.pins = self.flow / "data/storage-identities.json"
        self.config = ConfigurationProvider.pinned(PFConfig())
        self.publish_control()

    @staticmethod
    def write(path: Path, value: JsonObject) -> None:
        path.write_bytes((json.dumps(value, sort_keys=True) + "\n").encode())

    @staticmethod
    def append(connection: sqlite3.Connection, event: JsonObject) -> None:
        appended = ProcessEventJournal._append(
            connection, event, lambda record: record["event_id"], True
        )
        assert appended

    def publish_control(self) -> None:
        local_identity = runtime_process_identity(os.getpid())
        self.assertIsNotNone(local_identity)
        owner = {"pid": os.getpid(), "instance_id": "fixture-instance"}
        self.write(self.runtime / "runtime.lock", owner)
        self.write(
            self.runtime / "service.json",
            {
                **owner,
                "workplace_root": str(self.workplace),
                "status": "ready",
                "capabilities": {PROJECT_EVENT_MAINTENANCE_CAPABILITY: 1},
                PROJECT_EVENT_RUNTIME_IDENTITY: local_identity,
            },
        )

    def set_owner(self, owner: str) -> None:
        self.write(self.flow / "process-forge.yaml", {"project": {"id": owner}})

    def operation(
        self,
        operation: Literal["apply", "resume"] = "resume",
        *,
        configuration: ConfigurationProvider | None = None,
        deadline: float | None = None,
    ) -> JsonObject:
        return online.run_online_project_event_migration(
            project_root=self.project,
            workplace_root=self.workplace,
            device_config_path=self.device,
            configuration=self.config if configuration is None else configuration,
            operation=operation,
            deadline=deadline,
        )

    def produce_v1(self, producer: str, checkpoint: str) -> JsonObject:
        source = SOURCE
        source_variable = (
            "PF_TEST_RELEASED_V130_SOURCE"
            if producer == "released"
            else "PF_TEST_SELECTED_V1_SOURCE"
        )
        override = os.environ.get(source_variable)
        if override:
            source = Path(override).resolve(strict=True)
        if producer == "released":
            for name in ("runtime.lock", "service.json"):
                (self.runtime / name).unlink()
        args = [
            str(source),
            str(self.project),
            str(self.workplace),
            str(self.device),
            producer,
            checkpoint,
        ]
        result = subprocess.run(
            [sys.executable, "-B", "-c", _V1_PRODUCER, *args],
            cwd=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 77, result.stdout + result.stderr)
        self.publish_control()
        plan = json.loads(self.selector.read_bytes())
        self.assertEqual(plan["migration_id"], v1.MIGRATION_ID)
        self.assertEqual(self.slot()["state"], "pending")
        states = {"pending": "planned", "importing": "importing"}
        self.assertEqual(self.checkpoint(plan)["state"], states[checkpoint])
        self.assertEqual(self.identities(), [])
        self.assertEqual(self.events(), [_ORIGINAL])
        return plan

    def slot(self) -> JsonObject:
        return v1._slot(self.flow, self.target) or {}

    def directory(self, plan: JsonObject) -> Path:
        return v1.StorageMigrationService._journal(self.flow, plan["plan_checksum"])

    def checkpoint(self, plan: JsonObject) -> JsonObject:
        return json.loads((self.directory(plan) / "journal.json").read_bytes())

    def backup_bytes(self, plan: JsonObject) -> dict[str, bytes]:
        bundle = self.directory(plan) / "backup"
        return {path.name: path.read_bytes() for path in bundle.iterdir()}

    def identities(self) -> list[tuple[str, str]]:
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute(
                "SELECT name, type FROM sqlite_schema WHERE name IN "
                "('pf_store_meta','pf_schema_versions') ORDER BY name"
            ).fetchall()

    def events(self) -> list[JsonObject]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute("SELECT record FROM events ORDER BY seq")
            return [json.loads(row[0]) for row in rows]

    def ready(self, result: JsonObject, plan: JsonObject, data: bytes) -> None:
        self.assertEqual(result["status"], "ready", result["error"])
        self.assertEqual(result["targets"][0]["plan_checksum"], plan["plan_checksum"])
        self.assertEqual(self.slot()["state"], "ready")
        self.assertEqual(self.slot()["store_id"], plan["store_id"])
        self.assertEqual(self.slot()["plan_checksum"], plan["plan_checksum"])
        self.assertEqual(self.selector.read_bytes(), data)
        self.assertEqual((self.directory(plan) / "plan.json").read_bytes(), data)
        with closing(sqlite3.connect(self.path)) as connection:
            identity = connection.execute(
                "SELECT store_id, scope, owner_id FROM pf_store_meta"
            ).fetchone()
            self.assertEqual(identity, (plan["store_id"], "project", "history-a"))

    def failure(self, result: JsonObject, code: str, owner: str = "history-a") -> None:
        self.assertEqual(result["error"], {"code": code})
        self.assertEqual(
            result["requested_target"], {"kind": "events", "scope": "project"}
        )
        self.assertEqual(result["selected_target"]["owner_id"], owner)

    def test_released_full_target_pending_resumes_online(self) -> None:
        plan = self.produce_v1("released", "pending")
        original = self.selector.read_bytes()
        with patch.object(online, "uuid4", side_effect=AssertionError("reserved UUID")):
            self.ready(self.operation(), plan, original)
        self.assertEqual(self.events(), [_ORIGINAL])
        self.assertEqual(self.checkpoint(plan)["state"], "ready")

    def test_selected_v1_reuses_its_exact_backup(self) -> None:
        plan = self.produce_v1("selected", "importing")
        data, backup = self.selector.read_bytes(), self.backup_bytes(plan)
        before = self.checkpoint(plan)["backup_manifest_checksum"]
        with patch.object(
            online.SQLiteBackupService,
            "create",
            side_effect=AssertionError("existing backup"),
        ):
            self.ready(self.operation(), plan, data)
        self.assertEqual(self.backup_bytes(plan), backup)
        self.assertEqual(self.checkpoint(plan)["backup_manifest_checksum"], before)
        self.assertEqual(self.events(), [_ORIGINAL])

    def test_persisted_digest_alone_cannot_supply_historical_authority(self) -> None:
        plan = self.produce_v1("released", "pending")
        old_data = self.selector.read_bytes()
        changed_device = self.root / "changed-device.yaml"
        result = online.run_online_project_event_migration(
            project_root=self.project,
            workplace_root=self.workplace,
            device_config_path=changed_device,
            configuration=self.config,
            operation="resume",
        )
        self.failure(result, "storage_safety_changed")
        self.assertEqual(self.selector.read_bytes(), old_data)
        self.assertEqual(self.slot()["state"], "pending")
        self.assertEqual(self.identities(), [])

        # A well-formed checksum over a fabricated generation is still not a
        # producer generation. Model a selector-only checkpoint.
        for path in self.directory(plan).iterdir():
            path.unlink()
        self.directory(plan).rmdir()
        self.pins.unlink()
        plan.pop("plan_checksum")
        plan["safety_generation"] = _hash({"claimed": plan["safety_generation"]})
        plan["plan_checksum"] = _hash(plan)
        fabricated = online._canonical_bytes(plan)
        self.selector.write_bytes(fabricated)
        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            self.failure(self.operation("apply"), "storage_safety_changed")
        self.assertEqual(self.selector.read_bytes(), fabricated)
        self.assertFalse(self.pins.exists())

    def test_conflicting_other_owner_and_orphan_plan_block_fresh_default(self) -> None:
        plan = self.produce_v1("released", "pending")
        data = self.selector.read_bytes()
        self.pins.unlink()
        self.set_owner("other-owner")
        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            self.failure(
                self.operation("apply"), online._EVIDENCE_CONFLICT, "other-owner"
            )
            self.set_owner("history-a")
            self.selector.unlink()
            self.failure(self.operation("apply"), online._EVIDENCE_CONFLICT)
            misplaced = self.directory(plan).with_name("misplaced-plan")
            self.directory(plan).rename(misplaced)
            self.failure(self.operation("apply"), online._EVIDENCE_CONFLICT)
        self.assertEqual((misplaced / "plan.json").read_bytes(), data)
        self.assertEqual(self.events(), [_ORIGINAL])
        self.assertEqual(self.identities(), [])

    def test_competing_v2_selector_cannot_replace_selected_v1(self) -> None:
        plan = self.produce_v1("released", "pending")
        original = self.selector.read_bytes()
        contender = dict(plan, migration_id=online.MIGRATION_ID)
        contender.pop("plan_checksum")
        contender["plan_checksum"] = _hash(contender)
        conflict = self.selector.with_name("competing.json")
        competing = online._canonical_bytes(contender)
        conflict.write_bytes(competing)
        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            self.failure(self.operation("apply"), online._EVIDENCE_CONFLICT)
        self.assertEqual(conflict.read_bytes(), competing)
        self.assertEqual(self.selector.read_bytes(), original)
        self.assertEqual(self.slot()["state"], "pending")
        self.assertEqual(self.identities(), [])

    def test_missing_recorded_backup_is_never_recreated(self) -> None:
        plan = self.produce_v1("selected", "importing")
        bundle = self.directory(plan) / "backup"
        saved = bundle.with_name("saved-backup")
        bundle.rename(saved)
        with patch.object(
            online.SQLiteBackupService,
            "create",
            side_effect=AssertionError("no replacement backup"),
        ):
            self.failure(self.operation(), "storage_backup_missing")
        self.assertTrue(saved.is_dir())
        self.assertEqual(self.slot()["state"], "pending")
        self.assertEqual(self.identities(), [])

    def test_descriptor_with_shortened_inventory_is_rejected(self) -> None:
        descriptor = online._online_descriptor()
        descriptor["transform_files"].pop()
        descriptor["transform_checksum"] = _hash(descriptor["transform_files"])
        with patch.object(online, "_read_code_document", return_value=descriptor):
            self.failure(self.operation("apply"), "storage_transform_changed")
        self.assertFalse(self.selector.exists())

    def test_current_online_authority_is_required_for_historical_pending(self) -> None:
        plan = self.produce_v1("released", "pending")
        state = json.loads((self.runtime / "service.json").read_bytes())
        state[PROJECT_EVENT_RUNTIME_IDENTITY] = "different-process"
        self.write(self.runtime / "service.json", state)
        self.failure(self.operation(), "storage_project_event_runtime_unknown")
        self.assertEqual(self.slot()["state"], "pending")
        self.assertFalse((self.directory(plan) / "backup").exists())
        self.assertEqual(self.identities(), [])

    def test_v2_publication_checkpoints_resume_without_new_uuid(self) -> None:
        real = online.publish_immutable_bytes

        def after_selector(path: Path, data: bytes) -> None:
            real(path, data)
            raise Interrupted()

        with patch.object(online, "publish_immutable_bytes", after_selector):
            with self.assertRaises(Interrupted):
                self.operation("apply")
        data = self.selector.read_bytes()
        plan = json.loads(data)
        self.assertEqual(plan["migration_id"], online.MIGRATION_ID)
        plan_path = self.directory(plan) / "plan.json"
        self.assertFalse(plan_path.exists())
        self.assertFalse(self.pins.exists())

        def after_plan(path: Path, data: bytes) -> None:
            real(path, data)
            if path == plan_path:
                raise Interrupted()

        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            with patch.object(online, "publish_immutable_bytes", after_plan):
                with self.assertRaises(Interrupted):
                    self.operation()
            self.assertEqual(plan_path.read_bytes(), data)
            self.assertFalse(self.pins.exists())
            self.ready(self.operation(), plan, data)

    def test_partial_selector_and_missing_pending_checkpoint_refuse(self) -> None:
        self.selector.parent.mkdir(parents=True)
        self.selector.write_bytes(b"{")
        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            self.failure(self.operation("apply"), online._EVIDENCE_CONFLICT)
        self.assertEqual(self.selector.read_bytes(), b"{")
        self.selector.unlink()
        plan = self.produce_v1("selected", "pending")
        (self.directory(plan) / "journal.json").unlink()
        self.failure(self.operation(), "storage_journal_conflict")
        self.assertEqual(self.slot()["state"], "pending")

    def test_missing_resume_refuses_without_allocating(self) -> None:
        with patch.object(online, "uuid4", side_effect=AssertionError("no remint")):
            self.failure(self.operation(), online._PLAN_MISSING)
        self.assertFalse(self.pins.exists())

    def test_expired_deadline_prevents_publication_and_ddl_commit(self) -> None:
        expired = self.operation("apply", deadline=time.monotonic())
        self.assertEqual(expired["error"], {"code": "storage_deadline_exceeded"})
        self.assertFalse(self.selector.exists())
        real_clock = time.monotonic
        real_ddl = online.add_store_identity
        offset = 0.0

        def clock() -> float:
            return real_clock() + offset

        def expire_after_ddl(
            connection: sqlite3.Connection, target: StoreTarget, store_id: str
        ) -> None:
            nonlocal offset
            real_ddl(connection, target, store_id)
            offset = 120.0

        with patch.object(online.time, "monotonic", clock):
            with patch.object(online, "add_store_identity", expire_after_ddl):
                self.failure(self.operation("apply"), "storage_deadline_exceeded")
        data = self.selector.read_bytes()
        plan = json.loads(data)
        self.assertEqual(self.slot()["state"], "pending")
        self.assertEqual(self.checkpoint(plan)["state"], "importing")
        backup = self.backup_bytes(plan)
        self.assertEqual(self.identities(), [])
        self.ready(self.operation(), plan, data)
        self.assertEqual(self.backup_bytes(plan), backup)

    def test_inherited_project_only_admission_refuses_before_intent(self) -> None:
        with ExecutionAdmission().project(self.project):
            with patch.object(
                online, "wait_registry_file_lock", side_effect=AssertionError
            ):
                self.failure(self.operation("apply"), "storage_activity_unknown")

    def test_expiry_during_target_try_never_starts_binding_try(self) -> None:
        real_try = online.try_registry_file_lock
        real_clock = time.monotonic
        target_gate = v1.storage_identity_gate(self.flow)
        calls: list[Path] = []
        offset = 0.0

        @contextmanager
        def expire_after_target(
            path: Path, *, owner: online.PreparedRegistryOwner
        ) -> Iterator[str]:
            nonlocal offset
            calls.append(path)
            with real_try(path, owner=owner) as result:
                if path == target_gate:
                    self.assertEqual(result, "acquired")
                    offset = 120.0
                yield result

        with (
            patch.object(online.time, "monotonic", lambda: real_clock() + offset),
            patch.object(online, "try_registry_file_lock", expire_after_target),
        ):
            result = self.operation("apply")
        self.failure(result, "storage_deadline_exceeded")
        self.assertTrue(result["retryable"])
        self.assertEqual(calls, [target_gate])
        self.assertFalse(self.selector.exists())
        self.assertEqual(self.identities(), [])
        owner = online.prepare_registry_owner()
        with (
            ExecutionAdmission().start(self.neighbor, self.workplace),
            real_try(target_gate, owner=owner) as acquired,
            project_event_binding_writer_guard(self.project),
        ):
            self.assertEqual(acquired, "acquired")

    def test_v2_apply_and_resume_ignore_unrelated_accounting_identity(self) -> None:
        accounting = self.workplace / "data/accounting/identity.json"
        accounting.parent.mkdir(parents=True, exist_ok=True)
        self.write(accounting, {"missing": "origin_id"})
        unrelated = accounting.read_bytes()

        with (
            patch.object(online._Coordinator, "create_backup", side_effect=Interrupted),
            self.assertRaises(Interrupted),
        ):
            self.operation("apply")
        data = self.selector.read_bytes()
        self.ready(self.operation(), json.loads(data), data)
        self.assertEqual(accounting.read_bytes(), unrelated)

    def test_released_v1_refuses_if_full_generation_cannot_be_rebuilt(self) -> None:
        self.produce_v1("released", "pending")
        data = self.selector.read_bytes()
        accounting = self.workplace / "data/accounting/identity.json"
        accounting.parent.mkdir(parents=True, exist_ok=True)
        self.write(accounting, {"missing": "origin_id"})
        self.failure(self.operation(), "owner_identity_required")
        self.assertEqual(self.selector.read_bytes(), data)
        self.assertEqual(self.identities(), [])

    def test_plan_discovery_releases_workplace_admission(self) -> None:
        original_discover = online._Coordinator.discover
        scans = 0

        def admit_neighbor() -> None:
            with ExecutionAdmission().start(self.neighbor, self.workplace):
                self.assertTrue(ExecutionAdmission.held(self.neighbor, self.workplace))

        with ThreadPoolExecutor(max_workers=1) as pool:

            def observe_discovery(
                coordinator: online._Coordinator,
            ) -> online._Evidence | None:
                nonlocal scans
                scans += 1
                if scans == 2:
                    self.assertFalse(ExecutionAdmission.held(None, self.workplace))
                    self.assertFalse(ExecutionAdmission.held(self.project, None))
                    owner = online.prepare_registry_owner()
                    for gate in (
                        v1.storage_identity_gate(self.flow),
                        project_event_binding_path(self.project),
                    ):
                        with online.try_registry_file_lock(gate, owner=owner) as result:
                            self.assertNotEqual(result, "acquired")
                    pool.submit(admit_neighbor).result(timeout=5)
                return original_discover(coordinator)

            with patch.object(online._Coordinator, "discover", observe_discovery):
                result = self.operation("apply")
        self.assertEqual(result["status"], "ready", result)
        self.assertGreaterEqual(scans, 2)

    def test_binding_gate_retry_drops_both_admission_leases(self) -> None:
        binding_gate = project_event_binding_path(self.project)
        target_gate = v1.storage_identity_gate(self.flow)
        contested = threading.Event()
        attempts: list[Path] = []
        real_try = online.try_registry_file_lock
        real_wait = online.wait_registry_file_lock

        @contextmanager
        def observe_try(
            path: Path, *, owner: online.PreparedRegistryOwner
        ) -> Iterator[str]:
            self.assertTrue(ExecutionAdmission.held(self.project, self.workplace))
            attempts.append(path)
            with real_try(path, owner=owner) as result:
                yield result

        @contextmanager
        def observe_wait(path: Path, **kwargs: float) -> Iterator[None]:
            if path == binding_gate:
                self.assertFalse(ExecutionAdmission.held(self.project, None))
                self.assertFalse(ExecutionAdmission.held(None, self.workplace))
                contested.set()
            with real_wait(path, **kwargs):
                yield

        with ThreadPoolExecutor(max_workers=1) as pool:
            with project_event_binding_writer_guard(self.project):
                with patch.object(online, "try_registry_file_lock", observe_try):
                    with patch.object(online, "wait_registry_file_lock", observe_wait):
                        result = pool.submit(self.operation, "apply")
                        self.assertTrue(contested.wait(10))
                        self.assertEqual(attempts[:2], [target_gate, binding_gate])
                        self.assertFalse(self.selector.exists())
                        with ExecutionAdmission().start(self.neighbor, self.workplace):
                            self.assertTrue(
                                ExecutionAdmission.held(self.neighbor, self.workplace)
                            )
            self.assertEqual(result.result(10)["status"], "ready")

    def test_target_gate_miss_never_tries_binding_or_holds_admission(self) -> None:
        target = v1.storage_identity_gate(self.flow)
        binding = project_event_binding_path(self.project)
        attempt, held, waited, release = (threading.Event() for _ in range(4))
        attempts: list[Path] = []
        real_try = online.try_registry_file_lock
        real_wait = online.wait_registry_file_lock

        def own_target() -> None:
            self.assertTrue(attempt.wait(10))
            with real_wait(
                target, deadline=time.monotonic() + 10, stale_after_seconds=0
            ):
                held.set()
                self.assertTrue(release.wait(10))

        @contextmanager
        def observe_try(
            path: Path, *, owner: online.PreparedRegistryOwner
        ) -> Iterator[str]:
            attempts.append(path)
            if len(attempts) == 1:
                attempt.set()
                self.assertTrue(held.wait(10))
            with real_try(path, owner=owner) as result:
                yield result

        @contextmanager
        def observe_wait(path: Path, **kwargs: float) -> Iterator[None]:
            if attempt.is_set() and not waited.is_set():
                self.assertEqual(path, target)
                self.assertFalse(ExecutionAdmission.held(self.project, None))
                self.assertFalse(ExecutionAdmission.held(None, self.workplace))
                waited.set()
            with real_wait(path, **kwargs):
                yield

        with ThreadPoolExecutor(max_workers=2) as pool:
            holder = pool.submit(own_target)
            with (
                patch.object(online, "try_registry_file_lock", observe_try),
                patch.object(online, "wait_registry_file_lock", observe_wait),
            ):
                migration = pool.submit(self.operation, "apply")
                try:
                    self.assertTrue(waited.wait(10))
                    self.assertEqual(attempts, [target])
                    with ExecutionAdmission().start(self.neighbor, self.workplace):
                        self.assertTrue(
                            ExecutionAdmission.held(self.neighbor, self.workplace)
                        )
                finally:
                    release.set()
                holder.result(10)
                self.assertEqual(migration.result(10)["status"], "ready")
        self.assertEqual(attempts[:3], [target, target, binding])

    def test_binding_writer_wins_before_ddl(self) -> None:
        real_verify = online._Coordinator.backup_checksum
        verified = threading.Event()
        changed = threading.Event()

        def verify(coordinator: online._Coordinator, evidence: online._Evidence) -> str:
            checksum = real_verify(coordinator, evidence)
            verified.set()
            self.assertTrue(changed.wait(10))
            return checksum

        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch.object(online._Coordinator, "backup_checksum", verify):
                migration = pool.submit(self.operation, "apply")
                try:
                    self.assertTrue(verified.wait(10))
                    with project_event_binding_writer_guard(self.project):
                        self.set_owner("changed-owner")
                finally:
                    changed.set()
                self.failure(migration.result(10), "storage_enrollment_conflict")
        data = self.selector.read_bytes()
        plan = json.loads(data)
        backup = self.backup_bytes(plan)
        self.assertEqual(self.slot()["state"], "pending")
        self.assertEqual(self.identities(), [])
        self.assertEqual(self.events(), [_ORIGINAL])
        with project_event_binding_writer_guard(self.project):
            self.set_owner("history-a")
        self.ready(self.operation(), plan, data)
        self.assertEqual(self.backup_bytes(plan), backup)

    def test_commit_holds_binding_then_ready_rechecks_original_owner(self) -> None:
        real_ddl = online.add_store_identity
        real_try = execution_admission._registry_lock_try_os_lock
        real_apply = online._Coordinator.apply_identity
        after_ddl, contended, release_ddl, writer_done = (
            threading.Event() for _ in range(4)
        )
        writer_observed: list[list[tuple[str, str]]] = []

        def ddl(
            connection: sqlite3.Connection, target: StoreTarget, store_id: str
        ) -> None:
            real_ddl(connection, target, store_id)
            after_ddl.set()
            self.assertTrue(release_ddl.wait(10))

        def read_try(fd: int) -> bool:
            acquired = real_try(fd)
            if threading.current_thread().name == "binding-writer" and not acquired:
                contended.set()
            return acquired

        def write_after_commit() -> None:
            try:
                threading.current_thread().name = "binding-writer"
                with project_event_binding_writer_guard(self.project):
                    writer_observed.append(self.identities())
                    self.set_owner("changed-owner")
            finally:
                writer_done.set()

        def apply(
            coordinator: online._Coordinator,
            evidence: online._Evidence,
            facts: JsonObject,
            binding_gate: Path,
        ) -> str:
            checksum = real_apply(coordinator, evidence, facts, binding_gate)
            self.assertTrue(writer_done.wait(10))
            return checksum

        with ThreadPoolExecutor(max_workers=2) as pool:
            with (
                patch.object(online, "add_store_identity", ddl),
                patch.object(
                    execution_admission, "_registry_lock_try_os_lock", read_try
                ),
                patch.object(online._Coordinator, "apply_identity", apply),
            ):
                migration = pool.submit(self.operation, "apply")
                try:
                    self.assertTrue(after_ddl.wait(10))
                    writer = pool.submit(write_after_commit)
                    self.assertTrue(contended.wait(10))
                    self.assertEqual(self.identities(), [])
                    self.assertEqual(self.events(), [_ORIGINAL])
                    self.assertEqual(self.slot()["state"], "pending")
                    with ExecutionAdmission().start(self.neighbor, self.workplace):
                        self.assertTrue(
                            ExecutionAdmission.held(self.neighbor, self.workplace)
                        )
                finally:
                    release_ddl.set()
                writer.result(10)
                self.failure(migration.result(10), "storage_enrollment_conflict")
        self.assertEqual(
            writer_observed,
            [[("pf_schema_versions", "table"), ("pf_store_meta", "table")]],
        )
        data = self.selector.read_bytes()
        plan = json.loads(data)
        backup = self.backup_bytes(plan)
        self.assertEqual(self.checkpoint(plan)["state"], "verified")
        self.assertEqual(self.slot()["state"], "pending")
        with project_event_binding_writer_guard(self.project):
            self.set_owner("history-a")
        self.ready(self.operation(), plan, data)
        self.assertEqual(self.backup_bytes(plan), backup)

    def test_ready_repair_accepts_new_events_and_preserves_backup(self) -> None:
        result = self.operation("apply")
        self.assertEqual(result["status"], "ready", result["error"])
        data = self.selector.read_bytes()
        plan = json.loads(data)
        backup = self.backup_bytes(plan)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            self.append(connection, _NEW)
        directory = self.directory(plan)
        (directory / "report.json").unlink()
        journal = self.checkpoint(plan)
        journal["state"] = "verified"
        self.write(directory / "journal.json", journal)
        self.ready(self.operation(), plan, data)
        self.assertEqual(self.checkpoint(plan)["state"], "ready")
        self.assertTrue((directory / "report.json").is_file())
        self.assertEqual(self.events(), [_ORIGINAL, _NEW])
        self.assertEqual(self.backup_bytes(plan), backup)


if __name__ == "__main__":
    unittest.main()
