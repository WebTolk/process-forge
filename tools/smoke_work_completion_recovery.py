#!/usr/bin/env python3
"""Exercise interrupted terminal writes and fresh-service recovery in real PF fixtures."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import yaml
import processforge as core
from processforge_core.process_execution import ProcessExecutionService, canonical_fingerprint
from process_execution_smoke_support import fixture, stage_evidence

def require(condition, detail):
    if not condition:
        raise AssertionError(detail)

def prepare(service, started, project):
    for artifact, gate in [("brief", "prepare-ready"), ("change", "build-ready")]:
        result = service.transition(run_id=started["run_id"], outcome="completed", evidence=stage_evidence(artifact, gate))
        require(result.get("action") == "stage_transitioned", result)
    proof = project / (started["assignment_id"] + "-report.md")
    proof.write_text("accepted report", encoding="utf-8")
    evidence = stage_evidence("report", "verify-ready")
    evidence[0]["path"] = proof.name
    return proof, evidence

def paths(project, started):
    rid, aid = started["run_id"], started["assignment_id"]
    root = project / ".pf" / "runs" / rid
    return {
        "intent": root / "completion-intent.yaml",
        "assignment": project / ".pf" / "assignments" / (aid + ".yaml"),
        "run": root / "run.yaml", "summary": root / "summary.md",
        "handoff": project / ".pf" / "handoffs" / "runs" / (rid + "-handoff.md"),
        "index": root / "task-index.md",
        "projection": project / ".pf" / "artifacts" / "projections" / "process-execution-state.json",
    }

def interrupt(service, started, project, evidence, target, when):
    owned = paths(project, started)
    original_text, original_emit, original_unlink = ProcessExecutionService._atomic_text, core.emit_process_event, Path.unlink
    captured = {"hit": False, "intent": None}
    def save():
        if owned["intent"].is_file():
            captured["intent"] = yaml.safe_load(owned["intent"].read_text(encoding="utf-8"))
    def fail(operation):
        captured["hit"] = True
        save()
        if when == "after":
            operation()
            save()
        raise OSError(f"injected {when} {target}")
    def atomic(owner, path, content):
        matches = path == owned.get(target)
        if matches and target in {"assignment", "run"}:
            matches = yaml.safe_load(content).get("status") == ("done" if target == "assignment" else "completed")
        if matches and not captured["hit"]:
            fail(lambda: original_text(owner, path, content))
        return original_text(owner, path, content)
    def emit(project_root, event_type, **kwargs):
        if target == "event" and event_type == "run.completed" and not captured["hit"]:
            fail(lambda: original_emit(project_root, event_type, **kwargs))
        return original_emit(project_root, event_type, **kwargs)
    def unlink(path, *args, **kwargs):
        if target == "cleanup" and path == owned["intent"] and not captured["hit"]:
            fail(lambda: original_unlink(path, *args, **kwargs))
        return original_unlink(path, *args, **kwargs)
    try:
        with patch.object(ProcessExecutionService, "_atomic_text", atomic), patch.object(core, "emit_process_event", emit), patch.object(Path, "unlink", unlink):
            service.transition(run_id=started["run_id"], outcome="completed", evidence=evidence, notes="original completion note")
    except OSError as exc:
        require(str(exc) == f"injected {when} {target}", str(exc))
    else:
        raise AssertionError(f"fault not triggered: {when} {target}")
    require(captured["hit"], target)
    return captured["intent"]

def verify_final(project, started, intent):
    owned = paths(project, started)
    task = yaml.safe_load(owned["assignment"].read_text(encoding="utf-8"))
    run = yaml.safe_load(owned["run"].read_text(encoding="utf-8"))
    require(task["status"] == "done" and run["status"] == "completed", (task["status"], run["status"]))
    history = task["stage_history"]
    require([item["stage_id"] for item in history] == ["prepare", "build", "verify"], history)
    require(task["result"]["summary"] == "original completion note", task["result"])
    require(next(item for item in run["tasks"] if item["id"] == started["assignment_id"])["status"] == "done", run["tasks"])
    require(not owned["intent"].exists(), "journal remains")
    if intent:
        require(task["updated_at"] == run["updated_at"] == history[-1]["completed_at"] == intent["completed_at"], "completion time changed")
        require(task == intent["final"]["assignment"] and run == intent["final"]["run"], "terminal payload changed on retry")
        for key, journal_key in [("summary", "summary"), ("handoff", "handoff"), ("index", "task_index")]:
            require(owned[key].read_text(encoding="utf-8") == intent["final"][journal_key]["content"], f"{key} content changed on retry")
        events = [json.loads(line) for line in core.event_runtime_paths(project)[0].read_text(encoding="utf-8").splitlines() if line.strip()]
        for spec in intent["final"]["events"]:
            require(sum(item.get("event_id") == spec["event_id"] for item in events) == 1, spec)
    summary = owned["summary"].read_text(encoding="utf-8")
    require(all(f"`{stage}`" in summary for stage in ["prepare", "build", "verify"]), summary)
    require("summary.md" in owned["handoff"].read_text(encoding="utf-8"), "missing handoff summary")
    require(f"| `{started['assignment_id']}` | `done` |" in owned["index"].read_text(encoding="utf-8"), "task index is stale")
    projection = json.loads(owned["projection"].read_text(encoding="utf-8"))["state"]
    require(projection["run"]["status"] == "completed" and projection["assignment"]["status"] == "done", projection)

def test_failure_matrix():
    targets = ["run", "intent", "assignment", "summary", "handoff", "index", "projection", "event", "cleanup"]
    with fixture() as (workplace, project, first):
        for index, (target, when) in enumerate((target, when) for target in targets for when in ["before", "after"]):
            service = ProcessExecutionService(project, workplace, core)
            started = first if index == 0 else service.start(objective=f"Recover {when} {target}")
            require(started["action"] == "created_new", started)
            proof, evidence = prepare(service, started, project)
            intent = interrupt(service, started, project, evidence, target, when)
            pending = paths(project, started)["intent"].exists()
            if pending:
                proof.write_text("changed after commit intent", encoding="utf-8")
            fresh = ProcessExecutionService(project, workplace, core)
            selection = ({"run_id": started["run_id"]}, {"assignment_id": started["assignment_id"]}, {})[index % 3] if pending else {"run_id": started["run_id"]}
            operation = fresh.complete if index % 4 == 3 else fresh.transition
            result = operation(**selection, outcome="ignored-invalid-outcome" if pending else "completed", notes="ignored retry note" if pending else "original completion note")
            committed = target == "cleanup" and when == "after"
            require(result.get("action") == "run_completed" or (committed and result.get("reason") == "work_is_terminal"), result)
            verify_final(project, started, intent)
            owned = paths(project, started)
            before = {key: path.read_bytes() for key, path in owned.items() if key != "intent"}
            repeated = fresh.transition(run_id=started["run_id"], outcome="completed")
            require(repeated.get("reason") == "work_is_terminal", repeated)
            require(before == {key: path.read_bytes() for key, path in owned.items() if key != "intent"}, "terminal retry changed files")
            print(f"PASS: {when} {target}", flush=True)

def test_invalid_intents_fail_closed():
    with fixture() as (workplace, project, started):
        service = ProcessExecutionService(project, workplace, core)
        _proof, evidence = prepare(service, started, project)
        intent = interrupt(service, started, project, evidence, "assignment", "before")
        owned = paths(project, started)
        original = owned["intent"].read_bytes()
        files = {key: path.read_bytes() if path.exists() else None for key, path in owned.items() if key != "intent"}
        malformed = []
        value = deepcopy(intent); value["run_id"] = "other"; malformed.append(value)
        value = deepcopy(intent); value["final"]["summary"]["path"] = "../outside.md"; malformed.append(value)
        value = deepcopy(intent); value["final"]["run"]["status"] = "cancelled"; malformed.append(value)
        value = deepcopy(intent); value["final"]["run"]["process_execution"] = "malformed"; malformed.append(value)
        value = deepcopy(intent); value["final"]["summary"]["content"] = "corrupted"; malformed.append(value)
        # Ownership/status/pin checks must still reject structurally invalid
        # payloads even when their content fingerprint has been recomputed.
        for value in malformed[:-1]:
            value["fingerprint"] = canonical_fingerprint({key: item for key, item in value.items() if key != "fingerprint"})
        for value in ["invalid: [yaml", *malformed]:
            owned["intent"].write_text(value if isinstance(value, str) else yaml.safe_dump(value), encoding="utf-8")
            result = ProcessExecutionService(project, workplace, core).transition(run_id=started["run_id"], outcome="completed")
            require(result.get("reason") == "completion_intent_invalid", result)
            require(files == {key: path.read_bytes() if path.exists() else None for key, path in owned.items() if key != "intent"}, "invalid journal wrote terminal files")
        owned["intent"].write_bytes(original)
        recovered = ProcessExecutionService(project, workplace, core).transition(run_id=started["run_id"], outcome="completed")
        require(recovered.get("action") == "run_completed", recovered)
        verify_final(project, started, intent)
        print("PASS: malformed journals rejected without writes", flush=True)

def main():
    test_failure_matrix()
    test_invalid_intents_fail_closed()
    print("PASS: recoverable terminal completion")

if __name__ == "__main__":
    main()
