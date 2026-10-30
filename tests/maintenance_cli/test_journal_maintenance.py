"""Exercise real maintenance adapters and the primary-registered CLI entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from pf_cli.commands.journal_maintenance import JournalMaintenanceCommand
from pf_cli.parsers.journal_maintenance import register_journal_maintenance

from processforge_core.maintenance.backup import SQLiteBackupService
from processforge_core.maintenance.contracts import JsonObject, MaintenanceError
from processforge_core.sqlite_storage import JournalError

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = (
    Path(os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir())
    / "journal-maintenance-cli"
)


def parser_for(command: JournalMaintenanceCommand) -> argparse.ArgumentParser:
    """Build the actual standalone parser with a concrete command owner."""
    parser = argparse.ArgumentParser(prog="pf")
    groups = parser.add_subparsers(dest="command", required=True)
    register_journal_maintenance(groups.add_parser, execute=command.execute)
    return parser


class ParserTests(unittest.TestCase):
    """Check required selectors, explicit effects and parser isolation."""

    def test_all_five_operations_accept_json_and_explicit_paths(self) -> None:
        parser = parser_for(JournalMaintenanceCommand())
        cases = {
            "backup": ["--database", "db", "--output", "bundle"],
            "verify": ["--backup", "bundle"],
            "restore": ["--backup", "bundle", "--destination", "new-db"],
            "inspect": ["--project-root", "project", "--workplace", "workplace"],
            "import": ["--project-root", "project", "--workplace", "workplace"],
        }
        for operation, options in cases.items():
            with self.subTest(operation=operation):
                args = parser.parse_args(
                    ["journal-maintenance", operation, *options, "--json"]
                )
                self.assertEqual(args.maintenance_command, operation)
                self.assertTrue(args.json)
                self.assertTrue(callable(args.func))
                if operation in ("inspect", "import"):
                    self.assertEqual(args.maintenance_project_root, Path("project"))
                    self.assertFalse(hasattr(args, "project_root"))
                    self.assertFalse(hasattr(args, "workplace"))
                if operation == "import":
                    self.assertFalse(args.apply)
                    self.assertFalse(args.skip_invalid)

    def test_incomplete_selectors_and_abbreviated_effects_are_rejected(self) -> None:
        parser = parser_for(JournalMaintenanceCommand())
        cases: tuple[list[str], ...] = (
            [],
            ["backup", "--database", "db"],
            ["verify"],
            ["restore", "--backup", "bundle"],
            ["inspect", "--project-root", "project"],
            ["import", "--workplace", "workplace"],
            [
                "import",
                "--project-root",
                "project",
                "--workplace",
                "workplace",
                "--app",
            ],
        )
        for options in cases:
            with self.subTest(options=options), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    parser.parse_args(["journal-maintenance", *options])
                self.assertEqual(error.exception.code, 2)

    def test_inspect_cannot_apply_or_silently_skip_corruption(self) -> None:
        parser = parser_for(JournalMaintenanceCommand())
        for flag in ("--apply", "--skip-invalid"):
            with self.subTest(flag=flag), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parser.parse_args(
                        [
                            "journal-maintenance",
                            "inspect",
                            "--project-root",
                            "p",
                            "--workplace",
                            "w",
                            flag,
                        ]
                    )

    def test_help_discloses_immediate_writes_and_evidence_side_effects(self) -> None:
        parser = parser_for(JournalMaintenanceCommand())
        for operation, expected in (
            ("backup", "immediately"),
            ("restore", "immediately"),
            ("inspect", "quarantine"),
            ("import", "--apply"),
        ):
            output = io.StringIO()
            with self.subTest(operation=operation), redirect_stdout(output):
                with self.assertRaises(SystemExit) as error:
                    parser.parse_args(["journal-maintenance", operation, "--help"])
                self.assertEqual(error.exception.code, 0)
                self.assertIn(expected, output.getvalue())

    def test_construction_and_registration_are_cold(self) -> None:
        factory = Mock(side_effect=AssertionError("unexpected service construction"))
        command = JournalMaintenanceCommand(
            backup_factory=factory, scan_factory=factory, maintenance_factory=factory
        )
        parser = parser_for(command)
        parser.parse_args(["journal-maintenance", "verify", "--backup", "bundle"])
        factory.assert_not_called()

    def test_parser_builds_keep_their_own_handler(self) -> None:
        first, second = JournalMaintenanceCommand(), JournalMaintenanceCommand()
        options = ["journal-maintenance", "verify", "--backup", "bundle"]
        self.assertEqual(parser_for(first).parse_args(options).func, first.execute)
        self.assertEqual(parser_for(second).parse_args(options).func, second.execute)

    def test_default_adapter_import_never_loads_main_or_host(self) -> None:
        script = """
