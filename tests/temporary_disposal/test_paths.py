"""Small exact-object deletion fixtures inside explicitly selected scratch."""

import os
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.maintenance import temporary_disposal as disposal


@pytest.fixture
def owned_root():
    base = Path(os.environ["PF_TEST_SCRATCH_ROOT"])
    assert base.is_absolute()
    root = base / uuid4().hex
    root.mkdir()
    yield root
    # Each fixture owns only these small direct children; never recurse or chmod.
    for path in root.iterdir():
        path.unlink()
    root.rmdir()


def test_exact_owned_file_and_absence(owned_root):
    resource = disposal.create_owned_file(owned_root / "result")
    resource.path.write_bytes(b"payload")
    assert disposal.dispose_owned(resource).result == "needed"
    released = disposal.release_owned(resource)
    receipt = disposal.dispose_owned(released)
    assert (receipt.result, receipt.deleted_files, receipt.deleted_bytes) == (
        "deleted",
        1,
        7,
    )
    receipt = disposal.dispose_owned(released)
    assert (receipt.result, receipt.deleted_files, receipt.deleted_bytes) == (
        "already_absent",
        0,
        0,
    )


def test_foreign_identity_and_boundary_refused(owned_root):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    forged = replace(resource, _creation=object())
    assert disposal.dispose_owned(forged).result == "ownership_unknown"
    assert (
        disposal.dispose_owned(replace(resource, identity=(-1, -1))).result
        == "identity_changed"
    )
    assert (
        disposal.dispose_owned(replace(resource, boundary=owned_root.parent)).result
        == "unsafe_path"
    )
    assert resource.path.exists()


def test_replaced_object_is_never_deleted(owned_root):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    saved = owned_root / "original"
    resource.path.replace(saved)
    resource.path.write_bytes(b"foreign replacement")
    assert disposal.dispose_owned(resource).result == "identity_changed"
    assert resource.path.read_bytes() == b"foreign replacement"
    assert saved.exists()


def test_reparse_is_refused_without_following(owned_root, monkeypatch):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    monkeypatch.setattr(disposal, "_linked", lambda info: True)
    assert disposal.dispose_owned(resource).result == "unsafe_path"
    assert resource.path.exists()


def test_known_consumers_and_unpublished_evidence_preserved(owned_root):
    resource = disposal.create_owned_file(owned_root / "result")
    for use in (
        disposal.TemporaryUse(True, 1, True),
        disposal.TemporaryUse(True, 0, False),
    ):
        assert disposal.dispose_owned(replace(resource, use=use)).result == "needed"
    assert resource.path.exists()


def test_denied_delete_has_exact_receipt(owned_root, monkeypatch):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))

    def denied(*args, **kwargs):
        raise PermissionError(13, "simulated denial")

    if os.name == "nt":
        monkeypatch.setattr(disposal, "_windows_delete", denied)
    else:
        monkeypatch.setattr(disposal.os, "unlink", denied)
    receipt = disposal.dispose_owned(resource)
    assert (receipt.result, receipt.error_code, receipt.deleted_files) == (
        "cleanup_pending",
        13,
        0,
    )
    assert resource.path.exists()
