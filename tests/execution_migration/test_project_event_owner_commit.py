"""Exercise the binding writer against a real, guarded SQLite transaction."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import processforge as cli

from processforge_core.configuration import ConfigurationProvider, PFConfig
from processforge_core.configuration.device import DeviceConfigurationSource
from processforge_core.maintenance import fresh_project, project_event_owner
from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import MaintenanceError, StoreTarget
from processforge_core.maintenance.project_event_owner import (
    project_event_binding_path,
    read_project_event_binding,
    require_project_event_binding,
)
from processforge_core.maintenance.storage_migration import add_store_identity
from processforge_core.process_event_journal import ProcessEventJournal
from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.runtime.execution_admission import registry_file_lock

OWNER = "fixture-owner"
STORE_ID = "01675e8eae5d4233b64d0d5d18fb7b71"
RELATIVE_DB = "runtime/events/events.sqlite3"
EVENT = {
    "event_id": "evt_before_binding_race",
    "event_type": "fixture.journal",
    "time": "2026-11-24T00:00:00Z",
    "data": {"value": 143},
}
WAIT_SECONDS = 10


class BindingPublished(Exception):
    """Stop the fixture at the first post-publication onboarding event."""


class BootstrapBindingTests(unittest.TestCase):
    def test_force_allows_only_the_unbound_inert_template(self) -> None:
        scratch = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(scratch).resolve()
        project = root / "project"
        workplace = root / "workplace" / "workplace.yaml"
        public = project / ".pf/process-forge.yaml"
        local = project / ".pf/process-forge.local.yaml"
        public.parent.mkdir(parents=True)
        public.write_bytes(b"schema_version: 1\n")
        local_yaml = json.dumps({"workplace": {"manifest": str(workplace)}})
        files = {public: "project: {id: new-owner}\n", local: local_yaml}
        request = {"project_root": project, "workplace": workplace}

        selected = cli._project_bootstrap_binding(dict(request, force=True), files)
        self.assertEqual(selected.project_id, "new-owner")
        self.assertEqual(selected.workplace_root, workplace.parent)
        self.assertIsNone(selected.receipt)

        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            cli._project_bootstrap_binding(request, files)
        local.write_text(local_yaml, encoding="utf-8")
        with self.assertRaisesRegex(MaintenanceError, "^project_identity_required$"):
            cli._project_bootstrap_binding(dict(request, force=True), files)


class ProjectEventOwnerTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = self.enterContext(tempfile.TemporaryDirectory())
        self.scratch = Path(scratch).resolve()
        self.project = self.scratch / "project"
        self.project.mkdir()
        self.flow = self.project / ".pf"
        self.public = self.flow / "process-forge.yaml"
        self.local = self.flow / "process-forge.local.yaml"
        self.first = self.workplace("workplace-one")
        self.second = self.workplace("workplace-two")
        self.configuration = ConfigurationProvider.pinned(PFConfig())
        self.enterContext(
            patch.object(
                DeviceConfigurationSource,
                "default_path",
                return_value=self.scratch / "device.yaml",
            )
        )
        self.assertTrue(fresh_project.create_project_storage_root(self.project))
        self.public.write_text(f"project:\n  id: {OWNER}\n", encoding="utf-8")
        self.local.write_text(
            json.dumps({"workplace": {"manifest": str(self.first)}}), encoding="utf-8"
        )
        fresh_project.initialize_project_storage(
            self.project, self.first.parent, configuration=self.configuration
        )
        self.db = self.flow / RELATIVE_DB
        self.guard = project_event_binding_path(self.project)
        self.enterContext(
            patch.object(
                cli, "build_configuration_provider", return_value=self.configuration
            )
        )
        self.enterContext(
            patch.object(
                cli.project_initialization,
                "apply_agent_entry",
                return_value={"status": "complete", "agent_entry": {}},
            )
        )
        self.enterContext(
            patch.object(
                cli._process_event_recorder,
                "emit_process_event",
                side_effect=self.after_publication,
            )
        )

    def workplace(self, name: str) -> Path:
        path = self.scratch / name / "workplace.yaml"
        path.parent.mkdir()
        path.write_text(f"workplace:\n  id: {name}\n", encoding="utf-8")
        return path

    def use_legacy_event_store(self) -> None:
        (self.flow / fresh_project.RECEIPT).unlink()
        (self.flow / "data/storage-identities.json").unlink()
        legacy = self.scratch / "legacy-events.sqlite3"
        self.assertEqual(ProcessEventJournal().append_many(legacy, [EVENT]), 1)
        legacy.replace(self.db)

    def after_publication(self, project: Path, event: str, **kwargs: object) -> None:
        self.assertEqual(project, self.project)
        self.assertEqual(event, "project.onboarding.started")
        with registry_file_lock(self.guard, timeout_seconds=WAIT_SECONDS):
            raise BindingPublished

    def onboard(self, workplace: Path, *, owner: str = OWNER) -> None:
        answers = self.scratch / "answers.json"
        answers.write_text(json.dumps({"project": {"id": owner}}), encoding="utf-8")
        arguments = argparse.Namespace(
            project_root=str(self.project),
            workplace=str(workplace),
            answers=str(answers),
            project_type="generic-software-project",
            force=True,
            allow_missing_workplace=False,
            apply=True,
            command="project-onboard",
        )
        with self.assertRaises(BindingPublished):
            cli.command_init_project(arguments)

    def target(self) -> StoreTarget:
        return StoreTarget("events", self.db, RELATIVE_DB, "project", OWNER)

    def assert_tables(self, present: bool) -> None:
        with closing(sqlite3.connect(self.db.as_uri() + "?mode=ro", uri=True)) as db:
            tables = db.execute(
                "SELECT name FROM sqlite_schema WHERE name IN "
                "('pf_store_meta', 'pf_schema_versions') ORDER BY name"
            ).fetchall()
            self.assertEqual(
                tables, [("pf_schema_versions",), ("pf_store_meta",)] if present else []
            )
            if present:
                self.assertEqual(
                    db.execute("SELECT * FROM pf_store_meta").fetchall(),
                    [(1, STORE_ID, "project", OWNER, 1)],
                )
            (encoded,) = db.execute("SELECT record FROM events").fetchone()
            self.assertEqual(json.loads(encoded), EVENT)

    def observe_contention(self, event: threading.Event) -> None:
        def observed_lock(path: Path):
            self.assertEqual(path, self.guard)
            return registry_file_lock(
                path, timeout_seconds=WAIT_SECONDS, on_contention=event.set
            )

        self.enterContext(
            patch.object(
                project_event_owner, "registry_file_lock", side_effect=observed_lock
            )
        )

    def test_writer_wins_before_guarded_commit_and_identity_rolls_back(self) -> None:
        self.use_legacy_event_store()
        selection = read_project_event_binding(self.project)
        backup = SQLiteBackupService()
        bundle = self.scratch / "event-backup"
        backup.create(self.db, bundle)
        verifying = threading.Event()
        resume_verification = threading.Event()

        def migrate() -> dict[str, object]:
            verifying.set()
            self.assertTrue(resume_verification.wait(WAIT_SECONDS))
            verified = backup.verify(bundle)
            with registry_file_lock(self.guard), closing(sqlite3.connect(self.db)) as db:
                db.execute("BEGIN IMMEDIATE")
                add_store_identity(db, self.target(), STORE_ID)
                self.assertTrue(db.in_transaction)
                try:
                    with self.assertRaisesRegex(
                        MaintenanceError, "^storage_enrollment_conflict$"
                    ):
                        require_project_event_binding(selection)
                finally:
                    db.rollback()
            return verified

        with ThreadPoolExecutor(max_workers=1) as pool:
            migration = pool.submit(migrate)
            try:
                self.assertTrue(verifying.wait(WAIT_SECONDS))
                self.onboard(self.second)
                self.assertEqual(
                    read_project_event_binding(self.project).workplace_manifest,
                    self.second,
                )
            finally:
                resume_verification.set()
            verified = migration.result(timeout=WAIT_SECONDS)

        self.assert_tables(False)
        self.assertEqual(backup.verify(bundle), verified)
        self.assertFalse((self.flow / "data/storage-identities.json").exists())

        self.onboard(self.first)
        with registry_file_lock(self.guard), closing(sqlite3.connect(self.db)) as db:
            db.execute("BEGIN IMMEDIATE")
            add_store_identity(db, self.target(), STORE_ID)
            require_project_event_binding(selection)
            db.commit()
        self.assert_tables(True)
        self.assertEqual(backup.verify(bundle), verified)

    def test_writer_contends_until_native_commit(self) -> None:
        self.use_legacy_event_store()
        selection = read_project_event_binding(self.project)
        contended = threading.Event()
        self.observe_contention(contended)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with registry_file_lock(self.guard), closing(sqlite3.connect(self.db)) as db:
                db.execute("BEGIN IMMEDIATE")
                add_store_identity(db, self.target(), STORE_ID)
                require_project_event_binding(selection)
                writer = pool.submit(self.onboard, self.second)
                self.assertTrue(
                    contended.wait(WAIT_SECONDS), "writer never tried the held guard"
                )
                self.assertFalse(writer.done())
                self.assertEqual(
                    ProjectMetadataReader(self.project).workplace_manifest(), self.first
                )
                self.assert_tables(False)
                db.commit()
                self.assert_tables(True)
                self.assertEqual(
                    ProjectMetadataReader(self.project).workplace_manifest(), self.first
                )
            writer.result(timeout=WAIT_SECONDS)

        self.assertEqual(
            read_project_event_binding(self.project).workplace_manifest, self.second
        )
        self.assert_tables(True)
        with registry_file_lock(self.guard):
            with self.assertRaisesRegex(
                MaintenanceError, "^storage_enrollment_conflict$"
            ):
                require_project_event_binding(selection)

    def test_project_mode_reads_manifest_after_other_writer(self) -> None:
        self.use_legacy_event_store()
        before_write = threading.Event()
        finish_write = threading.Event()
        contended = threading.Event()
        read_started = threading.Event()
        self.observe_contention(contended)
        write_file = cli.write_file
        read_yaml_file = cli.read_yaml_file

        def hold_public_write(path: Path, *args, **kwargs):
            if path == self.public:
                before_write.set()
                if not finish_write.wait(WAIT_SECONDS):
                    raise AssertionError("writer was never released")
            return write_file(path, *args, **kwargs)

        def observe_public_read(path: Path):
            if path == self.public:
                read_started.set()
            return read_yaml_file(path)

        args = argparse.Namespace(
            project_root=str(self.project),
            mode="simple",
            workplace=None,
            json=False,
        )
        with (
            patch.object(cli, "write_file", side_effect=hold_public_write),
            patch.object(cli, "read_yaml_file", side_effect=observe_public_read),
            patch.object(cli, "write_project_context_snapshot_outputs"),
            patch.object(cli, "command_project_mode_status", return_value=0),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            writer = pool.submit(self.onboard, self.first, owner="new-owner")
            try:
                self.assertTrue(
                    before_write.wait(WAIT_SECONDS), "writer never reached publication"
                )
                read_started.clear()
                mode = pool.submit(cli.command_project_mode_set, args)
                self.assertTrue(
                    contended.wait(WAIT_SECONDS), "mode never tried the held guard"
                )
                self.assertFalse(read_started.is_set())
            finally:
                finish_write.set()
            writer.result(timeout=WAIT_SECONDS)
            self.assertEqual(mode.result(timeout=WAIT_SECONDS), 0)
        self.assertTrue(read_started.is_set())
        manifest = ProjectMetadataReader(self.project).manifest()
        self.assertEqual(manifest["project"]["id"], "new-owner")
        self.assertEqual(manifest["coordination"]["mode"], "simple")

    def test_receipt_backed_writer_refuses_reenrollment_without_manifest_change(self) -> None:
        old_files = self.public.read_bytes(), self.local.read_bytes()
        with self.assertRaisesRegex(MaintenanceError, "^storage_fresh_target_conflict$"):
            self.onboard(self.second)
        self.assertEqual((self.public.read_bytes(), self.local.read_bytes()), old_files)

    def test_repair_restores_local_manifest_and_preserves_public_candidate(self) -> None:
        selected = read_project_event_binding(self.project)
        public_bytes = self.public.read_bytes()
        self.local.unlink()
        args = argparse.Namespace(
            project_root=str(self.project),
            workplace=str(self.first),
            repair_action="restore_deterministic_artifacts",
            reason="fixture",
            apply=True,
        )
        with self.assertRaises(BindingPublished):
            cli.command_project_init_repair(args)
        self.assertEqual(read_project_event_binding(self.project), selected)
        self.assertEqual(self.public.read_bytes(), public_bytes)
        self.assertTrue(self.public.with_suffix(".yaml.candidate").is_file())

    def test_binding_resolves_alias_and_refuses_missing_enrollment(self) -> None:
        self.local.write_text(
            "workplace:\n  manifest: ../workplace-one/workplace.yaml\n",
            encoding="utf-8",
        )
        alias = self.project / ".." / self.project.name
        self.assertEqual(project_event_binding_path(alias), self.guard)
        selection = read_project_event_binding(alias)
        self.assertEqual(selection.project_root, self.project)
        self.assertEqual(selection.workplace_manifest, self.first)
        self.assertEqual(selection.event_target, self.db)
        with registry_file_lock(self.guard):
            require_project_event_binding(selection)
            self.local.unlink()
            with self.assertRaisesRegex(
                MaintenanceError, "^storage_enrollment_conflict$"
            ):
                require_project_event_binding(selection)


if __name__ == "__main__":
    unittest.main()
