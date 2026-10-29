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
from processforge_core.work.context import managed_scratch_namespace, scope_allows


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
    "mutation",
    [
        "readonly",
        "empty",
        "ambiguous",
        "forbidden",
        "metadata",
        "denied_action",
        "unowned",
        "missing_owner",
        "read_grant_only",
    ],
)
@pytest.mark.parametrize("artifact_only", [False, True])
def test_empty_metadata_or_ambiguous_grants_allocate_nothing(
    project, mutation, artifact_only
):
    doc = document(project)
    scope = doc["input"]["scope"]
    action = "write_artifact" if artifact_only else "write_product"
    scope["allowed_actions"] = ["read", action]
    scope["forbidden_actions"] = ["write_product"] if artifact_only else []
    if mutation == "readonly":
        scope["allowed_actions"] = ["read"]
    if mutation == "empty":
        scope["allowed_files"] = []
    if mutation == "metadata":
        scope["ownership"]["writer"] = False
    if mutation == "denied_action":
        scope["forbidden_actions"].append(action)
    if mutation == "unowned":
        scope["ownership"]["owned_files"] = []
    if mutation == "missing_owner":
        scope["ownership"]["owner_id"] = ""
    if mutation == "read_grant_only":
        scope["allowed_read_files"] = scope["allowed_files"]
        scope["allowed_files"] = []
    if mutation == "forbidden":
        scope["forbidden_files"] = [".pf/tmp/*/secret"]
    if mutation == "ambiguous":
        scope["allowed_files"].append(".pf/tmp/other/**")
        scope["ownership"]["owned_files"].append(".pf/tmp/other/**")
    assert managed_scratch_namespace(scope) is None
    scratch.allocate_scratch(project, doc)
    assert "managed_scratch" not in doc
    assert list((project / ".pf/tmp").iterdir()) == []


@pytest.mark.parametrize("artifact_only", [False, True])
def test_real_producer_schema_consumer_release_collection(project, artifact_only):
    import runpy

    doc = document(project)
    scope = doc["input"]["scope"]
    if artifact_only:
        scope["allowed_actions"] = ["read", "write_artifact"]
        scope["forbidden_actions"] = ["write_product"]
    original_scope = copy.deepcopy(scope)
    scratch.allocate_scratch(project, doc)
    assert scope == original_scope
    if artifact_only:
        assert not scope_allows(scope, "src/product.py", "write_product")
        assert not scope_allows(scope, doc["managed_scratch"]["path"], "write_product")
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
    finalized = scratch.finalize_scratch(
        doc, tree_absent=False, evidence_finalized=True
    )
    assert finalized is not None
    assert finalized.result == "needed"
    finalized = scratch.finalize_scratch(
        doc, tree_absent=True, evidence_finalized=False
    )
    assert finalized is not None
    assert finalized.result == "needed"
    receipt = scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True)
    assert receipt is not None
    assert receipt.result == "deleted" and receipt.deleted_files == 1, receipt
    attempt = scratch._attempt(project, doc["identity"])
    assert attempt.is_file() and attempt.with_name("scratch-release.json").is_file()
    assert attempt.with_name("scratch-cleanup.json").is_file() and not root.exists()
    finalized = scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True)
    assert finalized is not None
    assert finalized.result == "already_absent"


def test_failed_use_before_retry_and_valid_retention(project):
    doc = document(project)
    scratch.allocate_scratch(project, doc)
    resource = scratch.read_attempt_resources(project, doc)
    assert resource is not None
    (resource.path / "failed.tmp").write_bytes(b"failed")
    config = TemporaryFilesConfig(retain_unused=True)
    finalized = scratch.finalize_scratch(
        doc, tree_absent=True, evidence_finalized=True, config=config
    )
    assert finalized is not None
    assert finalized.result == "retained_by_configuration"
    receipt = scratch.finalize_scratch(
        doc,
        tree_absent=True,
        evidence_finalized=True,
        config=config,
        configuration_errors=("configuration_read_failed",),
    )
    assert receipt is not None
    assert receipt.result == "deleted"
    retry = document(project)
    retry["identity"]["attempt"] = 2
    scratch.allocate_scratch(project, retry)
    assert retry["managed_scratch"]["path"] != doc["managed_scratch"]["path"]
    assert not resource.path.exists()
    finalized = scratch.finalize_scratch(
        retry, tree_absent=True, evidence_finalized=True
    )
    assert finalized is not None
    assert finalized.result == "deleted"


