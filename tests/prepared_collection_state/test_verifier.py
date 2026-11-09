"""Historical receipt semantics with the actual receipt producer and validator."""

from __future__ import annotations

import copy
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import yaml

from processforge_core.prepared import input as prepared
from processforge_core.work import context
from processforge_core.work.context_documents import ContextContractInputs


class FixtureCore:
    """Bounded filesystem/configuration ports, with no services or Work launch."""

    @staticmethod
    def project_id(project: Path) -> str:
        return "project"

    @staticmethod
    def locate_flow_root(project: Path) -> Path:
        return project / ".pf"

    @staticmethod
    def assignment_capsule_path(project: Path, task_id: str) -> Path:
        return (
            project / ".pf/contexts/assignment-capsules" / (task_id + ".capsule.yaml")
        )

    @staticmethod
    def rel(path: Path, project: Path) -> str:
        return path.relative_to(project).as_posix()

    @staticmethod
    def load_yaml_document(path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_bytes())

    @staticmethod
    def project_context_snapshot_paths(project: Path) -> tuple[Path, Path]:
        return project / ".pf/contexts/project-context.snapshot.yaml", project / ".pf"

    @staticmethod
    def normalize_execution_mode(value: Any) -> dict[str, Any]:
        return copy.deepcopy(value)

    @staticmethod
    def normalize_ownership(metadata: dict, allowed: list) -> dict:
        return {"writer": True, "owner_id": "worker", "owned_files": allowed}

    @staticmethod
    def normalize_non_overlap(value: Any, allowed: list) -> dict:
        return {"policy": "block_on_write_overlap"}

    @staticmethod
    def normalize_context_artifacts(value: Any) -> list:
        return []

    @staticmethod
    def normalize_workspace_access(value: Any) -> dict:
        return ContextContractInputs().normalize_workspace_access(value)

    @staticmethod
    def workspace_access_public_path_issues(value: Any) -> list:
        return []


