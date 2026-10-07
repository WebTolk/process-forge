"""Characterize ordered Work transition publication and injected operations."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.composition import build_work_transition_commit_service
from processforge_core.process_execution import ProcessExecutionService


STAGE_OPERATIONS = [
    "clock", "task-status", "assignment-path", "assignment-write", "run-path",
    "run-write", "task-index", "state", "projection", "process.stage.completed",
    "process.stage.transitioned", "process.stage.started",
]
TERMINAL_OPERATIONS = [
    "clock", "build-intent", "intent-path", "intent-write", "replay-intent", "state", "advisory",
]


class RecordingOperations:
    def __init__(self, failure_at: str = ""):
        self.calls = []
        self.documents = {}
        self.failure_at = failure_at
        self.failure = OSError("required operation failed")
        self.intent = {"schema_version": 1, "notes": "first\nстрока", "opaque": {"kept": True}}
        self.run = {"id": "run", "status": "in_progress", "opaque": {"run": True}}
        self.assignment = {
            "id": "assignment", "stage": "old", "status": "in_progress", "created_at": "created",
            "stage_history": [{"stage_id": "earlier", "opaque": True}], "opaque": {"assignment": True},
            "stage_execution": {"started_at": "started", "evidence": [{"path": "proof.md", "opaque": True}]},
        }
        self.process = {"id": "process", "opaque": True}

    def call(self, name, args, kwargs, effect):
        self.calls.append((name, args, kwargs))
        if name == self.failure_at:
            raise self.failure
        return effect()

    def callback(self, name, effect):
        return lambda *args, **kwargs: self.call(name, args, kwargs, lambda: effect(*args, **kwargs))

    def atomic_yaml(self, path, document):
        name = "assignment-write" if path.name == "assignment.yaml" else "run-write"
        return self.call(name, (path, document), {}, lambda: self.documents.update({path.name: copy.deepcopy(document)}))

    def emit(self, event_type, *args, **kwargs):
        return self.call(event_type, args, kwargs, lambda: None)

    def dependencies(self):
        return {
            "now_utc": self.callback("clock", lambda: "now"),
            "set_run_task_status": self.callback("task-status", lambda run, _id, status: run.update({"task_status": status})),
            "assignment_path": self.callback("assignment-path", lambda _id: Path("assignment.yaml")),
            "run_path": self.callback("run-path", lambda _id: Path("run.yaml")),
            "atomic_yaml": self.atomic_yaml,
            "write_task_index": self.callback("task-index", lambda run: self.documents.update({"index": copy.deepcopy(run)})),
            "build_completion_intent": self.callback("build-intent", lambda *args, **kwargs: self.intent),
            "completion_intent_path": self.callback("intent-path", lambda _id: Path("intent.yaml")),
            "atomic_text": self.callback("intent-write", lambda path, text: self.documents.update({path.name: text})),
            "replay_completion_intent": self.callback("replay-intent", lambda *args, **kwargs: {"action": "unused-replay-result"}),
            "state": self.callback("state", lambda **selectors: {"action": "state", "opaque_state": True, "selectors": selectors}),
            "write_projection": self.callback("projection", lambda state: self.documents.update({"projection": copy.deepcopy(state)})),
            "emit": self.emit,
            "next_work_advisory": self.callback("advisory", lambda *args: {"next": {"advisory": True}}),
        }

    def inputs(self, *, terminal=False):
        return {"run": self.run, "assignment": self.assignment, "process": self.process,
                "stage_id": "old", "next_stage_id": "" if terminal else "next",
                "outcome": "completed", "notes": "new\nnote", "session_id": "session"}


class WorkTransitionCommitTests(unittest.TestCase):
    def test_stage_publication_and_event_order_preserve_records(self):
        ops = RecordingOperations()
        history = ops.assignment["stage_history"]
        evidence = ops.assignment["stage_execution"]["evidence"]
        opaque = ops.assignment["opaque"]
        result = build_work_transition_commit_service(**ops.dependencies()).commit(**ops.inputs())
        self.assertEqual([c[0] for c in ops.calls], STAGE_OPERATIONS)
        self.assertIs(ops.assignment["stage_history"], history)
        self.assertIs(ops.assignment["opaque"], opaque)
        self.assertEqual(history[-1], {"stage_id": "old", "status": "completed", "started_at": "started",
                         "completed_at": "now", "outcome": "completed", "next_stage_id": "next",
                         "evidence": evidence, "notes": "new\nnote"})
        self.assertIsNot(history[-1]["evidence"], evidence)
        self.assertIs(history[-1]["evidence"][0], evidence[0])
        self.assertEqual(ops.assignment["stage_execution"], {"started_at": "now", "evidence": [], "notes": ""})
        self.assertEqual(ops.documents["assignment.yaml"], ops.assignment)
        self.assertEqual(ops.documents["run.yaml"], ops.run)
        self.assertEqual(result["action"], "stage_transitioned")
        self.assertEqual((result["previous_stage_id"], result["next_stage_id"]), ("old", "next"))
        self.assertTrue(result["opaque_state"])
        self.assertEqual(ops.calls[-3][1][-1], "old")
        self.assertEqual(ops.calls[-2][1][-1], "next")
        self.assertEqual(ops.calls[-1][2]["outcome"], "started")

    def test_terminal_intent_precedes_replay_and_fresh_state(self):
        ops = RecordingOperations()
        result = build_work_transition_commit_service(**ops.dependencies()).commit(**ops.inputs(terminal=True))
        self.assertEqual([c[0] for c in ops.calls], TERMINAL_OPERATIONS)
        text = ops.documents["intent.yaml"]
        self.assertEqual(text, json.dumps(ops.intent, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        self.assertEqual(json.loads(text), ops.intent)
        self.assertIs(ops.calls[4][1][0], ops.intent)
        self.assertEqual(ops.calls[4][2], {"session_id": "session"})
        self.assertEqual(ops.calls[5][2], {"run_id": "run", "assignment_id": "assignment", "session_id": "session"})
        self.assertEqual(result["action"], "run_completed")
        self.assertEqual(result["next"], {"advisory": True})
        self.assertEqual(result["next_stage_id"], "")

    def test_stage_required_failures_stop_at_exact_prefix(self):
        for name in ["assignment-write", "run-write", "task-index", "state", "projection", *STAGE_OPERATIONS[-3:]]:
            with self.subTest(operation=name):
                ops = RecordingOperations(failure_at=name)
                service = build_work_transition_commit_service(**ops.dependencies())
                with self.assertRaises(OSError) as caught:
                    service.commit(**ops.inputs())
                self.assertIs(caught.exception, ops.failure)
                self.assertEqual([c[0] for c in ops.calls], STAGE_OPERATIONS[:STAGE_OPERATIONS.index(name) + 1])
                if STAGE_OPERATIONS.index(name) > STAGE_OPERATIONS.index("assignment-write"):
                    self.assertIn("assignment.yaml", ops.documents)

    def test_replay_failure_keeps_published_intent_and_stops(self):
        ops = RecordingOperations(failure_at="replay-intent")
        with self.assertRaises(OSError) as caught:
            build_work_transition_commit_service(**ops.dependencies()).commit(**ops.inputs(terminal=True))
        self.assertIs(caught.exception, ops.failure)
        self.assertEqual([c[0] for c in ops.calls], TERMINAL_OPERATIONS[:5])
        self.assertEqual(json.loads(ops.documents["intent.yaml"]), ops.intent)

    def test_construction_is_frozen_keyword_only_and_performs_no_operations(self):
        ops = RecordingOperations()
        service = build_work_transition_commit_service(**ops.dependencies())
        self.assertFalse(ops.calls)
        self.assertEqual(repr(service), "WorkTransitionCommitService()")
        self.assertTrue(all(p.kind == inspect.Parameter.KEYWORD_ONLY for p in inspect.signature(type(service)).parameters.values()))
        with self.assertRaises(FrozenInstanceError):
            service.state = lambda **kwargs: {}

    def test_facade_constructor_and_late_callback_override(self):
        self.assertEqual(ProcessExecutionService.__match_args__, ("project_root", "workplace_root", "core"))
        self.assertEqual(list(inspect.signature(ProcessExecutionService).parameters),
                         ["project_root", "workplace_root", "core", "observer", "records", "context", "definitions", "snapshots"])
        ops = RecordingOperations()
        dependencies = ops.dependencies()
        core = SimpleNamespace(now_utc=dependencies["now_utc"])
        facade = ProcessExecutionService(Path("."), None, core)
        for name, callback in dependencies.items():
            if name != "now_utc":
                object.__setattr__(facade, name if name == "state" else "_" + name, callback)
        service = facade._work_transition_commit_service()
        self.assertFalse(ops.calls)
        def replacement_state(**selectors):
            return {**dependencies["state"](**selectors), "replacement": True}
        object.__setattr__(facade, "state", replacement_state)
        self.assertTrue(service.commit(**ops.inputs())["replacement"])

    def test_leaf_import_has_no_transport_or_legacy_load(self):
        code = "import sys; import processforge_core.work_transition_commit; assert not ({'processforge_legacy', 'tools.processforge', 'processforge_core.host', 'pf_runtime.service'} & set(sys.modules))"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT,
                                env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