@pytest.mark.parametrize(
    "change",
    [
        "attempt",
        "owner",
        "path",
        "record",
        "extra",
        "denied_action",
        "unowned",
        "forbidden_scope",
        "ambiguous_scope",
    ],
)
def test_tampered_metadata_never_adopted(project, change):
    doc = document(project)
    doc["input"]["scope"]["allowed_actions"] = ["read", "write_artifact"]
    doc["input"]["scope"]["forbidden_actions"] = ["write_product"]
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
    scope = mutated["input"]["scope"]
    if change == "denied_action":
        scope["forbidden_actions"].append("write_artifact")
    if change == "unowned":
        scope["ownership"]["owned_files"] = []
    if change == "forbidden_scope":
        scope["forbidden_files"] = [".pf/tmp/worker-owned/**"]
    if change == "ambiguous_scope":
        scope["allowed_files"].append(".pf/tmp/other/**")
        scope["ownership"]["owned_files"].append(".pf/tmp/other/**")
    with pytest.raises((ValueError, FileNotFoundError)):
        scratch.read_attempt_resources(project, mutated)
    finalized = scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True)
    assert finalized is not None
    assert finalized.result == "deleted"


def test_old_input_environment_unchanged(project):
    doc = document(project)
    assert scratch.scratch_environment(doc, {"TEMP": "existing"}) == {
        "TEMP": "existing"
    }
    assert (
        scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True) is None
    )


def test_controller_failure_cleanup_precedes_retry_and_outside_locks(
    project, monkeypatch
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    import processforge as core

    from processforge_core.prepared import input as prepared_input

    doc = document(project)
    scratch.allocate_scratch(project, doc)
    attempt = scratch._attempt(project, doc["identity"])
    prepared_path = attempt.with_name("prepared-input.json")
    state = {
        "status": "failed",
        "attempt": 1,
        "prepared_input": {"path": prepared_path.relative_to(project).as_posix()},
    }
    attempt.with_name("exit.json").write_text(
        '{"status":"failed","exit_code":7}', encoding="utf8"
    )
    task = {"id": "task", "run_id": "run"}
    monkeypatch.setattr(core, "load_agent_run_state", lambda *a: state)
    monkeypatch.setattr(prepared_input, "load", lambda *a, **k: doc)
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a: SimpleNamespace(repository=None)
    )
    monkeypatch.setattr(core, "_legacy_tree_probe", lambda *a, **k: True)
    monkeypatch.setattr(
        core,
        "_ProjectMetadataReader",
        lambda *a: SimpleNamespace(workplace_manifest=lambda: None),
    )
    monkeypatch.setattr(
        core,
        "build_configuration_provider",
        lambda **k: SimpleNamespace(
            snapshot=lambda: SimpleNamespace(
                config=SimpleNamespace(
                    runtime=SimpleNamespace(temporary_files=TemporaryFilesConfig())
                ),
                errors=(),
            )
        ),
    )

    @contextmanager
    def forbidden_lock(*args):
        raise AssertionError("cleanup entered lifecycle lock")
        yield

    monkeypatch.setattr(core, "worker_run_lifecycle_lock", forbidden_lock)
    original = scratch.dispose_owned
    calls = []

    def blocked(resource, **kwargs):
        calls.append(resource.path)
        return disposal.CleanupReceipt(
            resource.resource_id, "cleanup_pending", error_code=13
        )

    monkeypatch.setattr(scratch, "dispose_owned", blocked)
    assert core._finalize_worker_scratch(project, task, trigger="before_retry") is False
    assert len(calls) == 1
    monkeypatch.setattr(scratch, "dispose_owned", original)
    # No retry of a denied target: this modeled refusal leaves it as explicit evidence.
    assert calls[0].is_dir()