import sys
from importlib.abc import MetaPathFinder

sys.path[:0] = ['src', 'tools']

class RefuseTransport(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('processforge', 'tools.processforge', 'pf_runtime.host'):
            raise AssertionError('maintenance imported a forbidden transport')
        return None

sys.meta_path.insert(0, RefuseTransport())
from pf_cli.commands.journal_maintenance import JournalMaintenanceCommand
from pf_cli.parsers.journal_maintenance import register_journal_maintenance
JournalMaintenanceCommand()
assert callable(register_journal_maintenance)
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


class MaintenanceFixture(unittest.TestCase):
    """Keep every synthetic project, database and temporary file in owned scratch."""

    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.root = (SCRATCH / ("cli-" + uuid4().hex)).resolve()
        self.assertTrue(self.root.is_relative_to(SCRATCH.resolve()))
        self.root.mkdir()
        self.addCleanup(self.cleanup_scratch)
        runtime_temp = self.root / "temporary"
        runtime_temp.mkdir()
        temporary_patch = patch.object(tempfile, "tempdir", str(runtime_temp))
        temporary_patch.start()
        self.addCleanup(temporary_patch.stop)
        self.project = self.root / "project"
        self.workplace = self.root / "workplace"
        self.workplace.mkdir()
        flow = self.project / ".pf"
        flow.mkdir(parents=True)
        (flow / "process-forge.yaml").write_text(
            "project:\n  id: maintenance-cli-fixture\n", encoding="utf-8"
        )
        self.source = flow / "runtime/events/events.ndjson"
        self.source.parent.mkdir(parents=True)
        self.event = {"event_id": "event-1", "event_type": "fixture"}
        self.valid_line = (json.dumps(self.event) + "\n").encode("utf-8")
        self.source.write_bytes(self.valid_line)
        self.event_db = flow / "runtime/events/events.sqlite3"
        self.raw_db = flow / "runtime/agent-events/hooks.sqlite3"
        self.selectors = [
            "--project-root",
            str(self.project),
            "--workplace",
            str(self.workplace),
        ]

    def cleanup_scratch(self) -> None:
        """Remove only this fixture after checking its exact owned parent."""
        self.assertEqual(self.root.parent, SCRATCH.resolve())
        info = self.root.lstat()
        self.assertFalse(
            stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & 0x400)
        )
        shutil.rmtree(self.root)

    def invoke(
        self, *options: str, command: JournalMaintenanceCommand | None = None
    ) -> tuple[int, JsonObject]:
        """Invoke the real parser/command and require a single quiet JSON object."""
        parser = parser_for(command or JournalMaintenanceCommand())
        args = parser.parse_args(["journal-maintenance", *options])
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = args.func(args)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        report = json.loads(output.getvalue())
        self.assertIsInstance(report, dict)
        return code, report

    def database(self) -> Path:
        """Create a real database for default backup/restore operations."""
        path = self.root / "source.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE fixture(value TEXT)")
            connection.execute("INSERT INTO fixture VALUES ('retained')")
            connection.commit()
        return path

    def project_bytes(self) -> dict[str, bytes]:
        """Snapshot project files to prove inspect/plan did not add side effects."""
        return {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }


class CommandTests(MaintenanceFixture):
    """Cover actual owners, corruption refusal, explicit skip and replay."""

    def test_live_wal_backup_verify_and_restore_without_apply(self) -> None:
        source = self.database()
        bundle, restored = self.root / "bundle", self.root / "restored.sqlite3"
        with closing(sqlite3.connect(source)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO fixture VALUES ('wal-commit')")
            writer.commit()
            self.assertTrue(Path(str(source) + "-wal").is_file())
            code, report = self.invoke(
                "backup", "--database", str(source), "--output", str(bundle), "--json"
            )
            self.assertEqual(code, 0)
            self.assertEqual(report["integrity_check"], "ok")
            code, verified = self.invoke("verify", "--backup", str(bundle))
            self.assertEqual(code, 0)
            self.assertEqual(verified["sha256"], report["sha256"])
            code, report = self.invoke(
                "restore", "--backup", str(bundle), "--destination", str(restored)
            )
            self.assertEqual(code, 0)
            self.assertTrue(report["verified"])
        with closing(sqlite3.connect(restored)) as connection:
            self.assertEqual(
                connection.execute("PRAGMA integrity_check").fetchone(), ("ok",)
            )
            self.assertEqual(
                connection.execute(
                    "SELECT value FROM fixture ORDER BY rowid"
                ).fetchall(),
                [("retained",), ("wal-commit",)],
            )
        self.assertTrue((bundle / "manifest.json").is_file())

    def test_existing_bundle_and_restore_destination_are_preserved(self) -> None:
        source, bundle = self.database(), self.root / "bundle"
        self.assertEqual(
            self.invoke("backup", "--database", str(source), "--output", str(bundle))[
                0
            ],
            0,
        )
        manifest = (bundle / "manifest.json").read_bytes()
        code, _report = self.invoke(
            "backup", "--database", str(source), "--output", str(bundle)
        )
        self.assertEqual(code, 1)
        self.assertEqual((bundle / "manifest.json").read_bytes(), manifest)
        destination = self.root / "occupied.sqlite3"
        destination.write_bytes(b"original destination")
        code, _report = self.invoke(
            "restore", "--backup", str(bundle), "--destination", str(destination)
        )
        self.assertEqual(code, 1)
        self.assertEqual(destination.read_bytes(), b"original destination")

    def test_tampered_backup_refuses_verify_and_restore(self) -> None:
        source, bundle = self.database(), self.root / "bundle"
        self.invoke("backup", "--database", str(source), "--output", str(bundle))
        database = bundle / "database.sqlite3"
        data = database.read_bytes()
        database.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        self.assertEqual(self.invoke("verify", "--backup", str(bundle))[0], 1)
        destination = self.root / "new.sqlite3"
        self.assertEqual(
            self.invoke(
                "restore", "--backup", str(bundle), "--destination", str(destination)
            )[0],
            1,
        )
        self.assertFalse(destination.exists())

    def test_missing_backup_and_non_database_return_json_failure(self) -> None:
        code, report = self.invoke("verify", "--backup", str(self.root / "missing"))
        self.assertEqual((code, report["status"]), (1, "failed"))
        invalid = self.root / "invalid.sqlite3"
        invalid.write_bytes(b"not a database: private record")
        code, report = self.invoke(
            "backup",
            "--database",
            str(invalid),
            "--output",
            str(self.root / "bad-bundle"),
        )
        self.assertEqual(code, 1)
        self.assertNotIn("private record", json.dumps(report))

    def test_inspect_and_plan_leave_project_bytes_unchanged(self) -> None:
        before = self.project_bytes()
        for operation in ("inspect", "import"):
            code, report = self.invoke(operation, *self.selectors)
            self.assertEqual((code, report["status"]), (0, "planned"))
            self.assertEqual(report["unique_events"], 1)
            self.assertFalse(report["applied"])
            self.assertEqual(self.project_bytes(), before)

    def test_explicit_inspect_quarantine_preserves_exact_nul_bytes(self) -> None:
        damaged = b"\x00private corrupt record\r\n"
        self.source.write_bytes(self.valid_line + damaged)
        before = self.project_bytes()
        evidence = self.root / "quarantine"
        code, report = self.invoke(
            "inspect", *self.selectors, "--evidence-dir", str(evidence), "--json"
        )
        self.assertEqual((code, report["status"]), (1, "blocked"))
        self.assertEqual(report["invalid_rows"], 1)
        self.assertEqual(self.project_bytes(), before)
        self.assertNotIn("private corrupt record", json.dumps(report))
        manifest_bytes = (evidence / "manifest.json").read_bytes()
        self.assertEqual(
            hashlib.sha256(manifest_bytes).hexdigest(), report["quarantine"]["sha256"]
        )
        record = json.loads(manifest_bytes)["records"][0]
        self.assertEqual((evidence / record["file"]).read_bytes(), damaged)
        self.assertEqual(record["offset"], len(self.valid_line))
        self.assertEqual(record["length"], len(damaged))
        self.assertEqual(record["sha256"], hashlib.sha256(damaged).hexdigest())

    def test_corrupt_apply_quarantines_without_creating_databases(self) -> None:
        self.source.write_bytes(self.valid_line + b"\x00broken\n")
        before = self.project_bytes()
        code, report = self.invoke("import", *self.selectors, "--apply")
        self.assertEqual((code, report["status"]), (1, "blocked"))
        self.assertEqual(report["counts"]["corrupted"], 1)
        self.assertEqual(report["counts"]["skipped"], 0)
        self.assertFalse(self.event_db.exists())
        self.assertFalse(self.raw_db.exists())
        self.assertEqual(
            self.source.read_bytes(), before[".pf/runtime/events/events.ndjson"]
        )
        self.assertEqual(report["quarantine"]["status"], "verified")

    def test_explicit_skip_and_replay_avoid_duplicates(self) -> None:
        original = self.valid_line + b"\x00broken\n"
        self.source.write_bytes(original)
        code, plan = self.invoke("import", *self.selectors, "--skip-invalid")
        self.assertEqual((code, plan["status"]), (0, "planned"))
        self.assertEqual(plan["counts"]["skipped"], 1)
        self.assertFalse(self.event_db.exists())
        code, imported = self.invoke(
            "import", *self.selectors, "--apply", "--skip-invalid"
        )
        self.assertEqual((code, imported["status"]), (0, "ready"))
        self.assertEqual(imported["counts"]["imported"], 1)
        self.assertEqual(imported["counts"]["corrupted"], 1)
        code, replay = self.invoke(
            "import", *self.selectors, "--apply", "--skip-invalid", "--json"
        )
        self.assertEqual((code, replay["status"]), (0, "ready"))
        self.assertEqual(replay["counts"]["imported"], 0)
        self.assertEqual(replay["counts"]["already_present"], 1)
        self.assertEqual(
            [item["status"] for item in replay["backups"]], ["verified"] * 2
        )
        self.assertEqual(self.source.read_bytes(), original)
        with closing(sqlite3.connect(self.event_db)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM events").fetchone(), (1,)
            )

    def test_identity_conflicts_remain_failures_with_explicit_skip(self) -> None:
        conflict = {**self.event, "event_type": "different"}
        original = self.valid_line + (json.dumps(conflict) + "\n").encode()
        self.source.write_bytes(original)
        code, report = self.invoke(
            "import", *self.selectors, "--apply", "--skip-invalid"
        )
        self.assertEqual(code, 1)
        self.assertEqual(report["error"], "migration_event_id_conflict")
        self.assertFalse(self.event_db.exists())
        self.assertEqual(self.source.read_bytes(), original)

    def test_missing_project_manifest_is_a_json_input_failure(self) -> None:
        (self.project / ".pf/process-forge.yaml").unlink()
        code, report = self.invoke("inspect", *self.selectors)
        self.assertEqual((code, report["error"]), (1, "maintenance_input_invalid"))
        self.assertNotIn(str(self.project), json.dumps(report))

    def test_error_mapping_hides_exception_details(self) -> None:
        cases = (
            (MaintenanceError("backup_hash_mismatch"), "backup_hash_mismatch"),
            (
                JournalError("journal_database_error: private record"),
                "journal_database_error",
            ),
            (JournalError("private/path\nrecord"), "maintenance_journal_failed"),
            (FileNotFoundError("private record"), "maintenance_io_failed"),
            (sqlite3.DatabaseError("private record"), "maintenance_database_failed"),
            (ValueError("private record"), "maintenance_input_invalid"),
            (SystemExit("private record"), "maintenance_input_invalid"),
        )
        for error, expected in cases:
            factory = Mock(side_effect=error)
            command = JournalMaintenanceCommand(backup_factory=factory)
            with self.subTest(error=type(error).__name__):
                code, report = self.invoke(
                    "backup", "--database", "db", "--output", "bundle", command=command
                )
                self.assertEqual((code, report["error"]), (1, expected))
                self.assertNotIn("private", json.dumps(report))

    def test_command_does_not_resolve_away_backend_path_guards(self) -> None:
        backend = Mock(spec=SQLiteBackupService)
        backend.create.return_value = {"status": "ok"}
        command = JournalMaintenanceCommand(backup_factory=lambda: backend)
        self.invoke(
            "backup", "--database", "link/../db", "--output", "bundle", command=command
        )
        backend.create.assert_called_once_with(Path("link/../db"), Path("bundle"))

    def test_invalid_backend_reports_cannot_claim_success(self) -> None:
        cases = (
            ({"status": "ready", "blocked": True}, None),
            ({"status": "unknown"}, None),
            ({"status": "ok", "error": "refused"}, None),
            ({"status": "ok", "value": float("nan")}, "maintenance_report_invalid"),
            (["not an object"], "maintenance_report_invalid"),
        )
        for value, expected in cases:
            backend = Mock(spec=SQLiteBackupService)
            backend.verify.return_value = value
            command = JournalMaintenanceCommand(backup_factory=lambda: backend)
            with self.subTest(value=value):
                code, report = self.invoke(
                    "verify", "--backup", "bundle", command=command
                )
                self.assertEqual(code, 1)
                if expected:
                    self.assertEqual(report["error"], expected)


class RegisteredCliTests(MaintenanceFixture):
    """Require the real Main registration; primary owns the integration point."""

    def cli(self, *options: str) -> tuple[int, JsonObject]:
        """Run the published entrypoint on explicit synthetic scratch inputs."""
        environment = dict(os.environ)
        environment.update(
            PYTHONDONTWRITEBYTECODE="1",
            TMP=str(self.root / "temporary"),
            TEMP=str(self.root / "temporary"),
        )
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/processforge.py"),
                "journal-maintenance",
                *options,
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.stderr, "", result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1, result.stdout)
        report = json.loads(result.stdout)
        self.assertIsInstance(report, dict)
        return result.returncode, report

    def test_registered_backup_verify_restore(self) -> None:
        source, bundle = self.database(), self.root / "bundle"
        code, created = self.cli(
            "backup", "--database", str(source), "--output", str(bundle), "--json"
        )
        self.assertEqual(code, 0)
        code, verified = self.cli("verify", "--backup", str(bundle), "--json")
        self.assertEqual((code, verified["sha256"]), (0, created["sha256"]))
        destination = self.root / "restored.sqlite3"
        self.assertEqual(
            self.cli(
                "restore", "--backup", str(bundle), "--destination", str(destination)
            )[0],
            0,
        )
        self.assertTrue(destination.is_file())

    def test_registered_inspect_and_import_plan_have_no_project_writes(self) -> None:
        before = self.project_bytes()
        for operation in ("inspect", "import"):
            code, report = self.cli(operation, *self.selectors, "--json")
            self.assertEqual((code, report["status"]), (0, "planned"))
            self.assertEqual(self.project_bytes(), before)

    def test_registered_corrupt_apply_requires_explicit_skip_and_replays(self) -> None:
        original = self.valid_line + b"\x00broken\n"
        self.source.write_bytes(original)
        self.assertEqual(self.cli("import", *self.selectors, "--apply")[0], 1)
        self.assertFalse(self.event_db.exists())
        options = ["import", *self.selectors, "--apply", "--skip-invalid", "--json"]
        code, first = self.cli(*options)
        self.assertEqual((code, first["counts"]["imported"]), (0, 1))
        code, second = self.cli(*options)
        self.assertEqual((code, second["counts"]["imported"]), (0, 0))
        self.assertEqual(second["counts"]["already_present"], 1)
        self.assertEqual(self.source.read_bytes(), original)

    def test_registered_failure_is_one_json_object_with_exit_one(self) -> None:
        code, report = self.cli(
            "verify", "--backup", str(self.root / "missing"), "--json"
        )
        self.assertEqual((code, report["status"]), (1, "failed"))
