"""Characterize ordered Work transition publication and injected operations."""

from __future__ import annotations

import copy
import inspect
import json
import os
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from typing import TypedDict, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from processforge_core.composition import build_work_transition_commit_service
from processforge_core.process_execution import ProcessExecutionService

ROOT = Path(__file__).resolve().parents[1]


STAGE_OPERATIONS = [
    "clock",
    "task-status",
    "build-intent",
    "intent-path",
    "intent-write",
    "replay-intent",
]
TERMINAL_OPERATIONS = [
    "clock",
    "build-intent",
    "intent-path",
    "intent-write",
    "replay-intent",
    "state",
    "advisory",
]


class RecordedHistoryEntry(TypedDict, total=False):
    stage_id: str
    opaque: bool
    evidence: list[dict[str, str | bool]]


class RecordedStageExecution(TypedDict):
    started_at: str
    evidence: list[dict[str, str | bool]]


class RecordedAssignment(TypedDict):
    id: str
    stage: str
    status: str
    created_at: str
    stage_history: list[RecordedHistoryEntry]
    opaque: dict[str, bool]
    stage_execution: RecordedStageExecution


class RecordingOperations:
    def __init__(self, failure_at: str = ""):
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.documents: dict[str, str | dict[str, object]] = {}
        self.failure_at = failure_at
        self.failure = OSError("required operation failed")
        self.intent = {
            "schema_version": 1,
            "notes": "first\nстрока",
            "opaque": {"kept": True},
        }
        self.run = {"id": "run", "status": "in_progress", "opaque": {"run": True}}
        self.assignment: RecordedAssignment = {
            "id": "assignment",
            "stage": "old",
            "status": "in_progress",
            "created_at": "created",
            "stage_history": [{"stage_id": "earlier", "opaque": True}],
            "opaque": {"assignment": True},
            "stage_execution": {
                "started_at": "started",
                "evidence": [{"path": "proof.md", "opaque": True}],
            },
        }
        self.process = {"id": "process", "opaque": True}

    def call(self, name, args, kwargs, effect):
        self.calls.append((name, args, kwargs))
        if name == self.failure_at:
            raise self.failure
        return effect()

    def callback(self, name, effect):
        return lambda *args, **kwargs: self.call(
            name, args, kwargs, lambda: effect(*args, **kwargs)
        )

    def atomic_yaml(self, path, document):
        name = "assignment-write" if path.name == "assignment.yaml" else "run-write"
        return self.call(
            name,
            (path, document),
            {},
            lambda: self.documents.update({path.name: copy.deepcopy(document)}),
        )

    def emit(self, event_type, *args, **kwargs):
        return self.call(event_type, args, kwargs, lambda: None)

    def dependencies(self):
        return {
            "now_utc": self.callback("clock", lambda: "now"),
            "set_run_task_status": self.callback(
                "task-status",
                lambda run, _id, status: run.update({"task_status": status}),
            ),
            "assignment_path": self.callback(
                "assignment-path", lambda _id: Path("assignment.yaml")
            ),
            "run_path": self.callback("run-path", lambda _id: Path("run.yaml")),
            "atomic_yaml": self.atomic_yaml,
            "write_task_index": self.callback(
                "task-index",
                lambda run: self.documents.update({"index": copy.deepcopy(run)}),
            ),
            "build_completion_intent": self.callback(
                "build-intent", lambda *args, **kwargs: self.intent
            ),
            "completion_intent_path": self.callback(
                "intent-path", lambda _id: Path("intent.yaml")
            ),
            "atomic_text": self.callback(
                "intent-write",
                lambda path, text: self.documents.update({path.name: text}),
            ),
            "replay_completion_intent": self.callback(
                "replay-intent",
                lambda *args, **kwargs: {
                    "opaque_state": True,
                    "action": "stage_transitioned",
                    "previous_stage_id": "old",
                    "next_stage_id": "next",
                },
            ),
            "state": self.callback(
                "state",
                lambda **selectors: {
                    "action": "state",
                    "opaque_state": True,
                    "selectors": selectors,
                },
            ),
            "write_projection": self.callback(
                "projection",
                lambda state: self.documents.update(
                    {"projection": copy.deepcopy(state)}
                ),
            ),
            "emit": self.emit,
            "next_work_advisory": self.callback(
                "advisory", lambda *args: {"next": {"advisory": True}}
            ),
        }

    def inputs(self, *, terminal=False):
        return {
            "run": self.run,
            "assignment": self.assignment,
            "process": self.process,
            "stage_id": "old",
            "next_stage_id": "" if terminal else "next",
            "outcome": "completed",
            "notes": "new\nnote",
            "session_id": "session",
        }


