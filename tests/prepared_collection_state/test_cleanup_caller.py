"""Historical proof plus current release authority, with explicit boundary models."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from processforge_core.executions.model import ExecutionKey
from processforge_core.prepared import command as scratch
from processforge_core.prepared import input as prepared
from processforge_core.prepared import resources
from processforge_core.work import context

from .test_verifier import accepted as accepted
from .test_verifier import rewrite_prepared


@pytest.fixture
def caller(accepted, monkeypatch):
    """Keep the actual verifier, contract validator, creation record and deletion.

    Model only current task/state/storage/resource ports and the lifecycle lock.
    The separate native cycle test exercises those ports with real Work and SQL.
    """
    f = accepted
    project, task, core = f["project"], f["task"], f["core"]
    task["allowed_files"].append(".pf/tmp/accepted-scratch/**")
    task["forbidden_actions"] = ["write_product"]
    intent = context.assignment_intent(
        project, project / ".pf/assignments/task.yaml", task, core
    )
    contract = f["capsule"]["execution_contract"]
    contract.update(
        assignment_intent=intent,
        assignment_intent_checksum=context.fingerprint(intent),
        scope=intent["scope"],
    )
    contract["contract_checksum"] = context.fingerprint(
        {k: v for k, v in contract.items() if k != "contract_checksum"}
    )
    f["capsule_path"].write_bytes(prepared.encoded(f["capsule"]))
    task["process_execution"]["assignment_capsule_checksum"] = prepared.digest(
        f["capsule_path"].read_bytes()
    )
    saved = f["document"]["input"]
    saved["scope"] = copy.deepcopy(intent["scope"])
    saved["sources"] = []
    saved["capsule"].update(
        checksum=task["process_execution"]["assignment_capsule_checksum"],
        contract_checksum=contract["contract_checksum"],
        intent_checksum=contract["assignment_intent_checksum"],
    )
    (project / ".pf/tmp").mkdir()
    scratch.allocate_scratch(project, f["document"])
    rewrite_prepared(f)
    f["scratch"] = project / f["document"]["managed_scratch"]["path"]
    (f["scratch"] / "payload").write_bytes(b"owned disposable bytes")
    task["stage"] = "stage-b"
    f["report"].write_bytes(b"new stage B output")
    f["state"]["status"] = "completed"
    f["proof"] = prepared.verify_accepted_collection(project, task, f["state"], core)
    f["record"] = SimpleNamespace(
        phase="absent",
        collection="collected",
        generation=1,
        revision=7,
        key=ExecutionKey("project", "run", "task", 1),
    )
    f["current_record"] = copy.deepcopy(f["record"])
    f["current_task"] = copy.deepcopy(task)
    f["current_state"] = copy.deepcopy(f["state"])
    f["generation"] = 1
    f["absent"] = True
    f["held"] = 0
    f["retry_pending"] = False
    f["repository"] = SimpleNamespace(
        readiness=lambda: SimpleNamespace(ready=True, generation=f["generation"]),
        load=lambda key: f["current_record"],
        load_latest=lambda *a: f["current_record"],
    )
    core._worker_assignment_service = SimpleNamespace(
        load=lambda *a: copy.deepcopy(f["current_task"])
    )
    core.load_agent_run_state = lambda *a: copy.deepcopy(f["current_state"])
    core._execution_storage = lambda *a: SimpleNamespace(repository=f["repository"])
    core._legacy_tree_probe = lambda *a: f["absent"]

    def retry(*args):
        if f["retry_pending"]:
            raise ValueError("retry_pending")

    core._retry_refuse_pending = retry

    @contextmanager
    def lock(*args):
        f["held"] += 1
        try:
            yield
        finally:
            f["held"] -= 1

    core.worker_run_lifecycle_lock = lock

    def authorize(*args):
        assert f["held"] == 0
        return {}

    monkeypatch.setattr(resources, "authorize_resources", authorize)
    release = scratch.release_scratch
    dispose = scratch.dispose_owned

    def checked_release(*args, **kwargs):
        # finalize_scratch repeats the same idempotent marker outside the lock.
        if not f["path"].with_name("scratch-release.json").exists():
            assert f["held"] == 1
        return release(*args, **kwargs)

    def checked_dispose(*args, **kwargs):
        assert f["held"] == 0
        return dispose(*args, **kwargs)

    monkeypatch.setattr(scratch, "release_scratch", checked_release)
    monkeypatch.setattr(scratch, "dispose_owned", checked_dispose)
    return f


def release(f):
    scratch.release_accepted_scratch(
        f["project"],
        f["task"],
        f["state"],
        f["document"],
        f["proof"],
        f["record"],
        f["core"],
    )


def test_stage_advance_artifact_only_release_and_disposal_replay(caller):
    f = caller
    receipt_bytes = f["receipt_path"].read_bytes()
    release(f)
    assert f["scratch"].is_dir()  # metadata commit does not traverse/delete
    result = scratch.finalize_scratch(
        f["document"], tree_absent=True, evidence_finalized=True
    )
    assert (
        result is not None and result.result == "deleted" and result.deleted_files == 1
    )
    release(f)
    result = scratch.finalize_scratch(
        f["document"], tree_absent=True, evidence_finalized=True
    )
    assert result is not None and result.result == "already_absent"
    assert f["receipt_path"].read_bytes() == receipt_bytes
    assert f["report"].read_bytes() == b"new stage B output"


@pytest.mark.parametrize("when", ["before", "during_authorization"])
@pytest.mark.parametrize(
    "change",
    [
        "task",
        "attempt",
        "reference",
        "sql_revision",
        "generation",
        "pending_collection",
        "retry",
        "cancellation",
        "completion",
        "creation",
    ],
)
def test_release_refuses_observation_drift(caller, monkeypatch, when, change):
    f = caller

    def mutate(*args):
        if change == "task":
            f["current_task"]["objective"] = "different intent"
        elif change == "attempt":
            f["current_state"]["attempt"] += 1
        elif change == "reference":
            f["current_state"]["prepared_input"]["checksum"] = prepared.digest(b"other")
        elif change == "sql_revision":
            f["current_record"].revision += 1
        elif change == "generation":
            f["generation"] += 1
        elif change == "pending_collection":
            f["current_record"].collection = "pending"
        elif change == "retry":
            f["retry_pending"] = True
        elif change == "cancellation":
            (f["project"] / ".pf/runs/run/cancellation-test.yaml").write_bytes(
                b"pending"
            )
        elif change == "completion":
            f["completion_path"].write_bytes(b"{}")
        elif change == "creation":
            f["path"].with_name("scratch-resource.json").write_bytes(b"{}")
        return {}

    if when == "before":
        mutate()
    else:
        monkeypatch.setattr(resources, "authorize_resources", mutate)
    with pytest.raises(ValueError):
        release(f)
    assert f["scratch"].is_dir()
    assert not f["path"].with_name("scratch-release.json").exists()


@pytest.mark.parametrize("prior_release", [False, True])
@pytest.mark.parametrize(
    "denial", ["resource", "intent", "scope", "actions", "capsule"]
)
def test_current_authority_required_even_after_release(
    caller, monkeypatch, prior_release, denial
):
    f = caller
    if prior_release:
        release(f)
    if denial == "resource":

        def denied(*args):
            raise ValueError("resource_revoked")

        monkeypatch.setattr(resources, "authorize_resources", denied)
    elif denial == "capsule":
        f["capsule_path"].write_bytes(b"{}")
    else:
        if denial == "intent":
            f["task"]["objective"] = "different intent"
        elif denial == "scope":
            f["task"]["allowed_files"] = []
        elif denial == "actions":
            f["task"]["allowed_actions"] = ["read"]
        f["current_task"] = copy.deepcopy(f["task"])
    with pytest.raises((ValueError, KeyError)):
        release(f)
    assert f["scratch"].is_dir()
    assert f["path"].with_name("scratch-release.json").exists() is prior_release


@pytest.mark.parametrize("absence", [True, False, None])
def test_legacy_attempt_bound_absence_is_independent(caller, absence):
    f = caller
    f["repository"] = f["record"] = None
    f["absent"] = absence
    if absence is True:
        release(f)
        assert f["path"].with_name("scratch-release.json").is_file()
    else:
        with pytest.raises(ValueError, match="execution_activity_unknown"):
            release(f)
        assert not f["path"].with_name("scratch-release.json").exists()


def test_legacy_absence_rechecked_after_authorization(caller, monkeypatch):
    f = caller
    f["repository"] = f["record"] = None

    def changed(*args):
        f["absent"] = None
        return {}

    monkeypatch.setattr(resources, "authorize_resources", changed)
    with pytest.raises(ValueError, match="execution_activity_unknown"):
        release(f)
    assert f["scratch"].is_dir()


@pytest.mark.parametrize("collection", ["pending", "failed", "refused"])
def test_completion_marker_does_not_reconcile_sql(caller, collection):
    f = caller
    f["record"].collection = f["current_record"].collection = collection
    with pytest.raises(ValueError, match="accepted_scratch_execution_changed"):
        release(f)
    assert f["current_record"].collection == collection
    assert not f["path"].with_name("scratch-release.json").exists()


def test_sql_record_from_another_attempt_cannot_authorize_release(caller):
    f = caller
    f["record"].key = f["current_record"].key = ExecutionKey(
        "project", "run", "task", 2
    )
    with pytest.raises(ValueError, match="accepted_scratch_execution_changed"):
        release(f)
    assert f["scratch"].is_dir()