def test_preparation_failure_finalizes_after_outer_scope_and_preserves_primary(project):
    doc = document(project)
    original = RuntimeError("command preparation failed")
    allocated = None
    with pytest.raises(RuntimeError) as caught:
        with scratch.preparation_scratch():
            scratch.allocate_scratch(project, doc)
            allocated = project / doc["managed_scratch"]["path"]
            assert allocated.is_dir()
            raise original
    assert caught.value is original and allocated is not None and not allocated.exists()
    attempt = scratch._attempt(project, doc["identity"])
    assert attempt.with_name("scratch-preparation-failure.json").is_file()
    assert (
        json.loads(attempt.with_name("scratch-cleanup.json").read_bytes())["result"]
        == "deleted"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("released", 0),
        ("consumers", True),
        ("evidence_finalized", 0),
    ],
)
def test_private_record_rejects_boolean_numeric_equivalence(project, field, value):
    doc = document(project)
    scratch.allocate_scratch(project, doc)
    record = json.loads(scratch._attempt(project, doc["identity"]).read_bytes())
    if field == "schema_version":
        record[field] = value
    else:
        record["use"][field] = value
    with pytest.raises(ValueError, match="scratch_record_invalid"):
        scratch.validate_resource_record(record, doc)
    finalized = scratch.finalize_scratch(doc, tree_absent=True, evidence_finalized=True)
    assert finalized is not None
    assert finalized.result == "deleted"


def _opened_directory_model(monkeypatch, platform, identities, *, query_failure=False):
    """Model native handles only; never call a filesystem or security API."""
    import ctypes
    import stat
    from types import SimpleNamespace

    from processforge_core.maintenance import temporary_files

    events: list[tuple] = []
    opened: dict[int, tuple[int, int]] = {}
    pending = iter(identities)

    def unexpected(*args, **kwargs):
        raise AssertionError("unexpected filesystem operation")

    def acquire(path):
        handle = len(opened) + 42
        opened[handle] = next(pending)
        events.append(("open", handle, str(path)))
        return handle

    def close(handle):
        events.append(("close", handle))

    def open_posix(path, flags, *, dir_fd):
        assert flags == 0x30000 and dir_fd == 17
        return acquire(path)

    def fstat(handle):
        events.append(("identity", handle))
        if query_failure:
            raise OSError(5, "query_failure")
        device, inode = opened[handle]
        return SimpleNamespace(st_mode=stat.S_IFDIR, st_dev=device, st_ino=inode)

    def create(path, access, share, security, creation, flags, template):
        assert (access, share, security, creation, flags, template) == (
            0x81,
            3,
            None,
            3,
            0x02200000,
            None,
        )
        return acquire(path)

    def query(handle, kind, pointer, size):
        if kind == 9:
            pointer._obj[0] = 0x10
        else:
            assert kind == 18
            events.append(("identity", handle))
            if query_failure:
                return False
            device, inode = opened[handle]
            pointer._obj.volume = device
            pointer._obj.identity[:] = inode.to_bytes(16, "little")
        return True

    model_os = SimpleNamespace(
        name=platform,
        O_RDONLY=0,
        O_DIRECTORY=0x10000,
        O_NOFOLLOW=0x20000,
        open=open_posix,
        fstat=fstat,
        close=close,
        scandir=unexpected,
        stat=unexpected,
        rmdir=unexpected,
        unlink=unexpected,
    )
    kernel = SimpleNamespace(
        CreateFileW=create, CloseHandle=close, GetFileInformationByHandleEx=query
    )
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(
        ctypes, "WinError", lambda code: OSError(code, "query_failure"), raising=False
    )
    monkeypatch.setattr(temporary_files, "os", model_os)
    monkeypatch.setattr(disposal, "os", model_os)
    return SimpleNamespace(os=model_os, events=events, opened=opened)


