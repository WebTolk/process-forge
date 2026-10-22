"""Synthetic two-project common-workplace and managed-driver integration tests."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import codex_exec_worker
from codex_exec_worker import ManagedUsageCapture
from pf_cli.commands.usage import UsageCommand
from pf_cli.parsers.usage import UsageCommandParser

from processforge_core.accounting.composition import WorkplaceAccounting
from processforge_core.accounting.storage import AccountingStorageError

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)


class SyntheticCliTests(unittest.TestCase):
    """Exercise real service/repository composition with synthetic source files."""

    def setUp(self) -> None:
        environment = patch.dict(
            os.environ,
            {
                name: ""
                for name in (
                    "PF_PROJECT_ROOT",
                    "PF_PREPARED_INPUT_FILE",
                    "PF_AGENT_RUN_DIR",
                    "PF_TASK_ID",
                    "PF_WORKER_TASK_ID",
                    "PF_RUN_ID",
                    "PF_WORKER_RUN_ID",
                    "PF_WORKER_ATTEMPT",
                )
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.root = Path(__file__).parent.resolve() / ("fixture-" + uuid4().hex)
        self.root.mkdir()
        assert self.root.parent == Path(__file__).parent.resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.workplace = self.root / "workplace"
        self.workplace.mkdir()
        (self.workplace / "workplace.yaml").write_text(
            "schema_version: 1\n", encoding="utf-8"
        )
        self.projects = []
        for project_id in ("a", "b"):
            project = self.root / project_id
            (project / ".pf").mkdir(parents=True)
            (project / ".pf" / "process-forge.yaml").write_text(
                f"project:\n  id: {project_id}\n", encoding="utf-8"
            )
            (project / ".pf" / "process-forge.local.yaml").write_text(
                'workplace:\n  manifest: "'
                + (self.workplace / "workplace.yaml").as_posix()
                + '"\n',
                encoding="utf-8",
            )
            self.projects.append(project)
        self.parser = argparse.ArgumentParser()
        sub = self.parser.add_subparsers(dest="command", required=True)
        UsageCommandParser(execute=UsageCommand().execute).register(sub.add_parser)

    def invoke(self, name: str, *extra: str, project: int = 0) -> tuple[int, dict]:
        args = self.parser.parse_args(
            ["usage", name, "--project-root", str(self.projects[project]), *extra]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            code = args.func(args)
        return code, json.loads(output.getvalue())

    def import_source(self, project: int = 0, value: int = 100) -> tuple[Path, Path]:
        project_id = ("a", "b")[project]
        path = self.root / f"{project_id}.jsonl"
        path.write_text(
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {"input_tokens": value, "output_tokens": 10},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        binding = self.root / f"{project_id}-binding.json"
        binding.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "primary_records": True,
                    "origin_id": "synthetic-origin",
                    "source_id": "source-" + project_id,
                    "profile": "codex-exec-v1",
                    "observed_at": NOW.isoformat(),
                    "attribution": {
                        "project_id": project_id,
                        "agent_instance_id": "agent-" + project_id,
                        "session_id": "session-" + project_id,
                        "run_id": "run",
                        "assignment_id": "task",
                        "attempt": 1,
                        "provider": "codex",
                    },
                }
            ),
            encoding="utf-8",
        )
        code, data = self.invoke(
            "import", "--file", str(path), "--binding", str(binding), project=project
        )
        self.assertEqual(code, 0, data)
        return path, binding

    def test_absent_store_query_does_not_create_identity_or_db(self) -> None:
        code, data = self.invoke("summary")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "unavailable")
        self.assertIsNone(data["totals"])
        self.assertFalse((self.workplace / "data").exists())

    def test_shared_store_scope_summary_details_and_replay(self) -> None:
        path, binding = self.import_source(0, 100)
        self.import_source(1, 200)
        first = WorkplaceAccounting.discover(self.projects[0])
        second = WorkplaceAccounting.discover(self.projects[1])
        self.assertEqual(first.database, second.database)
        self.assertEqual(first.ensure_identity(), second.ensure_identity())
        self.assertEqual(self.invoke("summary")[1]["totals"]["input_total"], 100)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.invoke("summary", "--scope", "workplace")[1]["totals"][
                    "input_total"
                ],
                300,
            )
            listed = self.invoke("projects", "--scope", "workplace")[1]
        self.assertEqual([item["project_id"] for item in listed["items"]], ["a", "b"])
        self.assertEqual(self.invoke("summary", "--project-id", "b")[0], 1)
        code, detail = self.invoke(
            "attempt", "--run", "run", "--task", "task", "--attempt", "1"
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(detail["items"]), 1)
        encoded = json.dumps(detail)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("source_hash", encoded)
        self.assertNotIn("source_ref", encoded)
        replayed = self.invoke(
            "replay", "--file", str(path), "--binding", str(binding)
        )[1]
        self.assertEqual(replayed["collection"]["stored"], 0)

    def test_invalid_timestamp_import_returns_json_and_keeps_prefix(self) -> None:
        path, binding = self.import_source()
        prefix = path.read_bytes()
        for bad_timestamp in (None, 123, [], {}):
            with self.subTest(timestamp=bad_timestamp):
                path.write_bytes(
                    prefix
                    + json.dumps(
                        {
                            "type": "turn.completed",
                            "timestamp": bad_timestamp,
                            "usage": {"input_tokens": 1, "output_tokens": 1},
                        }
                    ).encode()
                    + b"\n"
                )
                code, data = self.invoke(
                    "import", "--file", str(path), "--binding", str(binding)
                )
                self.assertEqual(code, 2)
                self.assertEqual(data["collection"]["error"], "malformed_receipt")
                self.assertEqual(self.invoke("summary")[1]["totals"]["total"], 110)

    def test_managed_invocation_cannot_choose_workplace_scope(self) -> None:
        with patch.dict(os.environ, {"PF_TASK_ID": "task"}):
            self.assertEqual(self.invoke("summary", "--scope", "workplace")[0], 1)

    def test_managed_invocation_cannot_switch_project_or_workplace(self) -> None:
        with patch.dict(
            os.environ, {"PF_TASK_ID": "task", "PF_PROJECT_ROOT": str(self.projects[0])}
        ):
            self.assertEqual(self.invoke("summary")[0], 0)
            self.assertEqual(self.invoke("summary", project=1)[0], 1)
            alternate = self.root / "alternate"
            alternate.mkdir()
            (alternate / "workplace.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            self.assertEqual(
                self.invoke("summary", "--workplace", str(alternate))[0], 1
            )

    def test_wrong_project_binding_does_not_create_store(self) -> None:
        binding = self.root / "bad.json"
        binding.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "primary_records": True,
                    "attribution": {"project_id": "b"},
                }
            ),
            encoding="utf-8",
        )
        code, _ = self.invoke("import", "--file", "missing", "--binding", str(binding))
        self.assertEqual(code, 1)
        self.assertFalse((self.workplace / "data").exists())

    def test_no_project_name_or_installation_fallback(self) -> None:
        (self.projects[0] / ".pf" / "process-forge.yaml").write_text(
            "project: {}\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "explicit_pf_project_id"):
            WorkplaceAccounting.discover(self.projects[0])
        (self.projects[1] / ".pf" / "process-forge.local.yaml").unlink()
        with self.assertRaisesRegex(ValueError, "configured_workplace"):
            WorkplaceAccounting.discover(self.projects[1])

    def test_read_queries_do_not_run_creating_repository_constructor(self) -> None:
        self.import_source()
        with patch(
            "processforge_core.accounting.storage.SQLiteAccountingRepository.__init__",
            side_effect=AssertionError("query attempted database creation"),
        ):
            self.assertEqual(self.invoke("summary")[0], 0)

    def test_missing_origin_does_not_create_a_second_origin_for_existing_store(
        self,
    ) -> None:
        self.import_source()
        composition = WorkplaceAccounting.discover(self.projects[0])
        (composition.directory / "identity.json").unlink()
        with self.assertRaisesRegex(AccountingStorageError, "origin_missing"):
            composition.ensure_identity()
        self.assertFalse((composition.directory / "identity.json").exists())

    def test_driver_capture_real_subprocess_synthetic_receipt_failed_exit(self) -> None:
        output = self.root / "report.txt"
        environment = {
            "PF_RUN_ID": "run",
            "PF_TASK_ID": "task",
            "PF_WORKER_ATTEMPT": "1",
            "PF_AGENT_RUN_DIR": str(self.root / "attempt"),
        }
        with patch.dict(os.environ, environment):
            capture = ManagedUsageCapture(self.projects[0], output, "synthetic-model")
            handle = capture.begin()
            self.assertIsNotNone(handle)
            capture.start_execution()
            script = "import sys,json; print(json.dumps({'type':'turn.completed','usage':{'input_tokens':7,'output_tokens':3}})); sys.exit(9)"
            result = subprocess.run(
                [sys.executable, "-c", script], stdout=handle, check=False
            )
            capture.finish()
        self.assertEqual(result.returncode, 9)
        self.assertEqual(self.invoke("summary")[1]["totals"]["total"], 10)
        self.assertEqual(
            self.invoke("details", "--kind", "activity")[1]["coverage"][
                "activity_intervals"
            ],
            1,
        )
        self.assertTrue((capture.directory / "codex.jsonl").is_file())

    def test_metadata_io_does_not_skew_execution_clock_pair(self) -> None:
        capture = ManagedUsageCapture(self.projects[0], self.root / "report", "model")
        self.assertIsNotNone(capture.begin())
        seconds = [0.0]
        real_write = capture._write_json

        class Clock:
            @staticmethod
            def now(tz):
                return NOW + timedelta(seconds=seconds[0])

        def slow_write(name, data):
            seconds[0] += 2
            real_write(name, data)

        with (
            patch.object(codex_exec_worker, "datetime", Clock),
            patch.object(
                codex_exec_worker.time, "monotonic", side_effect=lambda: seconds[0]
            ),
            patch.object(capture, "_write_json", side_effect=slow_write),
        ):
            capture.start_execution()
            seconds[0] += 10
            capture.finish()
        timing = json.loads((capture.directory / "timing.json").read_text())
        self.assertEqual(timing["elapsed_seconds"], 10)
        self.assertEqual(
            (
                datetime.fromisoformat(timing["wall_end"])
                - datetime.fromisoformat(timing["start"])
            ).total_seconds(),
            10,
        )
        summary = self.invoke("summary")[1]
        self.assertEqual(summary["execution_seconds"], 10)
        self.assertEqual(summary["occupied_seconds"], 10)
        self.assertEqual(summary["coverage"]["clock_quality"]["aligned"], 1)
        clipped = self.invoke(
            "summary",
            "--start",
            (NOW + timedelta(seconds=3)).isoformat(),
            "--end",
            (NOW + timedelta(seconds=9)).isoformat(),
        )[1]
        self.assertEqual(clipped["execution_seconds"], 6)

    def test_driver_accounting_failure_keeps_raw_and_exit(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "PF_AGENT_RUN_DIR": str(self.root / "attempt"),
                    "PF_WORKER_ATTEMPT": "2",
                },
            ),
            patch(
                "processforge_core.accounting.composition.WorkplaceAccounting.discover",
                side_effect=OSError("PRIVATE PATH"),
            ),
        ):
            capture = ManagedUsageCapture(
                self.projects[0], self.root / "report", "model"
            )
            handle = capture.begin()
            result = subprocess.run(
                [sys.executable, "-c", "print('{}'); raise SystemExit(17)"],
                stdout=handle,
                check=False,
            )
            capture.finish()
        self.assertEqual(result.returncode, 17)
        evidence = json.loads((capture.directory / "collection-error.json").read_text())
        self.assertNotIn("PRIVATE PATH", json.dumps(evidence))
        self.assertEqual((capture.directory / "codex.jsonl").read_text().strip(), "{}")

    def test_interrupted_capture_has_unknown_duration_and_partial_coverage(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {"PF_AGENT_RUN_DIR": str(self.root / "attempt"), "PF_WORKER_ATTEMPT": "4"},
        ):
            capture = ManagedUsageCapture(
                self.projects[0], self.root / "report", "model"
            )
            handle = capture.begin()
            capture.start_execution()
            handle.close()  # Simulate interruption before the finalizer runs.
        data = self.invoke("summary")[1]
        self.assertIsNone(data["execution_seconds"])
        self.assertIsNone(data["totals"]["input_total"])
        self.assertEqual(data["coverage"]["unknown_duration"], 1)
        self.assertEqual(data["coverage"]["declared_sources"]["partial"], 1)
        replay = self.invoke(
            "replay",
            "--file",
            str(capture.directory / "codex.jsonl"),
            "--binding",
            str(capture.directory / "binding.json"),
            "--timing",
            str(capture.directory / "timing.json"),
        )
        self.assertEqual(replay[0], 0)
        self.assertEqual(self.invoke("summary")[1]["coverage"]["activity_intervals"], 1)

    def test_existing_attempt_evidence_not_overwritten(self) -> None:
        with patch.dict(
            os.environ,
            {"PF_AGENT_RUN_DIR": str(self.root / "attempt"), "PF_WORKER_ATTEMPT": "3"},
        ):
            first = ManagedUsageCapture(self.projects[0], self.root / "report", "model")
            first.begin()
            first.receipt.write(b"{}\n")
            first.finish()
            before = {p.name: p.read_bytes() for p in first.directory.iterdir()}
            second = ManagedUsageCapture(
                self.projects[0], self.root / "report", "model"
            )
            self.assertIsNone(second.begin())
            second.finish()
            self.assertEqual(
                before, {p.name: p.read_bytes() for p in first.directory.iterdir()}
            )

    def test_worker_main_preserves_json_report_heartbeat_exit_on_accounting_error(
        self,
    ) -> None:
        output = self.root / "final-report.md"
        heartbeat = self.root / "heartbeat.json"
        exit_path = self.root / "exit.json"
        prompt = self.root / "prompt.md"
        prompt.write_text("synthetic prompt", encoding="utf-8")
        capsule = self.root / "capsule.yaml"
        capsule.write_text("synthetic: true", encoding="utf-8")
        access = self.root / "access.json"
        access.write_text("{}", encoding="utf-8")
        argv = [
            "worker",
            "--worker-prompt",
            str(prompt),
            "--capsule",
            str(capsule),
            "--workspace-access",
            str(access),
            "--output",
            str(output),
            "--heartbeat",
            str(heartbeat),
        ]

        def fake_run(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess:
            self.assertIn("--json", command)
            self.assertEqual(command[command.index("-o") + 1], str(output))
            self.assertFalse(kwargs["check"])
            kwargs["stdout"].write(
                b'{"type":"turn.completed","usage":{"output_tokens":2}}\n'
            )
            output.write_text("synthetic final report", encoding="utf-8")
            return subprocess.CompletedProcess(command, 7)

        with (
            patch.dict(
                os.environ,
                {
                    "PF_PROJECT_ROOT": str(self.projects[0]),
                    "PF_AGENT_MODEL": "synthetic-model",
                    "PF_AGENT_EXIT_PATH": str(exit_path),
                },
                clear=True,
            ),
            patch.object(sys, "argv", argv),
            patch.object(
                codex_exec_worker, "codex_executable", return_value="synthetic-codex"
            ),
            patch.object(codex_exec_worker, "capture_worker_input"),
            patch.object(codex_exec_worker.subprocess, "run", side_effect=fake_run),
            patch(
                "processforge_core.accounting.composition.WorkplaceAccounting.service",
                side_effect=OSError("PRIVATE"),
            ),
            patch(
                "processforge_core.diagnostics.operation", return_value=nullcontext()
            ),
        ):
            code = codex_exec_worker.main()
        self.assertEqual(code, 7)
        self.assertEqual(output.read_text(), "synthetic final report")
        self.assertEqual(json.loads(exit_path.read_text())["exit_code"], 7)
        self.assertEqual(json.loads(heartbeat.read_text())["status"], "failed")

    def test_bad_limits_and_half_open_window_rejected_before_missing_store(
        self,
    ) -> None:
        self.assertEqual(self.invoke("summary", "--limit", "0")[0], 1)
        self.assertEqual(self.invoke("summary", "--start", "2026-10-22T12:00:00")[0], 1)
        self.assertEqual(
            self.invoke(
                "summary", "--start", NOW.isoformat(), "--end", NOW.isoformat()
            )[0],
            1,
        )


if __name__ == "__main__":
    unittest.main()
