"""Real owned-directory and ordinary prepared-worker scratch lifecycle."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.configuration.models import TemporaryFilesConfig
from processforge_core.maintenance import temporary_disposal as disposal
from processforge_core.prepared import command as scratch
from processforge_core.work.context import managed_scratch_namespace


@pytest.fixture
def project():
    root = Path(os.environ["PF_TEST_SCRATCH_ROOT"]) / uuid4().hex
    (root / ".pf/tmp").mkdir(parents=True)
    return root


def document(project):
    namespace = ".pf/tmp/worker-owned"
    identity = {
        "kind": "work",
        "project_id": "project",
        "run_id": "run",
        "assignment_id": "task",
        "context_id": "context",
        "attempt": 1,
    }
    scope = {
        "allowed_files": [namespace + "/**"],
        "allowed_actions": ["read", "write_product"],
        "allowed_read_files": [],
        "forbidden_files": [],
        "forbidden_actions": [],
        "ownership": {
            "writer": True,
            "owner_id": "worker",
            "owned_files": [namespace + "/**"],
        },
    }
    return {
        "project_root": str(project),
        "identity": identity,
        "input": {
            "identity": {k: v for k, v in identity.items() if k != "attempt"},
            "scope": scope,
            "sources": [],
            "outputs": {
                "required_outputs": [],
                "expected_report": {"artifact": ".pf/artifacts/report.md"},
            },
        },
    }


def test_directory_real_nested_success_and_idempotence(project):
    resource = disposal.create_owned_directory(project / ".pf/tmp")
    (resource.path / "nested").mkdir()
    (resource.path / "nested/payload").write_bytes(b"payload")
    assert disposal.dispose_owned(resource).result == "needed"
    receipt = disposal.dispose_owned(disposal.release_owned(resource))
    assert receipt.result == "deleted" and receipt.deleted_files == 1, receipt
    assert receipt.deleted_directories == 2 and receipt.deleted_bytes == 7
    assert not resource.path.exists()
    absent = disposal.dispose_owned(disposal.release_owned(resource))
    assert absent.result == "already_absent" and absent.deleted_files == 0


@pytest.mark.parametrize(
    "held",
    [
        disposal.TemporaryUse(False, 0, True),
        disposal.TemporaryUse(True, 1, True),
        disposal.TemporaryUse(True, 0, False),
    ],
)
def test_directory_needed_holds(project, held):
    resource = disposal.create_owned_directory(project / ".pf/tmp")
    assert disposal.dispose_owned(replace(resource, use=held)).result == "needed"
    assert resource.path.is_dir()
    assert disposal.dispose_owned(disposal.release_owned(resource)).result == "deleted"


def test_directory_reparse_and_identity_refusal(project, monkeypatch):
    resource = disposal.release_owned(
        disposal.create_owned_directory(project / ".pf/tmp")
    )
    changed = replace(resource, identity=(0, 0))
    assert disposal.dispose_owned(changed).result != "deleted"
    original = disposal._linked
    monkeypatch.setattr(disposal, "_linked", lambda info: True)
    assert disposal.dispose_owned(resource).result != "deleted"
    monkeypatch.setattr(disposal, "_linked", original)
    assert disposal.dispose_owned(resource).result == "deleted"


def test_directory_failure_has_bounded_truthful_residual(project, monkeypatch):
    resource = disposal.release_owned(
        disposal.create_owned_directory(project / ".pf/tmp")
    )
    (resource.path / "payload").write_bytes(b"x")
    original = disposal._windows_delete

    def denied(owned):
        raise PermissionError(13, "fixture denial")

    monkeypatch.setattr(disposal, "_windows_delete", denied)
    if os.name == "nt":
        receipt = disposal.dispose_owned(resource)
        assert receipt.result == "cleanup_pending" and not receipt.complete
        assert receipt.residuals == (str(resource.path),) and resource.path.exists()
    monkeypatch.setattr(disposal, "_windows_delete", original)
    assert disposal.dispose_owned(resource).result == "deleted"


@pytest.mark.parametrize(
    "mutation", ["readonly", "empty", "ambiguous", "forbidden", "metadata"]
)
def test_empty_metadata_or_ambiguous_grants_allocate_nothing(project, mutation):
    doc = document(project)
    scope = doc["input"]["scope"]
    if mutation == "readonly":
        scope["allowed_actions"] = ["read"]
    if mutation == "empty":
        scope["allowed_files"] = []
    if mutation == "metadata":
        scope["ownership"]["writer"] = False
    if mutation == "forbidden":
        scope["forbidden_files"] = [".pf/tmp/*/secret"]
    if mutation == "ambiguous":
        scope["allowed_files"].append(".pf/tmp/other/**")
        scope["ownership"]["owned_files"].append(".pf/tmp/other/**")
    assert managed_scratch_namespace(scope) is None
    scratch.allocate_scratch(project, doc)
    assert "managed_scratch" not in doc
    assert list((project / ".pf/tmp").iterdir()) == []


def test_real_producer_schema_consumer_release_collection(project):
    import runpy

    doc = document(project)
    scratch.allocate_scratch(project, doc)
    schema_path = (
        Path(__file__).resolve().parents[2] / "schemas/prepared-input.schema.json"
    )
    schema = json.loads(schema_path.read_text())
    validator = runpy.run_path(
        str(schema_path.parents[1] / "tools/validate-process-forge-schemas.py")
    )
    validator["validate_against_schema"](
        doc["managed_scratch"],
        {"$ref": "#/$defs/managed_scratch", "$defs": schema["$defs"]},
        "managed scratch",
    )
    env = scratch.scratch_environment(doc, {"OTHER": "kept"})
    root = Path(env["TEMP"])
    assert env["TMP"] == env["TMPDIR"] == env["PF_WORKER_SCRATCH"] == str(root)
    assert env["OTHER"] == "kept"
    (root / "worker-result.tmp").write_bytes(b"actual disposable worker bytes")
    assert (
        scratch.finalize_scratch(doc, tree_absent=False, evidence_finalized=True).result
        == "needed"
    )
    assert (
        scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=False).result
        == "needed"
    )
    receipt = scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True)
    assert receipt.result == "deleted" and receipt.deleted_files == 1, receipt
    attempt = scratch._attempt(project, doc["identity"])
    assert attempt.is_file() and attempt.with_name("scratch-release.json").is_file()
    assert attempt.with_name("scratch-cleanup.json").is_file() and not root.exists()
    assert (
        scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True).result
        == "already_absent"
    )


def test_failed_use_before_retry_and_valid_retention(project):
    doc = document(project)
    scratch.allocate_scratch(project, doc)
    resource = scratch.read_attempt_resources(project, doc)
    assert resource is not None
    (resource.path / "failed.tmp").write_bytes(b"failed")
    config = TemporaryFilesConfig(retain_unused=True)
    assert (
        scratch.finalize_scratch(
            doc, tree_absent=True, evidence_finalized=True, config=config
        ).result
        == "retained_by_configuration"
    )
    receipt = scratch.finalize_scratch(
        doc,
        tree_absent=True,
        evidence_finalized=True,
        config=config,
        configuration_errors=("configuration_read_failed",),
    )
    assert receipt.result == "deleted"
    retry = document(project)
    retry["identity"]["attempt"] = 2
    scratch.allocate_scratch(project, retry)
    assert retry["managed_scratch"]["path"] != doc["managed_scratch"]["path"]
    assert not resource.path.exists()
    assert (
        scratch.finalize_scratch(
            retry, tree_absent=True, evidence_finalized=True
        ).result
        == "deleted"
    )


@pytest.mark.parametrize("change", ["attempt", "owner", "path", "record", "extra"])
def test_tampered_metadata_never_adopted(project, change):
    doc = document(project)
    scratch.allocate_scratch(project, doc)
    mutated = copy.deepcopy(doc)
    marker = mutated["managed_scratch"]
    if change == "attempt":
        marker["identity"]["attempt"] = 3
    if change == "owner":
        marker["owner_id"] = "someone-else"
    if change == "path":
        marker["path"] = ".pf/tmp/unowned"
    if change == "record":
        marker["record"]["sha256"] = "sha256:" + "0" * 64
    if change == "extra":
        marker["extra"] = True
    with pytest.raises((ValueError, FileNotFoundError)):
        scratch.read_attempt_resources(project, mutated)
    assert (
        scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True).result
        == "deleted"
    )


def test_old_input_environment_unchanged(project):
    doc = document(project)
    assert scratch.scratch_environment(doc, {"TEMP": "existing"}) == {
        "TEMP": "existing"
    }
    assert (
        scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True) is None
    )