@pytest.mark.parametrize("platform", ["posix", "nt"])
@pytest.mark.parametrize(
    "scenario", ["same", "replaced", "query_error", "body_error", "unbound"]
)
def test_directory_opened_identity_before_yield_pure(monkeypatch, platform, scenario):
    from processforge_core.maintenance import temporary_files

    identity = (7, (1 << 80) + 19)
    actual = (7, identity[1] + 1) if scenario == "replaced" else identity
    model = _opened_directory_model(
        monkeypatch, platform, [actual], query_failure=scenario == "query_error"
    )
    entered = []

    def use():
        with temporary_files._directory(
            Path("model-leaf"),
            17,
            expected_identity=None if scenario == "unbound" else identity,
        ) as descriptor:
            entered.append(descriptor)
            assert model.events[-1][0] == (
                "open" if platform == "nt" and scenario == "unbound" else "identity"
            )
            assert not any(event[0] == "close" for event in model.events)
            if scenario == "body_error":
                raise RuntimeError("body_error")

    if scenario == "replaced":
        with pytest.raises(ValueError, match="^identity_changed$"):
            use()
        assert entered == []
    elif scenario == "query_error":
        with pytest.raises(OSError, match="query_failure"):
            use()
        assert entered == []
    elif scenario == "body_error":
        with pytest.raises(RuntimeError, match="^body_error$"):
            use()
    else:
        use()
    assert len(entered) == (0 if scenario in {"replaced", "query_error"} else 1)
    assert model.events[-1] == ("close", 42)
    assert sum(event[0] == "close" for event in model.events) == 1


@pytest.mark.parametrize("platform", ["posix", "nt"])
@pytest.mark.parametrize("scenario", ["legitimate", "replaced", "nested_replaced"])
def test_directory_disposal_opened_identity_pure(monkeypatch, platform, scenario):
    import stat
    from contextlib import contextmanager
    from types import SimpleNamespace

    root = Path("model-boundary").absolute() / "owned"
    identity = (7, (1 << 80) + 19)
    child_identity = (7, identity[1] + 1)
    replacement = (7, identity[1] + 2)
    identities = [replacement if scenario == "replaced" else identity]
    if scenario == "nested_replaced":
        identities.append(replacement)
    model = _opened_directory_model(monkeypatch, platform, identities)
    infos = {
        root: SimpleNamespace(st_mode=stat.S_IFDIR, st_dev=7, st_ino=identity[1]),
        root / "nested": SimpleNamespace(
            st_mode=stat.S_IFDIR, st_dev=7, st_ino=child_identity[1]
        ),
    }
    monkeypatch.setattr(Path, "lstat", lambda path: infos[path])

    @contextmanager
    def parent(path):
        model.events.append(("parent", str(path)))
        yield None if platform == "nt" else 17

    @contextmanager
    def children(target):
        model.events.append(("scandir", str(target)))
        assert model.events[-2][0] == "identity"
        assert not any(event[0] == "close" for event in model.events)
        yield [SimpleNamespace(name="nested")] if scenario == "nested_replaced" else []

    def remove(*args, **kwargs):
        model.events.append(("delete",))

    monkeypatch.setattr(disposal, "_parent", parent)
    monkeypatch.setattr(disposal, "_windows_delete", remove)
    model.os.scandir = children
    model.os.stat = lambda *a, **k: (
        infos[root / "nested"] if scenario == "nested_replaced" else infos[root]
    )
    model.os.rmdir = remove
    resource = disposal.OwnedTemporary(
        "model-owned",
        root,
        identity,
        root.parent,
        disposal.TemporaryUse(True, 0, True),
        disposal._CREATED,
        "directory",
    )
    receipt = disposal._dispose_directory(resource, ("configuration_read_failed",))
    assert receipt.resource_id == resource.resource_id
    assert receipt.configuration_errors == ("configuration_read_failed",)
    assert receipt.deleted_files == receipt.deleted_bytes == 0
    if scenario == "legitimate":
        assert receipt.result == "deleted" and receipt.complete
        assert receipt.deleted_directories == 1 and receipt.residuals == ()
        assert sum(event[0] == "scandir" for event in model.events) == 1
        assert sum(event[0] == "delete" for event in model.events) == 1
    else:
        assert receipt.result == "cleanup_pending" and not receipt.complete
        assert receipt.reason_code == "identity_changed"
        assert receipt.deleted_directories == 0 and receipt.residuals == (str(root),)
        assert sum(event[0] == "scandir" for event in model.events) == (
            1 if scenario == "nested_replaced" else 0
        )
        assert not any(event[0] == "delete" for event in model.events)
    assert sum(event[0] == "close" for event in model.events) == len(identities)
