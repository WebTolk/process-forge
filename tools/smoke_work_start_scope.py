"""Explicit operator scope creates a natively pinned, executable Work."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core
from processforge_core.process_execution import ProcessExecutionService
from process_execution_smoke_support import fixture, stage_evidence


def records(project):
    return {str(p.relative_to(project)): p.read_bytes() for folder in
            ("assignments", "runs", "contexts/assignment-capsules")
            for p in (project / ".pf" / folder).rglob("*.yaml")}


def main():
    with fixture() as (workplace, project, initial):
        service = ProcessExecutionService(project, workplace, core)
        original = records(project)
        capsule = yaml.safe_load((project / ".pf/contexts/assignment-capsules" /
                                  (initial["assignment_id"] + ".capsule.yaml")).read_text(encoding="utf-8"))
        assert capsule["execution_contract"]["scope"]["allowed_files"] == []
        spec = {"schema_version": 1, "assignment": {
            "allowed_files": ["example.py", ".pf/artifacts/scoped/**"],
            "allowed_read_files": ["example.py"],
            "required_outputs": [{"id": "result", "path": ".pf/artifacts/scoped/result.md"}],
            "expected_report": {"artifact": ".pf/artifacts/scoped/result.md"},
        }}
        # Rejected declarations must not leave assignments/runs/capsules behind.
        bad = []
        for key, value in [("unknown", []), ("allowed_files", ["../escape"]),
                           ("allowed_read_files", ["C:/private"]), ("allowed_files", "*"),
                           ("allowed_actions", ["shell"]), ("execution_mode", "unknown"),
                           ("required_outputs", ["result"]), ("ownership", {"writer": "yes"})]:
            candidate = copy.deepcopy(spec)
            candidate["assignment"][key] = value
            bad.append(candidate)
        bad.extend([
            {**spec, "schema_version": True},
            {**spec, "assignment": {"allowed_files": ["example.py"], "forbidden_files": ["example.py"]}},
            {**spec, "assignment": {"allowed_actions": ["write_product"], "execution_mode": "read_only"}},
            {**spec, "assignment": {"allowed_actions": ["read"], "forbidden_actions": ["read"]}},
            {**spec, "assignment": {"execution_mode": "docs_only", "allowed_files": ["docs/guide.md"],
                                    "allowed_read_files": ["docs/guide.md"],
                                    "allowed_actions": ["read", "write_product"]}},
            {**spec, "assignment": {"allowed_files": [".pf/artifacts/implicit/**"],
                                    "allowed_read_files": ["example.py"],
                                    "allowed_actions": ["read", "write_artifact"],
                                    "required_outputs": [{"id": "implicit", "path": ".pf/artifacts/implicit/result.md"}],
                                    "expected_report": {"artifact": ".pf/artifacts/implicit/result.md"}}},
            {**spec, "assignment": {"allowed_files": [], "allowed_read_files": [], "allowed_actions": []}},
            {**spec, "assignment": {"required_sources": ["missing.md"]}},
            {**spec, "assignment": {"required_outputs": [{"id": "x", "path": "no-grant.md"}]}},
        ])
        for i, candidate in enumerate(bad):
            before = records(project)
            result = service.start(objective=f"Reject explicit scope {i}", scope_intent=candidate)
            assert result["action"] == "blocked", result
            assert records(project) == before, result

        planning = {"schema_version": 1, "assignment": {
            "execution_mode": "planning_only",
            "allowed_files": [".pf/artifacts/planning/**"],
            "allowed_read_files": ["example.py"],
            "allowed_actions": ["read", "write_artifact"],
            "required_outputs": [{"id": "plan", "path": ".pf/artifacts/planning/plan.md"}],
            "expected_report": {"artifact": ".pf/artifacts/planning/plan.md"},
        }}
        planned = service.start(objective="Explicit planning artifact scope", scope_intent=planning)
        assert planned["action"] == "created_new", planned
        assert planned["work_state"]["execution_readiness"]["status"] == "ready", planned
        planning_pin = project / ".pf/contexts/assignment-capsules" / (planned["assignment_id"] + ".capsule.yaml")
        planning_scope = yaml.safe_load(planning_pin.read_text(encoding="utf-8"))["execution_contract"]["scope"]
        assert "write_artifact" in planning_scope["allowed_actions"] and "write_product" not in planning_scope["allowed_actions"]

        # The public local CLI forwards input before standard immutable capture.
        path = project / "scope.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        command = [sys.executable, "-B", str(ROOT / "bin/pf.py"), "work-start", "--project-root",
                   str(project), "--workplace", str(workplace), "--objective", "Scoped CLI implementation",
                   "--scope-file", str(path), "--json"]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        assert completed.returncode == 0, completed.stdout + completed.stderr
        result = json.loads(completed.stdout)
        assert result["action"] == "created_new", result
        state = result["work_state"]
        assert state["process"]["pin_status"] == "pinned", state
        assert state["context"]["validation"]["status"] == "valid", state
        pin = project / ".pf/contexts/assignment-capsules" / (result["assignment_id"] + ".capsule.yaml")
        raw = pin.read_bytes()
        data = yaml.safe_load(raw)
        scope = data["execution_contract"]["scope"]
        assert "write_product" in scope["allowed_actions"] and "example.py" in scope["allowed_files"]
        assert state["context"]["checksum"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        again = service.start(objective="Scoped CLI implementation", scope_intent=spec)
        assert again["action"] == "continue_existing" and pin.read_bytes() == raw
        changed = copy.deepcopy(spec)
        changed["assignment"]["allowed_files"].append("extra.py")
        assert service.start(objective="Scoped CLI implementation", scope_intent=changed)["reason"] == "scope_intent_mismatch"
        assert pin.read_bytes() == raw
        before = records(project)
        assert service.start(objective="Overlapping work", scope_intent=spec)["reason"] == "write_scope_overlap"
        assert records(project) == before
        moved = service.transition(run_id=result["run_id"], assignment_id=result["assignment_id"],
                                   outcome="completed", evidence=stage_evidence("brief", "prepare-ready"), notes="Actual scoped transition")
        assert moved["action"] == "stage_transitioned", moved
        assert pin.read_bytes() == raw
        prior = {"run_id": initial["run_id"], "assignment_id": initial["assignment_id"],
                 "capsule_checksum": initial["context"]["checksum"]}
        successor = {"schema_version": 1, "assignment": {"allowed_files": ["other.py"]}, "predecessor": prior}
        created = service.start(objective="Explicit predecessor", scope_intent=successor)
        assert created["action"] == "created_new", created
        assert created["work_state"]["context"]["validation"]["status"] == "valid"
        successor["predecessor"]["capsule_checksum"] = "sha256:" + "0" * 64
        assert service.start(objective="Wrong predecessor", scope_intent=successor)["reason"] == "predecessor_changed"
        note = project / ".pf/handoffs/serial-transfer.md"
        note.write_text("Operator transferred the stopped fixture writer to its successor.\n", encoding="utf-8")
        transfer = copy.deepcopy(spec)
        transfer["predecessor"] = {"run_id": result["run_id"], "assignment_id": result["assignment_id"],
                                   "capsule_checksum": "sha256:" + hashlib.sha256(raw).hexdigest()}
        transfer["predecessor_handoff"] = ".pf/handoffs/serial-transfer.md"
        transferred = service.start(objective="Serial writer transfer", scope_intent=transfer)
        assert transferred["action"] == "created_new", transferred
        assert service.start(objective="Serial writer transfer", scope_intent=transfer)["action"] == "continue_existing"
        assert pin.read_bytes() == raw
        note.write_text("Changed handoff\n", encoding="utf-8")
        assert service.start(objective="Serial writer transfer", scope_intent=transfer)["reason"] == "scope_intent_mismatch"
        assert service.start(objective="Third writer", scope_intent=transfer)["reason"] == "write_scope_overlap"
        assert all((project / p).read_bytes() == value for p, value in original.items())
    print("PASS: explicit scope, negative no-publication cases, overlap, immutable reuse, predecessor and native pinned transition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
