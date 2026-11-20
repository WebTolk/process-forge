"""Historical capture pins must not hide a current semantic refusal."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from processforge_core.prepared import input as prepared
from processforge_core.prepared.collection import (
    CapturedAttemptReader,
    CollectionRecoveryStore,
    collection_refusal_reason,
)

from .test_verifier import accepted as accepted
from .test_verifier import rewrite_prepared, rewrite_receipt, verify


@pytest.fixture
def captured(accepted):
    f = accepted
    f["state"].update(
        status="completed",
        run_id="run",
        task_id="task",
        capsule_path=f["core"].rel(f["capsule_path"], f["project"]),
    )
    (f["project"] / ".pf/process-forge.yaml").write_text(
        "project:\n  id: project\n", encoding="utf8"
    )
    assert (
        CapturedAttemptReader(f["project"]).read(f["task"], f["state"], run_id="run")
        is not None
    )
    assert verify(f)["status"] == "accepted"
    return f


def files(project):
    return {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }


def current_refusal(f, monkeypatch):
    changed = copy.deepcopy(f["document"]["input"])
    changed["stage"] = {"id": "different-stage"}
    with monkeypatch.context() as patch:
        patch.setattr(prepared, "semantic_input", lambda *args: changed)
        with pytest.raises(ValueError, match="^prepared_input_changed$") as raised:
            prepared.load(f["project"], f["task"], f["state"], f["core"])
    assert collection_refusal_reason(raised.value) == "prepared_input_changed"
    return raised.value


def assert_recovery_observed(f, monkeypatch):
    reader = CapturedAttemptReader(f["project"])
    store = CollectionRecoveryStore(f["project"])
    before = files(f["project"])
    assert reader.read(f["task"], f["state"], run_id="run") is None
    assert files(f["project"]) == before
    error = current_refusal(f, monkeypatch)
    assert store.record(f["task"], f["state"], run_id="run", error=error)
    recovery = store.read(f["task"], f["state"], run_id="run")
    assert recovery is not None
    assert (recovery.attempt, recovery.reason) == (1, "prepared_input_changed")
    after = files(f["project"])
    assert all(after[name] == value for name, value in before.items())
    added = set(after) - set(before)
    assert len(added) == 1
    assert Path(added.pop()).name.startswith("collect-block-")
    assert store.record(f["task"], f["state"], run_id="run", error=error)
    assert files(f["project"]) == after


@contextmanager
def guarded_history(f, monkeypatch):
    outputs = {f["report"], f["report"].with_name("optional.md")}
    original = {name: getattr(Path, name) for name in ("open", "stat", "lstat")}

    def guard(name):
        def guarded(path, *args, **kwargs):
            assert path not in outputs, "historical metadata inspected output body"
            return original[name](path, *args, **kwargs)

        return guarded

    def forbidden(*args, **kwargs):
        pytest.fail("historical metadata attempted current source/output acceptance")

    with monkeypatch.context() as patch:
        for name in original:
            patch.setattr(Path, name, guard(name))
        for name in ("semantic_input", "output_records", "collection_receipt"):
            patch.setattr(prepared, name, forbidden)
        yield


def assert_metadata_miss(f, monkeypatch, *, recovery_expected=True):
    before = files(f["project"])
    task, state = copy.deepcopy(f["task"]), copy.deepcopy(f["state"])
    error = current_refusal(f, monkeypatch)
    reader = CapturedAttemptReader(f["project"])
    store = CollectionRecoveryStore(f["project"])
    with guarded_history(f, monkeypatch):
        assert reader.read(f["task"], f["state"], run_id="run") is None
        assert (
            store.record(f["task"], f["state"], run_id="run", error=error)
            is recovery_expected
        )
        observed = store.read(f["task"], f["state"], run_id="run")
        if recovery_expected:
            assert observed is not None and observed.reason == "prepared_input_changed"
            assert store.record(f["task"], f["state"], run_id="run", error=error)
        else:
            assert observed is None
    after = files(f["project"])
    assert f["task"] == task and f["state"] == state
    assert all(after[name] == raw for name, raw in before.items())
    if recovery_expected:
        added = set(after) - set(before)
        assert len(added) == 1 and Path(added.pop()).name.startswith("collect-block-")
    else:
        assert before == after


def duplicate_key(raw, key, first):
    needle = json.dumps(key).encode() + b":"
    replacement = needle + b" " + json.dumps(first).encode() + b", " + needle
    changed = raw.replace(needle, replacement, 1)
    assert changed != raw and json.loads(changed) == json.loads(raw)
    return changed


@pytest.mark.parametrize(
    ("target", "key", "first"),
    [
        ("receipt_path", "outputs", []),
        ("receipt_path", "schema_version", 2),
        ("receipt_path", "identity", {}),
        ("receipt_path", "receipt_id", "sha256:bad"),
        ("completion_path", "schema_version", 2),
        ("completion_path", "receipt_id", "sha256:bad"),
        ("receipt_path", "checksum", "sha256:"),
    ],
)
def test_duplicate_capture_keys_preserve_original_ids_but_require_recovery(
    captured, monkeypatch, target, key, first
):
    f = captured
    original_id = f["receipt"]["receipt_id"]
    path = f[target]
    path.write_bytes(duplicate_key(path.read_bytes(), key, first))
    assert json.loads(f["receipt_path"].read_bytes())["receipt_id"] == original_id
    assert json.loads(f["completion_path"].read_bytes())["receipt_id"] == original_id
    with pytest.raises(ValueError, match="^accepted_collection_invalid$"):
        verify(f)
    assert_metadata_miss(f, monkeypatch)


def test_unknown_receipt_fields_do_not_suppress_refusal(captured, monkeypatch):
    f = captured
    receipt = copy.deepcopy(f["receipt"])
    receipt["unexpected"] = True
    rewrite_receipt(f, receipt)
    with pytest.raises(ValueError, match="^accepted_collection_receipt_invalid$"):
        verify(f)
    assert_metadata_miss(f, monkeypatch)


@pytest.mark.parametrize("field", ["process", "snapshot", "scope", "capsule"])
def test_rehashed_immutable_binding_changes_require_recovery(
    captured, monkeypatch, field
):
    f = captured
    f["document"]["input"][field]["unexpected"] = True
    rewrite_prepared(f)
    with pytest.raises(ValueError, match="^prepared_input_context_mismatch$"):
        verify(f)
    assert_metadata_miss(f, monkeypatch)


@pytest.mark.parametrize("syntax", ["duplicate", "nonfinite"])
def test_ambiguous_prepared_identity_cannot_create_recovery_authority(
    captured, monkeypatch, syntax
):
    f = captured
    raw = f["path"].read_bytes()
    if syntax == "duplicate":
        changed = duplicate_key(raw, "schema_version", 2)
    else:
        changed = raw.rstrip()[:-1] + b', "unexpected": NaN}\n'
    f["path"].write_bytes(changed)
    f["state"]["prepared_input"]["checksum"] = prepared.digest(changed)
    f["receipt"]["prepared_input"] = copy.deepcopy(f["state"]["prepared_input"])
    rewrite_receipt(f, f["receipt"])
    with pytest.raises(ValueError, match="^accepted_collection_invalid$"):
        verify(f)
    # A malformed identity proof is unknown, not authority to create an observation.
    assert_metadata_miss(f, monkeypatch, recovery_expected=False)


def test_extra_prepared_reference_keys_do_not_create_recovery_authority(
    captured, monkeypatch
):
    f = captured
    f["state"]["prepared_input"]["unexpected"] = True
    f["receipt"]["prepared_input"] = copy.deepcopy(f["state"]["prepared_input"])
    rewrite_receipt(f, f["receipt"])
    with pytest.raises(ValueError, match="^prepared_input_reference_mismatch$"):
        verify(f)
    assert_metadata_miss(f, monkeypatch, recovery_expected=False)


def test_ambiguous_recovery_marker_is_not_read_or_overwritten(captured, monkeypatch):
    f = captured
    f["completion_path"].unlink()
    assert_metadata_miss(f, monkeypatch)
    (marker,) = f["path"].parent.glob("collect-block-*.json")
    marker.write_bytes(duplicate_key(marker.read_bytes(), "fingerprint", "sha256:bad"))
    before = files(f["project"])
    error = current_refusal(f, monkeypatch)
    store = CollectionRecoveryStore(f["project"])
    with guarded_history(f, monkeypatch):
        assert store.read(f["task"], f["state"], run_id="run") is None
        assert not store.record(f["task"], f["state"], run_id="run", error=error)
    assert files(f["project"]) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "report_only",
        "missing_optional",
        "extra",
        "duplicate",
        "required_missing",
        "required_bool",
        "required_false",
        "size_missing",
        "size_bool",
        "size_negative",
        "size_float",
        "size_over",
        "checksum_short",
        "checksum_invalid",
        "checksum_missing",
        "mtime",
        "missing_with_pin",
        "order",
        "path",
        "record_type",
        "outputs_type",
    ],
)
def test_invalid_saved_pins_do_not_suppress_current_refusal(
    captured, monkeypatch, mutation
):
    f = captured
    original = {
        name: f[name].read_bytes() for name in ("receipt_path", "completion_path")
    }
    receipt = copy.deepcopy(f["receipt"])
    records = receipt["outputs"]
    present = next(item for item in records if item["status"] == "present")
    missing = next(item for item in records if item["status"] == "missing")
    if mutation in {"report_only", "missing_optional"}:
        receipt["outputs"] = [present]
        if mutation == "report_only":
            present["checksum"] = "sha256:"
            del present["size"]
    elif mutation == "extra":
        records.append({"path": "extra.md", "required": False, "status": "missing"})
    elif mutation == "duplicate":
        records[0] = copy.deepcopy(present)
    elif mutation == "required_missing":
        present.clear()
        present.update(path=".pf/artifacts/report.md", required=True, status="missing")
    elif mutation == "required_bool":
        present["required"] = 1
    elif mutation == "required_false":
        present["required"] = False
    elif mutation == "size_missing":
        del present["size"]
    elif mutation == "size_bool":
        present["size"] = True
    elif mutation == "size_negative":
        present["size"] = -1
    elif mutation == "size_float":
        present["size"] = float(present["size"])
    elif mutation == "size_over":
        present["size"] = prepared.OUTPUT_FILE_BYTES + 1
    elif mutation == "checksum_short":
        present["checksum"] = "sha256:"
    elif mutation == "checksum_invalid":
        present["checksum"] = "sha256:" + "G" * 64
    elif mutation == "checksum_missing":
        del present["checksum"]
    elif mutation == "mtime":
        present["mtime_ns"] = 123
    elif mutation == "missing_with_pin":
        missing["size"] = 0
    elif mutation == "order":
        records.reverse()
    elif mutation == "path":
        present["path"] = "../report.md"
    elif mutation == "record_type":
        records[0] = None
    elif mutation == "outputs_type":
        receipt["outputs"] = {}
    rewrite_receipt(f, receipt)
    with pytest.raises(ValueError, match="^accepted_collection_outputs_invalid$"):
        verify(f)
    assert_recovery_observed(f, monkeypatch)
    for name, raw in original.items():
        f[name].write_bytes(raw)
    reader = CapturedAttemptReader(f["project"])
    store = CollectionRecoveryStore(f["project"])
    assert reader.read(f["task"], f["state"], run_id="run") is not None
    assert store.read(f["task"], f["state"], run_id="run") is None
    assert not store.record(
        f["task"], f["state"], run_id="run", error=current_refusal(f, monkeypatch)
    )


def test_rehashed_prepared_outputs_cannot_weaken_capsule(captured, monkeypatch):
    f = captured
    f["document"]["input"]["outputs"]["required_outputs"] = []
    f["receipt"]["outputs"] = [
        item for item in f["receipt"]["outputs"] if item["status"] == "present"
    ]
    rewrite_prepared(f)
    with pytest.raises(ValueError, match="^prepared_input_context_mismatch$"):
        verify(f)
    assert_recovery_observed(f, monkeypatch)


@pytest.mark.parametrize("report_action", ["unchanged", "modified", "deleted"])
def test_valid_history_ignores_current_stage_and_output_bodies(
    captured, monkeypatch, report_action
):
    f = captured
    f["task"]["stage"] = "stage-b"
    if report_action == "modified":
        f["report"].write_bytes(b"later stage output")
    elif report_action == "deleted":
        f["report"].unlink()
    before = files(f["project"])
    error = current_refusal(f, monkeypatch)
    reader = CapturedAttemptReader(f["project"])
    store = CollectionRecoveryStore(f["project"])
    outputs = {f["report"], f["report"].with_name("optional.md")}
    original = {name: getattr(Path, name) for name in ("open", "stat", "lstat")}

    def guard(name):
        def guarded(path, *args, **kwargs):
            assert path not in outputs, "historical observation inspected output body"
            return original[name](path, *args, **kwargs)

        return guarded

    def forbidden(*args, **kwargs):
        pytest.fail("historical observation attempted current acceptance/effects")

    with monkeypatch.context() as patch:
        for name in original:
            patch.setattr(Path, name, guard(name))
        for name in (
            "semantic_input",
            "output_records",
            "collection_receipt",
            "write_once",
        ):
            patch.setattr(prepared, name, forbidden)
        first = reader.read(f["task"], f["state"], run_id="run")
        assert first is not None
        assert reader.read(f["task"], f["state"], run_id="run") == first
        assert not store.record(f["task"], f["state"], run_id="run", error=error)
    assert files(f["project"]) == before
