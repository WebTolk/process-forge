"""Real Work v1/v2 creation, immutable successor and managed CLI integration."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import processforge as core
import process_execution_smoke_support as support
import prepared_executor
from processforge_core.egress.contracts import EgressError, binding_for, digest, encoded, require_v2
from processforge_core.egress.service import work_session
from processforge_core.prepared_input import semantic_input
from processforge_core.process_execution import ProcessExecutionService
from processforge_core.work_context import validate_execution_contract
from processforge_core.work_resource_material import MaterialError, _resolve_source
from smoke_egress_engine import candidate_store, denied, policy_for, recipient

spec = importlib.util.spec_from_file_location("egress_schema_validation", ROOT / "tools/validate-process-forge-schemas.py")
schema_validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema_validation)


def schema_errors(schema, value):
    return schema_validation.validate_instance(value, schema, schema, "$")


def run_checks():
    checks = []
    with support.fixture() as (workplace, project, original):
        old_path = core.assignment_capsule_path(project, original["assignment_id"])
        old_bytes = old_path.read_bytes()
        old = yaml.safe_load(old_bytes)
        task = support.assignment(project, original)
        service = ProcessExecutionService(project, workplace, core)
        assert old["execution_contract"]["contract_version"] == 1 and "egress" not in old["execution_contract"]
        valid = validate_execution_contract(project, core.assignment_yaml_path(project, task["id"]), task, old, core, require_ready=True)
        assert valid["status"] == "valid", valid
        denied(lambda: require_v2(old["execution_contract"]), "egress_contract_required")
        checks.append("A23 actual v1 Work unchanged strict v1 rejected")

        with recipient() as (endpoint, captured):
            policy = policy_for(project, endpoint)
            security = {"egress": binding_for(policy), "allowed_read_files": sorted(policy["sources"]),
                        "predecessor": {"assignment_id": task["id"], "capsule_checksum": digest(old_bytes)}}
            mismatch = service.start(objective=task["objective"], process_id="declarative-smoke", security=security)
            assert mismatch.get("reason") == "security_intent_mismatch", mismatch
            created = service.start(objective="Qualify a governed egress successor", process_id="declarative-smoke", security=security)
            assert created["action"] == "created_new", created
            new_task = core.load_yaml_document(core.assignment_yaml_path(project, created["assignment_id"]))
            new_path = core.assignment_capsule_path(project, created["assignment_id"])
            new_bytes = new_path.read_bytes()
            capsule = yaml.safe_load(new_bytes)
            assert capsule["execution_contract"]["contract_version"] == 2
            assert old_path.read_bytes() == old_bytes
            valid = validate_execution_contract(project, core.assignment_yaml_path(project, new_task["id"]), new_task, capsule, core, require_ready=True)
            assert valid["status"] == "valid", valid
            checks.extend(["A23 successor sealed before lifecycle writes preserves predecessor", "A23 same-objective security mismatch never resumes v1"])

            schema = json.loads((ROOT / "schemas/execution-contract.schema.json").read_text(encoding="utf-8"))
            assert not schema_errors(schema, capsule["execution_contract"])
            capsule_schema = json.loads((ROOT / "schemas/context-capsule.schema.json").read_text(encoding="utf-8"))
            assert not schema_errors(capsule_schema, capsule), schema_errors(capsule_schema, capsule)
            legacy_schema = copy.deepcopy(schema)
            legacy_schema["properties"]["contract_version"] = {"const": 1}
            assert schema_errors(legacy_schema, capsule["execution_contract"])
            grafted = copy.deepcopy(old["execution_contract"])
            grafted["egress"] = security["egress"]
            assert schema_errors(schema, grafted)
            changed = copy.deepcopy(new_task)
            changed["egress"]["purpose"] = "changed"
            result = validate_execution_contract(project, core.assignment_yaml_path(project, new_task["id"]), changed, capsule, core)
            assert result["status"] == "blocked" and result["reason"] == "assignment_contract_changed", result
            checks.append("A23 schema version rejection and security intent tamper")

            try:
                semantic_input(project, new_task, capsule, core)
            except ValueError as exc:
                assert str(exc) == "enforcement_unavailable", str(exc)
            else:
                raise AssertionError("strict native input must not be built")
            manifest = project.parent / "prepared.json"
            doc = {"schema_version": 1, "kind": "pf.prepared-input", "input": {"contract_version": 2},
                   "project_root": str(project), "identity": {}}
            raw = encoded(doc)
            manifest.write_bytes(raw)
            options = argparse.Namespace(prepared_input=str(manifest), prepared_sha256=digest(raw))
            env = {"PF_PREPARED_INPUT_FILE": str(manifest), "PF_PREPARED_INPUT_SHA256": digest(raw)}
            with patch("subprocess.Popen", side_effect=AssertionError("must not launch")):
                try:
                    prepared_executor.load_and_validate_manifest(options, env)
                except prepared_executor.ExecutorError as exc:
                    assert exc.code == "enforcement_unavailable"
                else:
                    raise AssertionError("strict wrapper must reject")
            checks.append("A05 strict native preparation and wrapper reject before launch")

            policy_path = project.parent / "policy.json"
            policy_path.write_bytes(encoded(policy))
            store = candidate_store(project.parent / ".pf-egress-private", project)
            session = work_session(core, project=project, assignment_id=new_task["id"], attempt=1,
                                   policy_path=policy_path, store_root=store.root)
            result = session.run()
            assert result["status"] == "completed" and len(captured) == 1
            assert b"private" not in captured[0]["body"] and b"public.txt" not in captured[0]["body"]
            checks.append("A01 real governed Work to independently capturing broker")

            result = subprocess.run([sys.executable, "-B", str(ROOT / "bin/pf.py"), "egress", "run",
                                     "--project-root", str(project), "--assignment", new_task["id"], "--attempt", "2",
                                     "--policy", str(policy_path), "--store-root", str(store.root)], capture_output=True, timeout=90)
            assert result.returncode == 0, (result.stdout.decode(errors="replace"), result.stderr.decode(errors="replace"))
            assert json.loads(result.stdout)["enforcement"] == "mediated_session" and len(captured) == 2
            checks.append("A26 actual CLI connected loopback capture")

            # Current stage is live authority, not the immutable capsule's initial stage.
            session = work_session(core, project=project, assignment_id=new_task["id"], attempt=3,
                                   policy_path=policy_path, store_root=store.root)
            view = session.prepare_view()
            run_path = core.locate_flow_root(project) / "runs" / created["run_id"] / "run.yaml"
            with core.registry_file_lock(run_path):
                denied(lambda: session.authorize(view), "work_authority_busy")
            checks.append("A10 Work transition guard serializes disclosure authorization")
            advanced = service.transition(run_id=created["run_id"], assignment_id=new_task["id"], outcome="completed",
                                          evidence=support.stage_evidence("brief", "prepare-ready"), notes="Synthetic fixture stage completion")
            assert advanced["action"] == "stage_transitioned", advanced
            denied(lambda: session.authorize(view), "invalid_binding")
            session.close()
            assert new_path.read_bytes() == new_bytes and old_path.read_bytes() == old_bytes
            checks.append("A11 real stage transition revokes old view without capsule mutation")

            try:
                _resolve_source(store.root, ".")
            except MaterialError:
                pass
            else:
                raise AssertionError("private receipt store must not enter resource index")
            checks.append("A27 reserved private store excluded from Work material")
    return {"status": "passed", "checks": len(checks), "cases": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_checks()
    print(json.dumps(report, ensure_ascii=False) if args.json else "PASS " + str(report["checks"]) + " Work egress checks")
