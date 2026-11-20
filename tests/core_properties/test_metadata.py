"""Permanent metadata, lifetime and provenance regressions for the real owner."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path

import pytest

from processforge_core.common.properties import (
    CoreIdentity,
    CoreProperties,
    DistributionMetadataReader,
)
from processforge_core.maintenance.update import CORE_MANIFEST_NAME


def assert_unknown(identity: CoreIdentity, reason: str, private: Path) -> None:
    """Require bounded portable diagnostics without swallowed known identity."""
    assert identity == CoreIdentity(reason=reason)
    assert len(identity.reason) <= 64
    assert str(private) not in repr(identity)
    assert "PRIVATE_CANARY" not in repr(identity)


def test_native_metadata_labels(
    tmp_path, write_distribution, release_label, source_commit
):
    properties = write_distribution(tmp_path, release_label)
    identity = properties.loaded
    raw = (tmp_path / CORE_MANIFEST_NAME).read_bytes()
    assert identity == CoreIdentity(
        version=release_label,
        build_id="manifest:sha256:" + hashlib.sha256(raw).hexdigest(),
        source_commit=source_commit,
        source_kind="manifest",
        status="ready",
        reason="",
    )
    assert properties.installed() == identity
    assert properties.spec_version == "1.0"
    assert properties.schema_bundle_version == "1.0"
    assert str(tmp_path) not in repr(identity)


def test_loaded_survives_update_removal_and_new_construction(
    tmp_path, write_distribution
):
    properties = write_distribution(tmp_path)
    loaded = properties.loaded
    replacement = write_distribution(tmp_path, "8.1.2-dev.4+new")
    assert properties.loaded is loaded
    assert properties.installed() == replacement.loaded
    assert properties.installed().version != loaded.version
    (tmp_path / "VERSION").unlink()
    assert_unknown(properties.installed(), "version_missing", tmp_path)
    assert properties.loaded is loaded
    assert_unknown(
        CoreProperties.from_distribution(tmp_path).loaded, "version_missing", tmp_path
    )
    restored = write_distribution(tmp_path, "9.0.0-rc.2")
    assert properties.installed() == restored.loaded
    assert properties.loaded is loaded


def test_same_label_new_metadata_build_and_no_payload_integrity_claim(
    tmp_path, write_distribution
):
    properties = write_distribution(tmp_path)
    loaded = properties.loaded
    newer = write_distribution(tmp_path, generated_at="2024-01-03T03:04:05Z")
    assert newer.loaded.version == loaded.version
    assert newer.loaded.source_commit == loaded.source_commit
    assert newer.loaded.build_id != loaded.build_id
    assert properties.installed() == newer.loaded
    assert properties.loaded is loaded
    # Metadata observation makes no claim about payloads outside its control files.
    (tmp_path / "payload.py").write_text("changed payload\n", encoding="utf-8")
    assert properties.installed() == newer.loaded


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"wrong",
        b"v1.2.3",
        b"01.2.3",
        b"1.2",
        b"1.2.3\nPRIVATE_CANARY",
        b"\xff",
        b"1.2.3-" + b"x" * 123,
    ],
)
def test_invalid_version_is_honest_unknown(tmp_path, raw):
    (tmp_path / "VERSION").write_bytes(raw)
    assert_unknown(
        DistributionMetadataReader(tmp_path).read(), "version_invalid", tmp_path
    )


def test_missing_version_does_not_select_cwd(tmp_path, monkeypatch, write_distribution):
    neighbour = tmp_path / "neighbour"
    write_distribution(neighbour, "99.3.4+neighbour")
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.chdir(neighbour)
    assert_unknown(
        CoreProperties.from_distribution(target).loaded, "version_missing", tmp_path
    )


@pytest.mark.parametrize("raw", [b"{", b"\xff", b"[]", b"null", b'"PRIVATE_CANARY"'])
def test_malformed_manifest(tmp_path, write_distribution, raw):
    write_distribution(tmp_path)
    (tmp_path / CORE_MANIFEST_NAME).write_bytes(raw)
    assert_unknown(
        DistributionMetadataReader(tmp_path).read(), "manifest_invalid", tmp_path
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("kind", "other"),
        ("source", []),
        ("files", {}),
        ("files", [None]),
    ],
)
def test_invalid_manifest_structure(tmp_path, write_distribution, field, value):
    write_distribution(tmp_path)
    path = tmp_path / CORE_MANIFEST_NAME
    metadata = json.loads(path.read_bytes())
    metadata[field] = value
    path.write_text(json.dumps(metadata), encoding="utf-8")
    assert_unknown(
        DistributionMetadataReader(tmp_path).read(), "manifest_invalid", tmp_path
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("relative_path", "../PRIVATE_CANARY"),
        ("relative_path", "/absolute"),
        ("relative_path", "x\\y"),
        ("sha256", "bad"),
    ],
)
def test_native_manifest_file_validation_is_used(
    tmp_path, write_distribution, field, value
):
    write_distribution(tmp_path)
    path = tmp_path / CORE_MANIFEST_NAME
    metadata = json.loads(path.read_bytes())
    metadata["files"][0][field] = value
    path.write_text(json.dumps(metadata), encoding="utf-8")
    assert_unknown(
        DistributionMetadataReader(tmp_path).read(), "manifest_invalid", tmp_path
    )


def test_inconsistent_version_and_manifest(tmp_path, write_distribution):
    properties = write_distribution(tmp_path)
    (tmp_path / "VERSION").write_text("8.0.0-rc.2", encoding="utf-8")
    assert_unknown(properties.installed(), "version_manifest_mismatch", tmp_path)
    assert properties.loaded.version != "unknown"


@pytest.mark.parametrize("name", ["VERSION", CORE_MANIFEST_NAME])
def test_unreadable_metadata_does_not_leak_os_error(
    tmp_path, monkeypatch, write_distribution, name
):
    properties = write_distribution(tmp_path)
    original = Path.open

    def denied(path, *args, **kwargs):
        if path == tmp_path / name:
            raise PermissionError("PRIVATE_CANARY " + str(tmp_path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    assert_unknown(properties.installed(), "metadata_unreadable", tmp_path)
    assert properties.loaded.status == "ready"


@pytest.mark.parametrize(
    ("name", "limit"), [("VERSION", 1024), (CORE_MANIFEST_NAME, 8 * 1024 * 1024)]
)
def test_oversized_metadata_has_bounded_read(
    tmp_path, monkeypatch, write_distribution, name, limit
):
    properties = write_distribution(tmp_path)
    target = tmp_path / name
    target.write_bytes(b"x" * (limit + 17))
    original = Path.open
    reads = []

    class ObservedStream:
        def __enter__(self):
            self.stream = original(target, "rb")
            return self

        def read(self, size=-1):
            reads.append(size)
            assert 0 <= size <= limit + 1
            return self.stream.read(size)

        def __exit__(self, *exc):
            self.stream.close()

    def observe(path, *args, **kwargs):
        return ObservedStream() if path == target else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observe)
    assert_unknown(properties.installed(), "metadata_too_large", tmp_path)
    assert reads == [limit + 1]


@pytest.mark.parametrize("name", ["VERSION", CORE_MANIFEST_NAME])
def test_metadata_changed_mid_observation_is_rejected(
    tmp_path, monkeypatch, write_distribution, name
):
    properties = write_distribution(tmp_path)
    original = DistributionMetadataReader._read
    changed = False

    def read(path, limit):
        nonlocal changed
        result = original(path, limit)
        if path == tmp_path / name and not changed:
            changed = True
            path.write_bytes(result + b" ")
        return result

    monkeypatch.setattr(DistributionMetadataReader, "_read", staticmethod(read))
    assert_unknown(properties.installed(), "metadata_changed", tmp_path)
    assert properties.loaded.status == "ready"


@pytest.mark.parametrize("commit", [None, 7, "broken", "f" * 39])
def test_invalid_manifest_provenance_is_partial(tmp_path, write_distribution, commit):
    write_distribution(tmp_path)
    path = tmp_path / CORE_MANIFEST_NAME
    metadata = json.loads(path.read_bytes())
    metadata["source"]["commit"] = commit
    path.write_text(json.dumps(metadata), encoding="utf-8")
    identity = DistributionMetadataReader(tmp_path).read()
    assert identity.version == metadata["version"]
    assert identity.source_commit == "unknown"
    assert identity.source_kind == "manifest"
    assert identity.status == "partial"
    assert identity.reason == "source_revision_unavailable"
    assert identity.build_id.startswith("manifest:sha256:")


def test_manifest_removal_observes_partial_metadata(tmp_path, write_distribution):
    properties = write_distribution(tmp_path)
    (tmp_path / CORE_MANIFEST_NAME).unlink()
    installed = properties.installed()
    assert installed.version == properties.loaded.version
    assert installed.status == "partial"
    assert installed.source_kind == "unmanaged"
    assert installed.build_id == installed.source_commit == "unknown"
    assert installed.reason == "build_metadata_unavailable"
    assert properties.loaded.status == "ready"


@pytest.mark.parametrize(
    "kind", ["detached40", "detached64", "loose", "packed", "worktree-packed"]
)
def test_git_head_provenance_with_unicode_refs(
    tmp_path, monkeypatch, source_commit, kind
):
    root = tmp_path / "source"
    root.mkdir()
    (root / "VERSION").write_text("8.9.1-dev.7", encoding="utf-8")
    common = root / ".git"
    admin = common
    if kind == "worktree-packed":
        common = tmp_path / "repository"
        admin = common / "worktrees" / "task"
        admin.mkdir(parents=True)
        (root / ".git").write_text(
            "gitdir: ../repository/worktrees/task\n", encoding="utf-8"
        )
        (admin / "commondir").write_text("../..\n", encoding="utf-8")
    else:
        common.mkdir()
    commit = (
        hashlib.sha256(b"sha256 repository fixture").hexdigest()
        if kind == "detached64"
        else source_commit
    )
    ref = "refs/heads/ветка-漢字"
    if kind.startswith("detached"):
        (admin / "HEAD").write_text(commit.upper() + "\n", encoding="utf-8")
    else:
        (admin / "HEAD").write_text("ref: " + ref + "\n", encoding="utf-8")
        if kind == "loose":
            target = common / ref
            target.parent.mkdir(parents=True)
            target.write_text(commit + "\n", encoding="utf-8")
        else:
            (common / "packed-refs").write_text(
                "# pack-refs with: peeled\n" + commit + " " + ref + "\n",
                encoding="utf-8",
            )
    original = Path.open
    opened = []

    def observe(path, *args, **kwargs):
        assert path.is_relative_to(tmp_path)
        opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", observe)
    identity = DistributionMetadataReader(root).read()
    assert identity.source_commit == commit
    assert identity.build_id == "git:" + commit
    assert identity.source_kind == "source_checkout"
    assert identity.status == "ready" and identity.reason == ""
    assert set(opened) <= {
        root / "VERSION",
        root / CORE_MANIFEST_NAME,
        root / ".git",
        admin / "commondir",
        admin / "HEAD",
        common / ref,
        common / "packed-refs",
    }


@pytest.mark.parametrize(
    "head",
    [b"garbage", b"\xff", b"ref: refs/heads/../../PRIVATE_CANARY", b"x" * 513],
)
def test_unavailable_git_revision_does_not_invent_provenance(tmp_path, head):
    (tmp_path / "VERSION").write_text("8.9.1-dev.7", encoding="utf-8")
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_bytes(head)
    identity = DistributionMetadataReader(tmp_path).read()
    assert identity.version == "8.9.1-dev.7"
    assert identity.build_id == identity.source_commit == "unknown"
    assert identity.status == "partial"
    assert identity.reason == "build_metadata_unavailable"
    assert "PRIVATE_CANARY" not in repr(identity)


def test_identity_is_a_frozen_portable_value_and_reader_is_injected():
    first = CoreIdentity(version="7.8.9-dev.2", status="partial")
    second = CoreIdentity(version="9.8.7+changed", status="partial")

    class Reader:
        def __init__(self):
            self.current = first
            self.calls = 0

        def read(self):
            self.calls += 1
            return self.current

    reader = Reader()
    properties = CoreProperties(reader)
    assert reader.calls == 1
    assert properties.loaded is first
    reader.current = second
    assert properties.loaded is first and reader.calls == 1
    assert properties.installed() is second
    assert properties.installed() is second and reader.calls == 3
    with pytest.raises(AttributeError):
        properties.loaded = second
    for field in fields(first):
        with pytest.raises(FrozenInstanceError):
            setattr(first, field.name, "changed")
        with pytest.raises(FrozenInstanceError):
            delattr(first, field.name)
    assert set(asdict(first)) == {
        "version",
        "build_id",
        "source_commit",
        "source_kind",
        "status",
        "reason",
    }
    assert all(isinstance(value, str) for value in asdict(first).values())