class WorkTransitionCommitTests(unittest.TestCase):
    def test_stage_publication_and_event_order_preserve_records(self):
        ops = RecordingOperations()
        history = ops.assignment["stage_history"]
        evidence = ops.assignment["stage_execution"]["evidence"]
        opaque = ops.assignment["opaque"]
        result = build_work_transition_commit_service(**ops.dependencies()).commit(
            **ops.inputs()
        )
        self.assertEqual([c[0] for c in ops.calls], STAGE_OPERATIONS)
        self.assertIs(ops.assignment["stage_history"], history)
        self.assertIs(ops.assignment["opaque"], opaque)
        self.assertEqual(
            history[-1],
            {
                "stage_id": "old",
                "status": "completed",
                "started_at": "started",
                "completed_at": "now",
                "outcome": "completed",
                "next_stage_id": "next",
                "evidence": evidence,
                "notes": "new\nnote",
            },
        )
        self.assertIsNot(history[-1]["evidence"], evidence)
        self.assertIs(history[-1]["evidence"][0], evidence[0])
        self.assertEqual(
            ops.assignment["stage_execution"],
            {"started_at": "now", "evidence": [], "notes": ""},
        )
        self.assertEqual(
            json.loads(cast(str, ops.documents["intent.yaml"])), ops.intent
        )
        built = ops.calls[2]
        self.assertIs(built[1][0], ops.run)
        self.assertIs(built[1][1], ops.assignment)
        self.assertEqual(built[2]["next_stage_id"], "next")
        self.assertEqual(result["action"], "stage_transitioned")
        self.assertEqual(
            (result["previous_stage_id"], result["next_stage_id"]), ("old", "next")
        )
        self.assertTrue(result["opaque_state"])
        self.assertIs(ops.calls[-1][1][0], ops.intent)
        self.assertEqual(ops.calls[-1][2], {"session_id": "session"})

    def test_terminal_intent_precedes_replay_and_fresh_state(self):
        ops = RecordingOperations()
        result = build_work_transition_commit_service(**ops.dependencies()).commit(
            **ops.inputs(terminal=True)
        )
        self.assertEqual([c[0] for c in ops.calls], TERMINAL_OPERATIONS)
        text = cast(str, ops.documents["intent.yaml"])
        self.assertEqual(
            text,
            json.dumps(ops.intent, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )
        self.assertEqual(json.loads(text), ops.intent)
        self.assertIs(ops.calls[4][1][0], ops.intent)
        self.assertEqual(ops.calls[4][2], {"session_id": "session"})
        self.assertEqual(
            ops.calls[5][2],
            {"run_id": "run", "assignment_id": "assignment", "session_id": "session"},
        )
        self.assertEqual(result["action"], "run_completed")
        self.assertEqual(result["next"], {"advisory": True})
        self.assertEqual(result["next_stage_id"], "")

    def test_stage_required_failures_stop_at_exact_prefix(self):
        for name in ["build-intent", "intent-path", "intent-write", "replay-intent"]:
            with self.subTest(operation=name):
                ops = RecordingOperations(failure_at=name)
                service = build_work_transition_commit_service(**ops.dependencies())
                with self.assertRaises(OSError) as caught:
                    service.commit(**ops.inputs())
                self.assertIs(caught.exception, ops.failure)
                self.assertEqual(
                    [c[0] for c in ops.calls],
                    STAGE_OPERATIONS[: STAGE_OPERATIONS.index(name) + 1],
                )
                if name == "replay-intent":
                    self.assertIn("intent.yaml", ops.documents)

    def test_replay_failure_keeps_published_intent_and_stops(self):
        ops = RecordingOperations(failure_at="replay-intent")
        with self.assertRaises(OSError) as caught:
            build_work_transition_commit_service(**ops.dependencies()).commit(
                **ops.inputs(terminal=True)
            )
        self.assertIs(caught.exception, ops.failure)
        self.assertEqual([c[0] for c in ops.calls], TERMINAL_OPERATIONS[:5])
        self.assertEqual(
            json.loads(cast(str, ops.documents["intent.yaml"])), ops.intent
        )

    def test_construction_is_frozen_keyword_only_and_performs_no_operations(self):
        ops = RecordingOperations()
        service = build_work_transition_commit_service(**ops.dependencies())
        self.assertFalse(ops.calls)
        self.assertEqual(repr(service), "WorkTransitionCommitService()")
        self.assertTrue(
            all(
                p.kind == inspect.Parameter.KEYWORD_ONLY
                for p in inspect.signature(type(service)).parameters.values()
            )
        )
        with self.assertRaises(FrozenInstanceError):
            setattr(service, "state", lambda **kwargs: {})

    def test_facade_constructor_and_late_callback_override(self):
        self.assertEqual(
            ProcessExecutionService.__match_args__,
            ("project_root", "workplace_root", "core"),
        )
        parameters = inspect.signature(ProcessExecutionService).parameters
        self.assertEqual(
            list(parameters),
            [
                "project_root",
                "workplace_root",
                "core",
                "observer",
                "records",
                "context",
                "definitions",
                "snapshots",
                "work_metadata",
                "output_checks",
                "verification_fingerprint",
            ],
        )
        self.assertEqual(
            parameters["work_metadata"].kind, inspect.Parameter.KEYWORD_ONLY
        )
        self.assertIsNone(parameters["work_metadata"].default)
        ops = RecordingOperations()
        dependencies = ops.dependencies()
        core = SimpleNamespace(now_utc=dependencies["now_utc"])
        facade = ProcessExecutionService(Path("."), None, core)
        object.__setattr__(facade, "_clock", dependencies["now_utc"])
        for name, callback in dependencies.items():
            if name != "now_utc":
                object.__setattr__(
                    facade, name if name == "state" else "_" + name, callback
                )
        service = facade._work_transition_commit_service()
        self.assertFalse(ops.calls)

        def replacement_state(**selectors):
            return {**dependencies["state"](**selectors), "replacement": True}

        object.__setattr__(facade, "state", replacement_state)
        self.assertTrue(service.commit(**ops.inputs(terminal=True))["replacement"])

    def test_leaf_import_has_no_transport_or_legacy_load(self):
        code = "import sys; import processforge_core.work.transition_commit; assert not ({'processforge_legacy', 'tools.processforge', 'processforge_core.host', 'pf_runtime.service'} & set(sys.modules))"
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=ROOT,
            env={
                **os.environ,
                "PYTHONPATH": str(ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class FixtureRun(TypedDict):
    id: str
    status: str
    process: str
    process_execution: dict[str, object]
    tasks: list[dict[str, str]]


class LifecycleRecoveryTests(unittest.TestCase):
    """Exercise the real caller, readers, publishers and journal deduplication.

    The fixture contains already selected, pinned synthetic records. It does
    not bootstrap a workplace, start Work or qualify managed storage/hooks.
    Event admission uses the source journal SQL adapter on an owned SQLite
    fixture; external dispatch and device configuration are deliberately absent.
    """

    def setUp(self):
        import sqlite3

        import processforge as core

        from processforge_core.maintenance.temporary_disposal import (
            CleanupError,
            create_owned_directory,
            dispose_owned,
            release_owned,
        )
        from processforge_core.process_event_journal import SCHEMA
        from processforge_core.process_execution import canonical_fingerprint

        # Match existing owned scratch: inherit Windows access, keep POSIX 0700.
        resource = create_owned_directory(Path(os.environ["PF_TEST_SCRATCH_ROOT"]))

        def cleanup() -> None:
            receipt = dispose_owned(release_owned(resource))
            if receipt.result not in {"deleted", "already_absent"}:
                raise CleanupError(receipt.error_code or 0, receipt.result)

        self.directory = SimpleNamespace(name=str(resource.path), cleanup=cleanup)
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        self.core = core
        self.process = {
            "id": "fixture",
            "version": "1.0.0",
            "stages": [{"id": stage} for stage in ("first", "second", "third")],
        }
        pin: dict[str, object] = {
            "definition": self.process,
            "process_id": "fixture",
            "process_version": "1.0.0",
            "process_fingerprint": canonical_fingerprint(self.process),
            "snapshot_id": "fixture-snapshot",
            "snapshot_checksum": "fixture-checksum",
        }
        self.run_document: FixtureRun = {
            "id": "run",
            "status": "in_progress",
            "process": "fixture",
            "process_execution": pin,
            "tasks": [{"id": "assignment", "status": "in_progress"}],
        }
        self.assignment = {
            "id": "assignment",
            "run_id": "run",
            "stage": "first",
            "status": "in_progress",
            "created_at": "created",
            "updated_at": "created",
            "stage_history": [],
            "stage_execution": {"started_at": "created", "evidence": [], "notes": ""},
            "allowed_actions": ["read", "write_artifact"],
            "allowed_files": ["proof.md"],
        }
        self.service = self.fresh()
        self.service._atomic_yaml(
            self.project / ".pf/process-forge.yaml", {"project": {"id": "fixture"}}
        )
        self.service._atomic_yaml(self.service._run_path("run"), self.run_document)
        self.service._atomic_yaml(
            self.service._assignment_path("assignment"), self.assignment
        )
        self.connection = sqlite3.connect(
            self.project / "events.sqlite3", isolation_level=None
        )
        self.addCleanup(self.connection.close)
        for statement in SCHEMA:
            self.connection.execute(statement)

    def fresh(self):
        owner = ProcessExecutionService(self.project, None, self.core)
        object.__setattr__(
            owner, "_process_events", SimpleNamespace(emit_process_event=self.record)
        )
        return owner

    def record(self, project_root, event_type, **kwargs):
        from processforge_core.process_event_journal import ProcessEventJournal
        from processforge_core.sqlite_storage import transaction

        self.assertEqual(project_root, self.project)
        event = {**kwargs, "event_type": event_type, "time": "fixture-time"}
        with transaction(self.connection):
            ProcessEventJournal._append(
                self.connection, event, lambda row: row["event_id"], True
            )
        return event

    def advance(self, service=None, **kwargs):
        return (service or self.service).transition(
            run_id="run",
            assignment_id="assignment",
            context_id="assignment-capsule",
            outcome=kwargs.pop("outcome", "completed"),
            **kwargs,
        )

    def capture_failure(self, target, when, terminal=False):
        from unittest.mock import patch

        original_text = ProcessExecutionService._atomic_text
        original_record = self.record
        original_state = ProcessExecutionService.state
        intent_path = self.service._completion_intent_path("run")
        captured = {}

        def fail(operation):
            captured["hit"] = True
            if when == "after":
                operation()
            if intent_path.exists():
                captured["intent"] = json.loads(intent_path.read_text(encoding="utf-8"))
            raise OSError(f"injected {when} {target}")

        def text(owner, path, content):
            kind = {
                intent_path: "intent",
                owner._assignment_path("assignment"): "assignment",
                owner._run_path("run"): "run",
                owner._run_path("run").parent / "task-index.md": "index",
                owner._flow_root()
                / "artifacts/projections/process-execution-state.json": "projection",
            }.get(path)
            # Admission's evidence write is not yet a stage advancement.
            matches = kind == target and not captured.get("hit")
            if matches and kind == "assignment":
                import yaml

                document = yaml.safe_load(content)
                matches = bool(document.get("stage_history"))
            if matches:
                return fail(lambda: original_text(owner, path, content))
            return original_text(owner, path, content)

        def event(project_root, event_type, **kwargs):
            if event_type == target and not captured.get("hit"):
                return fail(lambda: original_record(project_root, event_type, **kwargs))
            return original_record(project_root, event_type, **kwargs)

        def state(owner, **kwargs):
            if target == "state" and intent_path.exists() and not captured.get("hit"):
                return fail(lambda: original_state(owner, **kwargs))
            return original_state(owner, **kwargs)

        owner = self.fresh()
        object.__setattr__(
            owner, "_process_events", SimpleNamespace(emit_process_event=event)
        )
        with (
            patch.object(ProcessExecutionService, "_atomic_text", text),
            patch.object(ProcessExecutionService, "state", state),
        ):
            with self.assertRaisesRegex(OSError, f"injected {when} {target}"):
                self.advance(
                    owner,
                    notes="original note",
                    evidence=[{"kind": "note", "summary": "original evidence"}],
                )
        self.assertTrue(captured.get("hit"))
        return captured.get("intent")

    def verify_recovery(self, intent, result, terminal=False):
        self.assertEqual(
            result["action"], "run_completed" if terminal else "stage_transitioned"
        )
        self.assertEqual(result["previous_stage_id"], "first")
        self.assertEqual(result["next_stage_id"], "" if terminal else "second")
        assignment = self.service._load_assignment("assignment")
        run = self.service._load_run("run")
        self.assertEqual(len(assignment["stage_history"]), 1)
        self.assertEqual(assignment["stage_history"][0]["notes"], "original note")
        self.assertEqual(
            assignment["stage_history"][0]["evidence"],
            [{"kind": "note", "summary": "original evidence"}],
        )
        self.assertEqual(assignment["stage"], "first" if terminal else "second")
        if intent:
            self.assertEqual(assignment, intent["final"]["assignment"])
            self.assertEqual(run, intent["final"]["run"])
            self.assertEqual(
                (self.service._run_path("run").parent / "task-index.md").read_text(
                    encoding="utf-8"
                ),
                intent["final"]["task_index"]["content"],
            )
            specs = intent["final"]["events"]
            self.assertEqual(
                [
                    row[0]
                    for row in self.connection.execute(
                        "SELECT event_id FROM events ORDER BY seq"
                    )
                ],
                [spec["event_id"] for spec in specs],
            )
        self.assertEqual(
            self.connection.execute("SELECT count(*) FROM events").fetchone()[0],
            6 if terminal else 3,
        )
        projection = json.loads(
            (
                self.project / ".pf/artifacts/projections/process-execution-state.json"
            ).read_text(encoding="utf-8")
        )["state"]
        self.assertEqual(projection["stage"]["id"], assignment["stage"])
        self.assertEqual(projection["run"]["status"], run["status"])
        self.assertFalse(self.service._completion_intent_path("run").exists())

    def test_caller_fault_matrix(self):
        targets = [
            "intent",
            "assignment",
            "run",
            "index",
            "state",
            "projection",
            "process.stage.completed",
            "process.stage.transitioned",
            "process.stage.started",
        ]
        for target in targets:
            for when in ["before", "after"]:
                with self.subTest(target=target, when=when):
                    # Every matrix row owns independent files and a fresh journal.
                    if target != targets[0] or when != "before":
                        self.connection.close()
                        self.directory.cleanup()
                        self.setUp()
                    intent = self.capture_failure(target, when)
                    result = self.advance(
                        self.fresh(),
                        notes="retry note",
                        evidence=[{"kind": "note", "summary": "retry evidence"}],
                    )
                    # Before durable intent publication no advancement was accepted.
                    if intent is None:
                        self.assertEqual(result["action"], "stage_transitioned")
                        self.assertEqual(
                            len(
                                self.service._load_assignment("assignment")[
                                    "stage_history"
                                ]
                            ),
                            1,
                        )
                        self.assertEqual(
                            self.service._load_assignment("assignment")["stage"],
                            "second",
                        )
                        continue
                    self.assertTrue(result["recovered"])
                    self.verify_recovery(intent, result)
                    # A deliberate following invocation can still advance normally.
                    following = self.advance(self.fresh())
                    self.assertEqual(following["next_stage_id"], "third")
                    self.assertEqual(
                        len(
                            self.service._load_assignment("assignment")["stage_history"]
                        ),
                        2,
                    )

    def test_pending_replay_does_not_admit_new_request(self):
        intent = self.capture_failure("process.stage.transitioned", "after")
        result = self.advance(
            self.fresh(), outcome="invalid", evidence="invalid", notes="ignored"
        )
        self.verify_recovery(intent, result)

    def test_invalid_intents_fail_closed_without_writes(self):
        intent = self.capture_failure("projection", "before")
        intent_path = self.service._completion_intent_path("run")
        files = [
            self.service._run_path("run"),
            self.service._assignment_path("assignment"),
        ]
        before = [path.read_bytes() for path in files]
        original = intent_path.read_bytes()
        from processforge_core.process_execution import canonical_fingerprint

        changes = [
            lambda obj: obj.update(run_id="other"),
            lambda obj: obj["owner"].update(assignment_path="../other"),
            lambda obj: obj["final"]["task_index"].update(path="../other"),
            lambda obj: obj["transition"].update(next_stage_id="third"),
            lambda obj: obj["final"]["events"].pop(),
            lambda obj: obj["final"]["events"][0].update(event_id="different"),
            lambda obj: obj["final"]["run"]["process_execution"].update(
                snapshot_id="different"
            ),
            lambda obj: obj["final"]["assignment"].update(stage_history=[]),
            lambda obj: obj.update(transition=[]),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                changed = copy.deepcopy(intent)
                change(changed)
                changed["fingerprint"] = canonical_fingerprint(
                    {
                        key: value
                        for key, value in changed.items()
                        if key != "fingerprint"
                    }
                )
                intent_path.write_text(json.dumps(changed), encoding="utf-8")
                result = self.advance(self.fresh())
                self.assertEqual(result["reason"], "completion_intent_invalid")
                self.assertEqual([path.read_bytes() for path in files], before)
                self.assertEqual(
                    self.connection.execute("SELECT count(*) FROM events").fetchone()[
                        0
                    ],
                    0,
                )
        intent_path.write_bytes(original)
        self.verify_recovery(intent, self.advance(self.fresh()))

    def test_terminal_protocol_still_recovers(self):
        self.process["stages"] = [{"id": "first"}]
        from processforge_core.process_execution import canonical_fingerprint

        self.run_document["process_execution"]["process_fingerprint"] = (
            canonical_fingerprint(self.process)
        )
        self.service._atomic_yaml(self.service._run_path("run"), self.run_document)
        intent = self.capture_failure("projection", "after", terminal=True)
        result = self.advance(self.fresh(), outcome="invalid")
        self.verify_recovery(intent, result, terminal=True)
        self.assertEqual(self.advance(self.fresh())["reason"], "work_is_terminal")


if __name__ == "__main__":
    unittest.main()