@pytest.fixture
def accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Produce real receipt bytes; only preparation/resource ports are isolated."""
    project = tmp_path / "project"
    project.mkdir()
    core = FixtureCore()
    task: dict[str, Any] = {
        "id": "task",
        "run_id": "run",
        "stage": "stage-a",
        "process": "test",
        "objective": "bounded fixture",
        "allowed_files": [".pf/artifacts/**"],
        "allowed_actions": ["read", "write_artifact"],
        "execution_mode": {"kind": "implementation", "code_changes_allowed": True},
        "required_outputs": [
            {"id": "report", "path": ".pf/artifacts/report.md", "required": False},
            {"id": "optional", "path": ".pf/artifacts/optional.md", "required": False},
        ],
        "expected_report": {"artifact": ".pf/artifacts/report.md"},
    }
    assignment_path = project / ".pf/assignments/task.yaml"
    intent = context.assignment_intent(project, assignment_path, task, core)
    definition = {"id": "test", "stages": [{"id": "stage-a"}, {"id": "stage-b"}]}
    process = {
        "id": "test",
        "version": "1",
        "fingerprint": context.fingerprint(definition),
    }
    process_pin = {
        "process_id": "test",
        "process_version": "1",
        "process_fingerprint": process["fingerprint"],
        "definition": definition,
    }
    identity = {
        "kind": "work",
        "project_id": "project",
        "run_id": "run",
        "assignment_id": "task",
        "context_id": "context",
    }
    snapshot = {"id": "snapshot", "checksum": prepared.digest(b"snapshot")}
    contract = {
        "contract_version": 1,
        "identity": identity,
        "assignment_intent": intent,
        "assignment_intent_checksum": context.fingerprint(intent),
        "snapshot": snapshot,
        "process": process,
        "resources": {"selected_ids": [], "bindings_checksum": context.fingerprint({})},
        "scope": intent["scope"],
        "outputs": intent["outputs"],
        "capabilities": {"required": [], "optional": []},
        "workspace_access": intent["workspace_access"],
        "parameters": {},
        "coordination": {},
        "source_limits": context.SOURCE_LIMITS,
        "readiness": {"status": "ready", "blockers": []},
        "required_sources": [],
        "worker_may_rebuild_context": False,
    }
    contract["contract_checksum"] = context.fingerprint(contract)
    capsule = {
        "capsule": {"id": "context"},
        "execution_contract": contract,
        "resource_bindings": {},
        "context": {"selected_resource_ids": []},
        "context_snapshot": {"id": snapshot["id"], "sha256": snapshot["checksum"]},
        "process_execution": process_pin,
    }
    capsule_path = core.assignment_capsule_path(project, "task")
    capsule_path.parent.mkdir(parents=True)
    capsule_path.write_bytes(prepared.encoded(capsule))
    task["process_execution"] = {
        **process_pin,
        "assignment_capsule": core.rel(capsule_path, project),
        "assignment_capsule_checksum": prepared.digest(capsule_path.read_bytes()),
    }
    run_path = project / ".pf/runs/run/run.yaml"
    run_path.parent.mkdir(parents=True)
    run_path.write_text(
        json.dumps(
            {
                "id": "run",
                "process": "test",
                "tasks": [{"id": "task", "assignment": ".pf/assignments/task.yaml"}],
                "process_execution": process_pin,
            }
        ),
        encoding="utf8",
    )
    saved = {
        "identity": identity,
        "capsule": {
            "path": core.rel(capsule_path, project),
            "checksum": prepared.digest(capsule_path.read_bytes()),
            "contract_checksum": contract["contract_checksum"],
            "intent_checksum": contract["assignment_intent_checksum"],
        },
        "process": process,
        "snapshot": snapshot,
        "outputs": intent["outputs"],
        "scope": intent["scope"],
        "stage": context.stage_view(capsule, task),
    }
    with monkeypatch.context() as patch:
        patch.setattr(prepared, "semantic_input", lambda *args: copy.deepcopy(saved))
        document = prepared.build(project, task, capsule, 1, core)
        path = (
            project / ".pf/runtime/agent-runs/run/task/attempts/1/prepared-input.json"
        )
        checksum = prepared.write_once(path, document)
        state = {
            "attempt": 1,
            "prepared_input": {"path": core.rel(path, project), "checksum": checksum},
        }
        report = project / ".pf/artifacts/report.md"
        report.parent.mkdir(parents=True)
        report.write_text("accepted stage A output", encoding="utf8")
        receipt_path, receipt = prepared.collection_receipt(project, task, state, core)
    completion_path = receipt_path.with_name("collection-complete.json")
    # Exact two-field producer marker, published only after accepted collection.
    prepared.write_once(
        completion_path, {"schema_version": 1, "receipt_id": receipt["receipt_id"]}
    )
    return dict(
        project=project,
        core=core,
        task=task,
        state=state,
        document=document,
        capsule=capsule,
        capsule_path=capsule_path,
        path=path,
        report=report,
        receipt=receipt,
        receipt_path=receipt_path,
        completion_path=completion_path,
    )


def verify(fixture: dict) -> dict:
    return prepared.verify_accepted_collection(
        fixture["project"], fixture["task"], fixture["state"], fixture["core"]
    )


def rewrite_receipt(fixture: dict, receipt: dict) -> None:
    receipt["receipt_id"] = context.fingerprint(
        {k: v for k, v in receipt.items() if k != "receipt_id"}
    )
    fixture["receipt_path"].write_bytes(prepared.encoded(receipt))
    fixture["completion_path"].write_bytes(
        prepared.encoded({"schema_version": 1, "receipt_id": receipt["receipt_id"]})
    )


def rewrite_prepared(fixture: dict) -> None:
    fixture["document"]["input_fingerprint"] = context.fingerprint(
        fixture["document"]["input"]
    )
    raw = prepared.encoded(fixture["document"])
    fixture["path"].write_bytes(raw)
    fixture["state"]["prepared_input"]["checksum"] = prepared.digest(raw)
    fixture["receipt"]["prepared_input"] = copy.deepcopy(
        fixture["state"]["prepared_input"]
    )
    rewrite_receipt(fixture, fixture["receipt"])


@pytest.mark.parametrize("report_action", ["unchanged", "modified", "deleted"])
def test_stage_change_and_report_mutation_are_historical(
    accepted, monkeypatch, report_action
):
    fixture = accepted
    fixture["task"]["stage"] = "stage-b"
    assert (
        context.stage_view(fixture["capsule"], fixture["task"])["id"]
        != fixture["document"]["input"]["stage"]["id"]
    )
    if report_action == "modified":
        fixture["report"].write_bytes(b"new stage B bytes")
    elif report_action == "deleted":
        fixture["report"].unlink()
    before = {
        p.relative_to(fixture["project"]).as_posix(): p.read_bytes()
        for p in fixture["project"].rglob("*")
        if p.is_file()
    }

    def forbidden(*args, **kwargs):
        pytest.fail("historical verifier attempted creator/output/effect call")

    original_open, original_stat, original_lstat = Path.open, Path.stat, Path.lstat
    output_paths = {fixture["report"], fixture["report"].with_name("optional.md")}

    def guarded_open(path, mode="r", *args, **kwargs):
        if path in output_paths or any(c in mode for c in "wax+"):
            forbidden()
        return original_open(path, mode, *args, **kwargs)

    def guarded_stat(path, *args, **kwargs):
        if path in output_paths:
            forbidden()
        return original_stat(path, *args, **kwargs)

    def guarded_lstat(path, *args, **kwargs):
        if path in output_paths:
            forbidden()
        return original_lstat(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        for name in (
            "collection_receipt",
            "output_records",
            "semantic_input",
            "build",
            "write_once",
            "bind_managed_scratch",
        ):
            patch.setattr(prepared, name, forbidden)
        patch.setattr(Path, "open", guarded_open)
        patch.setattr(Path, "stat", guarded_stat)
        patch.setattr(Path, "lstat", guarded_lstat)
        patch.setattr(sqlite3, "connect", forbidden)
        for name in ("mkdir", "unlink", "remove", "rename", "replace", "link"):
            patch.setattr(os, name, forbidden)
        first, second = verify(fixture), verify(fixture)
        assert first == second and first["status"] == "accepted"
    after = {
        p.relative_to(fixture["project"]).as_posix(): p.read_bytes()
        for p in fixture["project"].rglob("*")
        if p.is_file()
    }
    assert before == after
    assert first["receipt"]["outputs"] == fixture["receipt"]["outputs"]


@pytest.mark.parametrize("missing", ["both", "completion", "receipt"])
def test_acceptance_is_distinct_from_receipt_creation(accepted, missing):
    if missing in {"both", "receipt"}:
        accepted["receipt_path"].unlink()
    if missing in {"both", "completion"}:
        accepted["completion_path"].unlink()
    if missing == "receipt":
        with pytest.raises(ValueError):
            verify(accepted)
    else:
        result = verify(accepted)
        assert result["status"] == "not_accepted"
        assert any(pin["status"] == "missing" for pin in result["snapshot"])


@pytest.mark.parametrize("target", ["receipt", "completion"])
@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "schema",
        "bool",
        "id",
        "duplicate",
        "nonfinite",
        "overflow",
        "oversized",
        "array",
        "invalid_utf8",
        "directory",
    ],
)
def test_strict_bounded_metadata(accepted, target, mutation):
    path = accepted[target + "_path"]
    value = json.loads(path.read_bytes())
    if mutation == "unknown":
        value["unknown"] = 0
    elif mutation == "schema":
        value["schema_version"] = 2
    elif mutation == "bool":
        value["schema_version"] = True
    elif mutation == "id":
        value["receipt_id"] = prepared.digest(b"foreign")
    raw = json.dumps(value).encode()
    if mutation == "duplicate":
        raw = raw[:-1] + b', "schema_version": 1}'
    elif mutation == "nonfinite":
        raw = raw[:-1] + b', "extra": NaN}'
    elif mutation == "overflow":
        raw = raw[:-1] + b', "extra": 1e999}'
    elif mutation == "oversized":
        raw = b" " * (prepared.MAX_BYTES + 1)
    elif mutation == "array":
        raw = b"[]"
    elif mutation == "invalid_utf8":
        raw = b"\xff"
    if mutation == "directory":
        path.unlink()
        path.mkdir()
    else:
        path.write_bytes(raw)
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "missing",
        "duplicate",
        "required_missing",
        "required_bool",
        "size_bool",
        "size_negative",
        "size_over",
        "checksum",
        "mtime",
        "missing_pin",
        "missing_with_pin",
        "order",
        "required_false",
        "path",
    ],
)
def test_output_schema_uses_saved_specs_even_with_rehashed_receipt(accepted, mutation):
    receipt = copy.deepcopy(accepted["receipt"])
    records = receipt["outputs"]
    present = next(item for item in records if item["status"] == "present")
    missing = next(item for item in records if item["status"] == "missing")
    if mutation == "extra":
        records.append({"path": "extra.md", "required": False, "status": "missing"})
    elif mutation == "missing":
        records.pop()
    elif mutation == "duplicate":
        records[0] = copy.deepcopy(records[1])
    elif mutation == "required_missing":
        present.clear()
        present.update(path=".pf/artifacts/report.md", required=True, status="missing")
    elif mutation == "required_bool":
        present["required"] = 1
    elif mutation == "size_bool":
        present["size"] = True
    elif mutation == "size_negative":
        present["size"] = -1
    elif mutation == "size_over":
        present["size"] = prepared.OUTPUT_FILE_BYTES + 1
    elif mutation == "checksum":
        present["checksum"] = "sha256:" + "G" * 64
    elif mutation == "mtime":
        present["mtime_ns"] = 123
    elif mutation == "missing_pin":
        del present["checksum"]
    elif mutation == "missing_with_pin":
        missing["size"] = 0
    elif mutation == "order":
        records.reverse()
    elif mutation == "required_false":
        present["required"] = False
    elif mutation == "path":
        present["path"] = "../report.md"
    rewrite_receipt(accepted, receipt)
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize("key", ["path", "checksum", "attempt", "run_id", "id"])
def test_exact_trusted_reference(accepted, key):
    if key in {"path", "checksum"}:
        accepted["state"]["prepared_input"][key] = (
            "foreign" if key == "path" else prepared.digest(b"foreign")
        )
    elif key == "attempt":
        accepted["state"]["attempt"] = True
    else:
        accepted["task"][key] = "foreign"
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize(
    "key",
    [
        "identity",
        "capsule",
        "process",
        "snapshot",
        "scope",
        "outputs",
        "intent",
        "task_pin",
    ],
)
def test_immutable_binding_beyond_load_current_false(accepted, key):
    if key == "intent":
        accepted["task"]["objective"] = "replaced immutable intent"
    elif key == "task_pin":
        del accepted["task"]["process_execution"]["assignment_capsule_checksum"]
    else:
        saved = accepted["document"]["input"]
        if key == "identity":
            saved[key]["context_id"] = "foreign"
        elif key == "capsule":
            saved[key]["intent_checksum"] = prepared.digest(b"foreign")
        elif key == "outputs":
            saved[key]["required_outputs"] = []
        else:
            saved[key]["foreign"] = "changed"
        rewrite_prepared(accepted)
    with pytest.raises(ValueError):
        verify(accepted)


def test_capsule_bytes_are_pinned_even_same_context_id(accepted):
    accepted["capsule_path"].write_bytes(accepted["capsule_path"].read_bytes() + b"\n")
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize(
    "key", ["run_id", "assignment_id", "context_id", "project_id", "attempt"]
)
def test_receipt_exact_identity_even_with_recomputed_self_hash(accepted, key):
    receipt = copy.deepcopy(accepted["receipt"])
    receipt["identity"][key] = True if key == "attempt" else "foreign"
    rewrite_receipt(accepted, receipt)
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize("key", ["path", "checksum"])
def test_receipt_exact_reference_even_with_recomputed_self_hash(accepted, key):
    receipt = copy.deepcopy(accepted["receipt"])
    receipt["prepared_input"][key] = (
        "foreign" if key == "path" else prepared.digest(b"foreign")
    )
    rewrite_receipt(accepted, receipt)
    with pytest.raises(ValueError):
        verify(accepted)


def test_malformed_receipt_does_not_downgrade_to_not_accepted(accepted):
    accepted["completion_path"].unlink()
    accepted["receipt_path"].write_bytes(b'{"schema_version":2}')
    with pytest.raises(ValueError):
        verify(accepted)


def test_nested_duplicate_keys_refuse(accepted):
    raw = accepted["receipt_path"].read_bytes()
    raw = raw.replace(b'"attempt": 1', b'"attempt": 1, "attempt": 1')
    accepted["receipt_path"].write_bytes(raw)
    with pytest.raises(ValueError):
        verify(accepted)


def test_old_readiness_blockers_are_not_new_launch_authority(accepted):
    capsule = accepted["capsule"]
    contract = capsule["execution_contract"]
    contract["readiness"] = {
        "status": "blocked",
        "blockers": [{"code": "historical_material_unavailable"}],
    }
    contract["contract_checksum"] = context.fingerprint(
        {k: v for k, v in contract.items() if k != "contract_checksum"}
    )
    accepted["capsule_path"].write_bytes(prepared.encoded(capsule))
    capsule_checksum = prepared.digest(accepted["capsule_path"].read_bytes())
    accepted["task"]["process_execution"]["assignment_capsule_checksum"] = (
        capsule_checksum
    )
    accepted["document"]["input"]["capsule"].update(
        checksum=capsule_checksum, contract_checksum=contract["contract_checksum"]
    )
    rewrite_prepared(accepted)
    assert verify(accepted)["status"] == "accepted"
    validation = context.validate_execution_contract(
        accepted["project"],
        accepted["project"] / ".pf/assignments/task.yaml",
        accepted["task"],
        capsule,
        accepted["core"],
        check_sources=False,
        require_ready=True,
    )
    assert validation["status"] == "blocked"


def test_revoked_assignment_grant_does_not_validate(accepted):
    accepted["task"]["allowed_actions"] = ["read"]
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize(
    "target", ["path", "receipt_path", "completion_path", "capsule_path"]
)
def test_snapshot_records_raw_bytes_for_caller_cas(accepted, target):
    proof = verify(accepted)
    path = accepted[target]
    relative = path.relative_to(accepted["project"]).as_posix()
    pin = next(item for item in proof["snapshot"] if item["path"] == relative)
    raw = path.read_bytes()
    assert pin == {
        "path": relative,
        "status": "present",
        "checksum": prepared.digest(raw),
        "size": len(raw),
    }
    path.write_bytes(raw + b"\n")
    assert prepared.digest(path.read_bytes()) != pin["checksum"]


def test_receipt_pins_cannot_change_without_completion_binding(accepted):
    receipt = accepted["receipt"]
    receipt["outputs"][-1]["checksum"] = prepared.digest(b"changed")
    receipt["receipt_id"] = context.fingerprint(
        {k: v for k, v in receipt.items() if k != "receipt_id"}
    )
    accepted["receipt_path"].write_bytes(prepared.encoded(receipt))
    with pytest.raises(ValueError):
        verify(accepted)


@pytest.mark.parametrize(
    "mutation", ["duplicate", "bool_schema", "bool_attempt", "nonfinite"]
)
def test_prepared_parser_is_strict_even_when_legacy_load_accepts(accepted, mutation):
    raw = accepted["path"].read_bytes()
    if mutation == "duplicate":
        raw = raw.rstrip()[:-1] + b', "schema_version": 1}'
    elif mutation == "nonfinite":
        raw = raw.rstrip()[:-1] + b', "unknown": Infinity}'
    else:
        document = accepted["document"]
        if mutation == "bool_schema":
            document["schema_version"] = True
        else:
            document["identity"]["attempt"] = True
        raw = prepared.encoded(document)
    accepted["path"].write_bytes(raw)
    accepted["state"]["prepared_input"]["checksum"] = prepared.digest(raw)
    with pytest.raises(ValueError):
        verify(accepted)


def test_creator_retains_current_stage_validation(accepted, monkeypatch):
    fixture = accepted
    fixture["task"]["stage"] = "stage-b"

    def current_semantic(*args):
        saved = copy.deepcopy(fixture["document"]["input"])
        saved["stage"] = context.stage_view(fixture["capsule"], fixture["task"])
        return saved

    monkeypatch.setattr(prepared, "semantic_input", current_semantic)
    with pytest.raises(ValueError, match="prepared_input_changed"):
        prepared.collection_receipt(
            fixture["project"], fixture["task"], fixture["state"], fixture["core"]
        )
    assert verify(fixture)["status"] == "accepted"


def test_total_output_budget_uses_saved_pins(accepted):
    fixture = accepted
    # Five distinct outputs are enough to exceed the existing 32 MiB total
    # while every individual pin satisfies its 8 MiB budget.
    outputs = fixture["document"]["input"]["outputs"]
    outputs["required_outputs"] += [
        {"id": f"extra-{i}", "path": f".pf/artifacts/extra-{i}.md", "required": True}
        for i in range(4)
    ]
    capsule = fixture["capsule"]
    contract = capsule["execution_contract"]
    contract["outputs"] = copy.deepcopy(outputs)
    fixture["task"]["required_outputs"] += [
        {"id": f"extra-{i}", "path": f".pf/artifacts/extra-{i}.md", "required": True}
        for i in range(4)
    ]
    contract["assignment_intent"] = context.assignment_intent(
        fixture["project"],
        fixture["project"] / ".pf/assignments/task.yaml",
        fixture["task"],
        fixture["core"],
    )
    contract["outputs"] = copy.deepcopy(contract["assignment_intent"]["outputs"])
    fixture["document"]["input"]["outputs"] = copy.deepcopy(contract["outputs"])
    contract["assignment_intent_checksum"] = context.fingerprint(
        contract["assignment_intent"]
    )
    contract["contract_checksum"] = context.fingerprint(
        {k: v for k, v in contract.items() if k != "contract_checksum"}
    )
    fixture["capsule_path"].write_bytes(prepared.encoded(capsule))
    capsule_checksum = prepared.digest(fixture["capsule_path"].read_bytes())
    fixture["task"]["process_execution"]["assignment_capsule_checksum"] = (
        capsule_checksum
    )
    fixture["document"]["input"]["capsule"].update(
        checksum=capsule_checksum,
        contract_checksum=contract["contract_checksum"],
        intent_checksum=contract["assignment_intent_checksum"],
    )
    records = fixture["receipt"]["outputs"]
    records += [
        {
            "path": f".pf/artifacts/extra-{i}.md",
            "required": True,
            "status": "present",
            "size": prepared.OUTPUT_FILE_BYTES,
            "checksum": prepared.digest(b"pin"),
        }
        for i in range(4)
    ]
    records.sort(key=lambda item: item["path"])
    rewrite_prepared(fixture)
    with pytest.raises(ValueError, match="prepared_output_budget_exceeded"):
        verify(fixture)
