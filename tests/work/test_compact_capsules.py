"""Authored compact-storage regressions; execution needs a separate QA grant.

Filesystem tests require PF_COMPACT_TEST_ROOT pointing at the QA Work's
authorized disposable directory. No fixture uses the global temp directory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from processforge_core.work import compact_codec, compact_objects
from processforge_core.work.compact_codec import (
    canonical_bytes,
    decode_canonical,
    decode_capsule,
    object_ref,
    pack_capsule,
)
from processforge_core.work.compact_model import (
    MAX_BYTES,
    CapsuleIdentity,
    CompactError,
    ObjectRef,
    VerifiedCapsule,
)
from processforge_core.work.compact_objects import (
    ProjectObjectStore,
    object_relative_path,
)


def checksum(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def test_schema_parsed_once_and_cache_deeply_immutable(monkeypatch):
    import importlib

    original = compact_codec.json.loads
    count = 0

    def loads(raw, *args, **kwargs):
        nonlocal count
        if raw == compact_codec._SEMANTIC_SCHEMA_JSON:
            count += 1
        return original(raw, *args, **kwargs)

    monkeypatch.setattr(compact_codec.json, "loads", loads)
    importlib.reload(compact_codec)
    cached = compact_codec._SEMANTIC_SCHEMA
    for _ in range(10):
        load(plan())
    assert count == 1
    assert compact_codec._SEMANTIC_SCHEMA is cached
    with pytest.raises(TypeError):
        cached["type"] = "null"
    with pytest.raises(TypeError):
        cached["$defs"]["execution_contract"]["type"] = "null"
    assert isinstance(cached["required"], tuple)
    assert (
        hashlib.sha256(compact_codec._SEMANTIC_SCHEMA_JSON.encode()).hexdigest()
        == compact_codec._SEMANTIC_SCHEMA_SHA256
    )


def test_reuse_real_fsync_preserves_existing_identity_and_bytes(sandbox, monkeypatch):
    raw = b"existing durable bytes"
    ref = raw_ref(raw)
    objects = store(sandbox)
    objects.publish(ref, [raw])
    path = sandbox / object_relative_path(ref)
    before = path.stat()
    real_fsync = os.fsync
    flushed = []

    def fsync(fd):
        info = os.fstat(fd)
        real_fsync(fd)
        flushed.append((info.st_dev, info.st_ino))

    monkeypatch.setattr(os, "fsync", fsync)
    objects.publish(ref, [raw])
    assert (before.st_dev, before.st_ino) in flushed
    after = path.stat()
    assert (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) == (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    assert path.read_bytes() == raw


@pytest.mark.parametrize("failure", ["open", "fsync", "write_grant"])
def test_reuse_durability_failure_never_clobbers(sandbox, monkeypatch, failure):
    raw = b"unchanged"
    ref = raw_ref(raw)
    store(sandbox).publish(ref, [raw])
    path = sandbox / object_relative_path(ref)
    before = path.stat()
    real_open, real_fsync = os.open, os.fsync
    grants = 0

    def authorize(relative, action):
        nonlocal grants
        assert relative == object_relative_path(ref).as_posix()
        if action == "write_artifact":
            grants += 1
            if failure == "write_grant" and grants == 3:
                raise PermissionError("current write denied")

    def checked_open(selected, flags, *args, **kwargs):
        if Path(selected) == path and flags & os.O_RDWR:
            assert not flags & (os.O_TRUNC | os.O_CREAT)
            if failure == "open":
                raise PermissionError("writable durability handle denied")
        return real_open(selected, flags, *args, **kwargs)

    def checked_fsync(fd):
        info = os.fstat(fd)
        if failure == "fsync" and (info.st_dev, info.st_ino) == (
            before.st_dev,
            before.st_ino,
        ):
            raise OSError("existing durability unavailable")
        real_fsync(fd)

    monkeypatch.setattr(os, "open", checked_open)
    monkeypatch.setattr(os, "fsync", checked_fsync)
    with pytest.raises(OSError):
        store(sandbox, authorize=authorize).publish(ref, [raw])
    assert path.stat().st_ino == before.st_ino
    assert path.read_bytes() == raw


def fingerprint(value: Any) -> str:
    # Independent copy of the existing context.fingerprint formula.
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return checksum(raw)


def identity(assignment: str = "assignment-one") -> CapsuleIdentity:
    return CapsuleIdentity(
        "12345678-1234-5678-9abc-123456789abc",
        "project-one",
        "run-one",
        assignment,
        assignment + "-capsule",
    )


def document(selected: CapsuleIdentity) -> dict[str, Any]:
    scope = {
        "allowed_files": [],
        "allowed_read_files": [],
        "allowed_actions": ["read"],
        "forbidden_files": [],
        "forbidden_actions": [],
        "ownership": {},
        "non_overlap": {},
    }
    outputs = {"required_outputs": [], "expected_report": {}}
    intent = {
        "objective": "shared",
        "scope": copy.deepcopy(scope),
        "outputs": copy.deepcopy(outputs),
        "workspace_access": {},
        "execution_mode": {
            "kind": "implementation",
            "code_changes_allowed": True,
            "artifact_changes_allowed": True,
            "requires_review": True,
        },
        "required_sources": [],
        "context_artifacts": [],
        "subagent_policy": {},
        "required_capabilities": [],
        "optional_capabilities": [],
        "process": "review",
        "selected_specializations": [],
        "coordination_requirements": {},
        "director_inbox_submit_required": False,
        "parameters": {},
        "allowed_tools": [],
        "allowed_templates": [],
        "selected_sources": [],
        "obligations": {},
    }
    definition = {"id": "review", "stages": [{"id": "implementation"}]}
    pin = {
        "definition": definition,
        "process_id": "review",
        "process_version": "1.0",
        "process_fingerprint": fingerprint(definition),
    }
    snapshot_digest = fingerprint({"snapshot": "frozen"})
    bindings = {"schema_version": 1, "resources": [], "status": "available"}
    logical = asdict(selected)
    logical.pop("project_uuid")
    contract = {
        "contract_version": 1,
        "identity": {"kind": "work", **logical},
        "assignment_intent": intent,
        "assignment_intent_checksum": fingerprint(intent),
        "scope": copy.deepcopy(scope),
        "outputs": copy.deepcopy(outputs),
        "workspace_access": {},
        "required_sources": [],
        "parameters": {},
        "coordination": {},
        "source_limits": {"files": 128, "file_bytes": 1048576, "total_bytes": 8388608},
        "capabilities": {"required": [], "optional": []},
        "readiness": {"status": "ready", "blockers": []},
        "worker_may_rebuild_context": False,
        "snapshot": {"id": "snapshot-one", "checksum": snapshot_digest},
        "process": {
            "id": pin["process_id"],
            "version": pin["process_version"],
            "fingerprint": pin["process_fingerprint"],
        },
        "resources": {"selected_ids": [], "bindings_checksum": fingerprint(bindings)},
    }
    contract["contract_checksum"] = fingerprint(contract)
    return {
        "schema_version": 1,
        "capsule": {
            "id": selected.context_id,
            "assignment_id": selected.assignment_id,
            "assignment_path": f".pf/assignments/{selected.assignment_id}.yaml",
            "immutable": True,
            "worker_may_rebuild_context": False,
            "generated_at": "2026-11-03T09:00:00Z",
        },
        "assignment": {
            "id": selected.assignment_id,
            "run_id": selected.run_id,
            "path": f".pf/assignments/{selected.assignment_id}.yaml",
        },
        "scope": scope,
        "outputs": outputs,
        "workspace_access": {},
        "context": {
            "selected_resource_ids": [],
            "a/b": {"~": [1, True, None]},
            "numeric": {"0": "object key"},
        },
        "context_snapshot": {
            "id": "snapshot-one",
            "sha256": snapshot_digest,
            "freshness_at_creation": "fresh",
        },
        "resource_bindings": bindings,
        "process_execution": pin,
        "execution_contract": contract,
    }


def plan(
    selected: CapsuleIdentity | None = None, material: tuple[Any, ...] = ()
) -> Any:
    selected = selected or identity()
    return pack_capsule(
        identity=selected, document=document(selected), material=material
    )


def load(
    prepared: Any,
    *,
    selected: CapsuleIdentity | None = None,
    objects: dict[str, bytes] | None = None,
) -> VerifiedCapsule:
    objects = (
        objects
        if objects is not None
        else {ref.digest: raw for ref, raw in prepared.objects}
    )
    return decode_capsule(
        raw=prepared.envelope_bytes,
        expected_checksum=prepared.envelope_checksum,
        expected_identity=selected or identity(),
        read_object=lambda ref: objects[ref.digest],
    )


def rewrite_manifest(prepared: Any, mutate: Any) -> tuple[bytes, dict[str, bytes]]:
    objects = {ref.digest: raw for ref, raw in prepared.objects}
    envelope = json.loads(prepared.envelope_bytes)
    manifest = json.loads(objects[envelope["manifest"]["digest"]])
    mutate(manifest)
    raw = canonical_bytes(manifest)
    ref = object_ref(raw, media_type="application/json", codec="pf.context-manifest.v1")
    objects[ref.digest] = raw
    envelope["manifest"] = asdict(ref)
    return canonical_bytes(envelope), objects


@pytest.fixture
def sandbox() -> Iterator[Path]:
    configured = os.environ.get("PF_COMPACT_TEST_ROOT")
    if not configured:
        pytest.fail("PF_COMPACT_TEST_ROOT must name the QA Work's authorized scratch")
    root = Path(configured)
    if not root.is_absolute() or not root.is_dir():
        pytest.fail("PF_COMPACT_TEST_ROOT must be an existing absolute directory")
    with tempfile.TemporaryDirectory(prefix="compact-capsules-", dir=root) as name:
        yield Path(name)


def store(root: Path, *, authorize: Any = None, sync: Any = None) -> ProjectObjectStore:
    # Test-only injected backends make no claim of real directory durability.
    return ProjectObjectStore(
        root,
        authorize=authorize or (lambda path, action: None),
        sync_directory=sync or (lambda path: None),
    )


def raw_ref(raw: bytes) -> ObjectRef:
    return object_ref(raw, media_type="application/octet-stream", codec="raw.v1")


def test_cj1_exact_bytes_and_unicode_order() -> None:
    raw = canonical_bytes(
        {"z": [None, True, False, -(2**63), 2**63 - 1], "é": "e\u0301", "a": "é"}
    )
    assert (
        raw
        == '{"a":"é","z":[null,true,false,-9223372036854775808,9223372036854775807],"é":"é"}'.encode()
    )
    assert canonical_bytes(decode_canonical(raw)) == raw
    assert decode_canonical(b"true") is True
    assert type(decode_canonical(b"1")) is int


@pytest.mark.parametrize(
    "raw,code",
    [
        (b'{"x":1,"x":2}', "duplicate_key"),
        (b'{"outer":{"x":1,"x":2}}', "duplicate_key"),
        (b'{"b":0,"a":0}', "noncanonical_json"),
        (b"{}\n", "noncanonical_json"),
        (b'{ "x":1}', "noncanonical_json"),
        (b"-0", "noncanonical_json"),
        (b'"\\u0061"', "noncanonical_json"),
        (b"9223372036854775808", "integer_overflow"),
        (b"-9223372036854775809", "integer_overflow"),
        (b"1.0", "unsupported_number"),
        (b"1e0", "unsupported_number"),
        (b"NaN", "unsupported_number"),
        (b"Infinity", "unsupported_number"),
        (b'"\\u0000"', "invalid_string"),
        (b'"\\ud800"', "invalid_string"),
        (b'"\xff"', "invalid_json"),
        (b"\xef\xbb\xbf{}", "invalid_json"),
    ],
)
def test_cj1_rejects_ambiguous_and_unsupported_bytes(raw: bytes, code: str) -> None:
    with pytest.raises(CompactError, match=code):
        decode_canonical(raw)


@pytest.mark.parametrize(
    "value", [1.0, float("nan"), 2**63, {1: "bad"}, "\x00", "\udfff"]
)
def test_encoder_rejects_without_coercing(value: Any) -> None:
    with pytest.raises(CompactError):
        canonical_bytes(value)


def test_cj1_depth_and_size_checked_before_json_allocation() -> None:
    assert canonical_bytes(decode_canonical(b"[" * 64 + b"0" + b"]" * 64))
    with pytest.raises(CompactError, match="nesting_limit"):
        decode_canonical(b"[" * 65 + b"0" + b"]" * 65)
    with pytest.raises(CompactError, match="size_limit"):
        decode_canonical(b" " * (MAX_BYTES + 1))
    with pytest.raises(CompactError, match="size_limit"):
        canonical_bytes("é" * MAX_BYTES)


def test_deep_immutable_dtos_detach_mutable_aliases() -> None:
    value = {"x": {"list": [1]}}
    material = [{"nested": ["one"]}]
    verified = VerifiedCapsule(2, identity(), checksum(b"{}"), value, material)
    value["x"]["list"].append(2)
    material[0]["nested"].append("two")
    assert verified.document["x"]["list"] == (1,)
    assert verified.material[0]["nested"] == ("one",)
    with pytest.raises(TypeError):
        verified.document["x"]["new"] = 1


def test_deterministic_roundtrip_shared_bytes_and_distinct_work() -> None:
    first, again, other = plan(), plan(), plan(identity("assignment-two"))
    assert first == again
    assert first.envelope_bytes != other.envelope_bytes
    assert first.envelope_checksum != other.envelope_checksum
    shared = {ref.digest for ref, _ in first.objects} & {
        ref.digest for ref, _ in other.objects
    }
    definition_digest = hashlib.sha256(
        canonical_bytes(document(identity())["process_execution"]["definition"])
    ).hexdigest()
    assert definition_digest in shared
    assert len(first.objects) == len({ref.digest for ref, _ in first.objects})
    assert list(ref.digest for ref, _ in first.objects) == sorted(
        ref.digest for ref, _ in first.objects
    )
    assert canonical_bytes(load(first).document) == canonical_bytes(
        document(identity())
    )
    assert load(first).document["context"]["a/b"]["~"] == (1, True, None)
    assert load(first).document["context"]["numeric"]["0"] == "object key"
    with pytest.raises(CompactError, match="identity_mismatch"):
        load(first, selected=identity("assignment-two"))


def test_physical_pin_and_identity_fail_before_reference_disclosure() -> None:
    prepared = plan()
    calls = []

    def reader(ref):
        calls.append(ref)
        raise AssertionError("reader must not be called")

    with pytest.raises(CompactError, match="capsule_checksum_mismatch"):
        decode_capsule(
            raw=prepared.envelope_bytes + b"\n",
            expected_checksum=prepared.envelope_checksum,
            expected_identity=identity(),
            read_object=reader,
        )
    with pytest.raises(CompactError, match="identity_mismatch"):
        decode_capsule(
            raw=prepared.envelope_bytes,
            expected_checksum=prepared.envelope_checksum,
            expected_identity=identity("assignment-two"),
            read_object=reader,
        )
    assert calls == []


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", True),
        ("reader_floor", True),
        ("writer_floor", 3),
        ("required_features", ["unknown"]),
    ],
)
def test_envelope_dispatch_fails_closed(key: str, value: Any) -> None:
    envelope = json.loads(plan().envelope_bytes)
    envelope[key] = value
    raw = canonical_bytes(envelope)
    with pytest.raises(CompactError):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda ref: pytest.fail("unsupported format read an object"),
        )


def test_legacy_yaml_is_not_decoded_or_rewritten() -> None:
    raw = b"\xef\xbb\xbfschema_version: 1\r\n"
    original = bytes(raw)
    with pytest.raises(CompactError):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda ref: pytest.fail("legacy reader called"),
        )
    assert raw == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("size", True),
        ("size", -1),
        ("size", 2**63),
        ("digest", "A" * 64),
        ("algorithm", "sha1"),
    ],
)
def test_reference_validation(field: str, value: Any) -> None:
    fields = asdict(raw_ref(b"x"))
    fields[field] = value
    with pytest.raises(CompactError):
        ObjectRef(**fields)


@pytest.mark.parametrize(
    "mutation,code",
    [
        (
            lambda m: m["identity"].update(context_id="another-capsule"),
            "identity_mismatch",
        ),
        (lambda m: m.update(version=True), "unsupported_manifest"),
        (lambda m: m["fragments"].reverse(), "fragment_order"),
        (lambda m: m["fragments"].append(m["fragments"][0]), "fragment_order"),
        (lambda m: m["fragments"][0].update(target=""), "invalid_pointer"),
        (lambda m: m["fragments"][0].update(target="/~2"), "invalid_pointer"),
        (
            lambda m: m["fragments"][0]["object"].update(codec="raw.v1"),
            "unsupported_codec",
        ),
    ],
)
def test_manifest_rejection_before_leaf_reads(mutation: Any, code: str) -> None:
    raw, objects = rewrite_manifest(plan(), mutation)
    calls = []

    def reader(ref: ObjectRef) -> bytes:
        calls.append(ref)
        assert len(calls) == 1
        return objects[ref.digest]

    with pytest.raises(CompactError, match=code):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=reader,
        )


@pytest.mark.parametrize(
    "targets", [["/x", "/x/y"], ["/x/y", "/x"], ["/x~1y", "/x~1y/z"]]
)
def test_expansion_ancestor_collisions_before_fragment_fetch(
    targets: list[str],
) -> None:
    def mutate(manifest: Any) -> None:
        ref = manifest["fragments"][0]["object"]
        manifest["fragments"] = sorted(
            [{"target": target, "object": ref} for target in targets],
            key=lambda item: item["target"].encode(),
        )

    raw, objects = rewrite_manifest(plan(), mutate)
    with pytest.raises(CompactError, match="expansion_collision"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda ref: objects[ref.digest],
        )


def test_expansion_budget_prevents_fetch_and_allocation() -> None:
    def mutate(manifest: Any) -> None:
        ref = manifest["fragments"][0]["object"]
        ref["size"] = MAX_BYTES
        manifest["fragments"] = [{"target": "/large", "object": ref}]

    raw, objects = rewrite_manifest(plan(), mutate)
    calls = []

    def reader(ref: ObjectRef) -> bytes:
        calls.append(ref)
        assert len(calls) == 1
        return objects[ref.digest]

    with pytest.raises(CompactError, match="expansion_size_limit"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=reader,
        )


def test_total_closure_budget_is_checked_before_fragment_fetch() -> None:
    def mutate(manifest: Any) -> None:
        ref = manifest["fragments"][0]["object"]
        ref["size"] = MAX_BYTES - 10
        manifest["fragments"] = [{"target": "/x", "object": ref}]

    raw, objects = rewrite_manifest(plan(), mutate)
    calls = []

    def reader(ref: ObjectRef) -> bytes:
        calls.append(ref)
        assert len(calls) == 1
        return objects[ref.digest]

    with pytest.raises(CompactError, match="closure_size_limit"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=reader,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("context", []),
        ("resolved_resources", False),
        (
            "resource_bindings",
            {"schema_version": True, "status": "available", "resources": []},
        ),
    ],
)
def test_pinned_semantic_schema_rejects_malformed_fields(
    field: str, value: Any
) -> None:
    source = document(identity())
    source[field] = value
    with pytest.raises(CompactError, match="semantic_schema_invalid"):
        pack_capsule(identity=identity(), document=source, material=())


def test_decode_checks_semantic_schema_even_after_storage_rehash() -> None:
    body = b"true"
    bad_ref = object_ref(
        body, media_type="application/json", codec="pf.context-fragment.v1"
    )

    def mutate(manifest: Any) -> None:
        manifest["fragments"].append(
            {"target": "/resolved_resources", "object": asdict(bad_ref)}
        )
        manifest["fragments"].sort(key=lambda item: item["target"].encode())

    raw, objects = rewrite_manifest(plan(), mutate)
    objects[bad_ref.digest] = body
    with pytest.raises(CompactError, match="semantic_schema_invalid"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda ref: objects[ref.digest],
        )


def test_same_digest_with_different_reference_metadata_rejected() -> None:
    def mutate(manifest: Any) -> None:
        ref = copy.deepcopy(manifest["fragments"][0]["object"])
        ref["size"] += 1
        manifest["fragments"].append({"target": "/zz-extra", "object": ref})

    raw, objects = rewrite_manifest(plan(), mutate)
    with pytest.raises(CompactError, match="reference_metadata_mismatch"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda ref: objects[ref.digest],
        )


def test_corrupt_fragment_and_noncanonical_fragment_rejected() -> None:
    prepared = plan()
    objects = {ref.digest: raw for ref, raw in prepared.objects}
    fragment = next(
        ref for ref, _ in prepared.objects if ref.codec == "pf.context-fragment.v1"
    )
    objects[fragment.digest] = b" " * fragment.size
    with pytest.raises(CompactError, match="object_hash_mismatch"):
        load(prepared, objects=objects)
    noncanonical = b'{ "x":1}'
    ref = object_ref(
        noncanonical, media_type="application/json", codec="pf.context-fragment.v1"
    )

    def mutate(manifest: Any) -> None:
        manifest["fragments"][0]["object"] = asdict(ref)

    raw, objects = rewrite_manifest(prepared, mutate)
    objects[ref.digest] = noncanonical
    with pytest.raises(CompactError, match="noncanonical_json"):
        decode_capsule(
            raw=raw,
            expected_checksum=checksum(raw),
            expected_identity=identity(),
            read_object=lambda selected: objects[selected.digest],
        )


def test_recursive_refs_are_not_data_or_resolved() -> None:
    source = document(identity())
    source["extra"] = {"nested": asdict(raw_ref(b"hidden"))}
    with pytest.raises(CompactError, match="recursive_reference"):
        pack_capsule(identity=identity(), document=source, material=())


@pytest.mark.parametrize("field", ["contract_checksum", "assignment_intent_checksum"])
def test_packing_does_not_recompute_or_repair_checksums(field: str) -> None:
    source = document(identity())
    source["execution_contract"][field] = "sha256:" + "0" * 64
    if field != "contract_checksum":
        contract = source["execution_contract"]
        contract["contract_checksum"] = fingerprint(
            {
                key: value
                for key, value in contract.items()
                if key != "contract_checksum"
            }
        )
    with pytest.raises(CompactError, match="checksum_mismatch"):
        pack_capsule(identity=identity(), document=source, material=())


def test_metadata_material_never_fetches_hidden_body() -> None:
    descriptor = raw_ref(b'{"public_id":"compiler"}')
    material = (
        {
            "resource_id": "compiler",
            "role": "descriptor",
            "access": "metadata",
            "object": asdict(descriptor),
            "original_checksum": "sha256:" + "1" * 64,
            "required": True,
            "interpretation_version": "1",
        },
    )
    prepared = plan(material=material)
    assert descriptor.digest not in {ref.digest for ref, _ in prepared.objects}
    verified = load(prepared)
    assert verified.material[0]["access"] == "metadata"
    assert "material" not in verified.document
    bad = copy.deepcopy(material)
    bad[0]["role"] = "knowledge"
    with pytest.raises(CompactError, match="metadata_body_reference"):
        plan(material=bad)


def test_constructor_has_no_io_or_callback_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("construction performed I/O or invoked a capability")

    root = Path(os.environ.get("PF_COMPACT_TEST_ROOT", str(Path.cwd())))
    monkeypatch.setattr(Path, "lstat", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    ProjectObjectStore(root, authorize=forbidden, sync_directory=forbidden)
    with pytest.raises(CompactError, match="capability_unavailable"):
        ProjectObjectStore(root, authorize=None, sync_directory=forbidden)
    with pytest.raises(CompactError, match="capability_unavailable"):
        ProjectObjectStore(root, authorize=forbidden, sync_directory=None)


def test_exact_authorization_denial_precedes_disclosure(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = raw_ref(b"private")
    expected = object_relative_path(ref).as_posix()
    calls = []

    def deny(path: str, action: str) -> None:
        calls.append((path, action))
        raise PermissionError("denied")

    denied = store(sandbox, authorize=deny)
    monkeypatch.setattr(
        Path, "lstat", lambda *args: pytest.fail("stat before authorization")
    )
    monkeypatch.setattr(
        os, "open", lambda *args: pytest.fail("open before authorization")
    )
    for operation in (
        lambda: denied.read(ref, maximum_bytes=10),
        lambda: denied.verify(ref),
        lambda: denied.publish(ref, [b"private"]),
    ):
        with pytest.raises(PermissionError, match="denied"):
            operation()
    assert calls == [
        (expected, "read"),
        (expected, "read"),
        (expected, "write_artifact"),
    ]


def test_streaming_publication_reuse_and_read_budget(sandbox: Path) -> None:
    raw = b"portable\x00binary" * 20000
    ref = raw_ref(raw)
    syncs = []
    objects = store(sandbox, sync=syncs.append)
    objects.publish(
        ref, (raw[index : index + 4096] for index in range(0, len(raw), 4096))
    )
    path = sandbox / object_relative_path(ref)
    before = path.stat()
    objects.publish(ref, [raw])
    assert path.stat().st_ino == before.st_ino
    objects.verify(ref)
    assert objects.read(ref, maximum_bytes=len(raw)) == raw
    with pytest.raises(CompactError, match="size_limit"):
        objects.read(ref, maximum_bytes=len(raw) - 1)
    assert syncs and syncs[-1] == path.parent
    assert not list(path.parent.glob(".compact-*.tmp"))


def test_real_store_roundtrip_authorizes_each_reference(sandbox: Path) -> None:
    prepared = plan()
    calls = []
    allowed = {object_relative_path(ref).as_posix() for ref, _ in prepared.objects}

    def authorize(path: str, action: str) -> None:
        assert path in allowed
        calls.append((path, action))

    objects = store(sandbox, authorize=authorize)
    manifest_digest = json.loads(prepared.envelope_bytes)["manifest"]["digest"]
    for ref, body in sorted(
        prepared.objects, key=lambda item: item[0].digest == manifest_digest
    ):
        objects.publish(ref, [body])
    calls.clear()
    decoded = decode_capsule(
        raw=prepared.envelope_bytes,
        expected_checksum=prepared.envelope_checksum,
        expected_identity=identity(),
        read_object=lambda ref: objects.read(ref, maximum_bytes=MAX_BYTES),
    )
    assert canonical_bytes(decoded.document) == canonical_bytes(document(identity()))
    assert (
        calls[0][0]
        == object_relative_path(
            next(ref for ref, _ in prepared.objects if ref.digest == manifest_digest)
        ).as_posix()
    )
    assert all(action == "read" for _, action in calls)
    assert {path for path, _ in calls} == allowed


def test_false_authorization_result_is_not_a_grant(sandbox: Path) -> None:
    objects = store(sandbox, authorize=lambda path, action: False)
    with pytest.raises(CompactError, match="authorization_invalid"):
        objects.publish(raw_ref(b"good"), [b"good"])
    assert not (sandbox / ".pf").exists()


def test_existing_object_reuse_requires_read_grant(sandbox: Path) -> None:
    ref = raw_ref(b"same")
    store(sandbox).publish(ref, [b"same"])

    def write_only(path: str, action: str) -> None:
        if action == "read":
            raise PermissionError("read denied")

    with pytest.raises(PermissionError, match="read denied"):
        store(sandbox, authorize=write_only).publish(ref, [b"same"])
    assert (sandbox / object_relative_path(ref)).read_bytes() == b"same"


def test_missing_corrupt_and_conflicting_destination(sandbox: Path) -> None:
    objects = store(sandbox)
    ref = raw_ref(b"good")
    with pytest.raises(CompactError, match="object_missing"):
        objects.read(ref, maximum_bytes=4)
    objects.publish(ref, [b"good"])
    path = sandbox / object_relative_path(ref)
    path.write_bytes(b"evil")
    with pytest.raises(CompactError, match="object_hash_mismatch"):
        objects.verify(ref)
    with pytest.raises(CompactError, match="object_hash_mismatch"):
        objects.publish(ref, [b"good"])
    assert path.read_bytes() == b"evil"
    path.write_bytes(b"shorter-or-longer")
    with pytest.raises(CompactError, match="object_size_mismatch"):
        objects.read(ref, maximum_bytes=4)


@pytest.mark.parametrize(
    "chunks,code",
    [
        ([b"bad!"], "object_hash_mismatch"),
        ([b"too long"], "object_size_mismatch"),
        ([b"x"], "object_size_mismatch"),
        ([bytearray(b"good")], "invalid_bytes"),
    ],
)
def test_bad_stream_never_publishes(sandbox: Path, chunks: Any, code: str) -> None:
    ref = raw_ref(b"good")
    with pytest.raises(CompactError, match=code):
        store(sandbox).publish(ref, chunks)
    path = sandbox / object_relative_path(ref)
    assert not path.exists()
    assert not list(path.parent.glob(".compact-*.tmp"))


def test_link_failure_has_no_fallback_replace(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = raw_ref(b"good")

    def unavailable(*args: Any) -> None:
        raise OSError("link unavailable")

    monkeypatch.setattr(compact_objects.os, "link", unavailable)
    with pytest.raises(OSError, match="link unavailable"):
        store(sandbox).publish(ref, [b"good"])
    assert not (sandbox / object_relative_path(ref)).exists()


def test_file_fsync_failure_never_publishes(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: Any) -> None:
        raise OSError("fsync unavailable")

    monkeypatch.setattr(compact_objects.os, "fsync", fail)
    ref = raw_ref(b"good")
    with pytest.raises(OSError, match="fsync unavailable"):
        store(sandbox).publish(ref, [b"good"])
    assert not (sandbox / object_relative_path(ref)).exists()


@pytest.mark.parametrize("winner", [b"good", b"evil"])
def test_no_clobber_when_destination_appears_during_link(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch, winner: bytes
) -> None:
    ref = raw_ref(b"good")
    path = sandbox / object_relative_path(ref)

    def occupied(source: Path, destination: Path) -> None:
        destination.write_bytes(winner)
        raise FileExistsError("another publisher won")

    monkeypatch.setattr(compact_objects.os, "link", occupied)
    if winner == b"good":
        store(sandbox).publish(ref, [b"good"])
    else:
        with pytest.raises(CompactError, match="object_hash_mismatch"):
            store(sandbox).publish(ref, [b"good"])
    assert path.read_bytes() == winner


def test_interrupted_stream_does_not_publish_partial_object(sandbox: Path) -> None:
    def interrupted() -> Iterator[bytes]:
        yield b"go"
        raise OSError("source interrupted")

    ref = raw_ref(b"good")
    with pytest.raises(OSError, match="source interrupted"):
        store(sandbox).publish(ref, interrupted())
    path = sandbox / object_relative_path(ref)
    assert not path.exists()
    assert not list(path.parent.glob(".compact-*.tmp"))


def test_directory_sync_failure_leaves_orphan_and_retry_reuses(sandbox: Path) -> None:
    ref = raw_ref(b"orphan")
    path = sandbox / object_relative_path(ref)

    def fail_after_link(directory: Path) -> None:
        if path.exists():
            raise OSError("directory durability unavailable")

    with pytest.raises(OSError, match="directory durability unavailable"):
        store(sandbox, sync=fail_after_link).publish(ref, [b"orphan"])
    assert path.read_bytes() == b"orphan"
    inode = path.stat().st_ino
    store(sandbox).publish(ref, [b"orphan"])
    assert path.stat().st_ino == inode


def test_parent_sync_failure_propagates_before_link(sandbox: Path) -> None:
    ref = raw_ref(b"good")

    def fail(directory: Path) -> None:
        raise OSError("parent durability unavailable")

    with pytest.raises(OSError, match="parent durability unavailable"):
        store(sandbox, sync=fail).publish(ref, [b"good"])
    assert not (sandbox / object_relative_path(ref)).exists()


def test_false_directory_sync_result_fails_closed(sandbox: Path) -> None:
    ref = raw_ref(b"good")
    with pytest.raises(CompactError, match="durability_invalid"):
        store(sandbox, sync=lambda path: False).publish(ref, [b"good"])
    assert not (sandbox / object_relative_path(ref)).exists()


def test_simulated_collision_requires_actual_byte_equality(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = raw_ref(b"good")
    objects = store(sandbox)
    objects.publish(ref, [b"good"])
    path = sandbox / object_relative_path(ref)
    path.write_bytes(b"evil")
    original = objects._consume

    def simulated_equal_hash(
        selected: Path, selected_ref: ObjectRef, *, keep: bool
    ) -> bytes:
        if selected == path:
            return b""  # Model a digest collision, not permission or equality.
        return original(selected, selected_ref, keep=keep)

    monkeypatch.setattr(objects, "_consume", simulated_equal_hash)
    with pytest.raises(CompactError, match="object_collision"):
        objects.publish(ref, [b"good"])
    assert path.read_bytes() == b"evil"


def test_symlink_parent_denied_without_following(sandbox: Path) -> None:
    outside = sandbox / "elsewhere"
    outside.mkdir()
    (sandbox / ".pf").mkdir()
    try:
        (sandbox / ".pf" / "objects").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("host does not permit creation of this disposable symlink fixture")
    ref = raw_ref(b"good")
    with pytest.raises(CompactError, match="unsafe_object_path"):
        store(sandbox).publish(ref, [b"good"])
    assert list(outside.iterdir()) == []


def test_windows_reparse_attribute_is_rejected_without_following(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = sandbox / ".pf"
    metadata.mkdir()
    real_lstat = Path.lstat

    def marked(path: Path) -> Any:
        info = real_lstat(path)
        if path == metadata:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", marked)
    with pytest.raises(CompactError, match="unsafe_object_path"):
        store(sandbox).publish(raw_ref(b"good"), [b"good"])
    assert not (metadata / "objects").exists()
