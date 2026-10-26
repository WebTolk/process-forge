"""Real publisher success/failure cleanup and truthful failure reporting."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.configuration.models import TemporaryFilesConfig
from processforge_core.maintenance import temporary_disposal as disposal
from processforge_core.work.publication import WorkDocumentPublisher


@pytest.fixture
def owned_root():
    base = Path(os.environ["PF_TEST_SCRATCH_ROOT"])
    assert base.is_absolute()
    root = base / uuid4().hex
    root.mkdir()
    yield root
    for path in root.iterdir():
        path.unlink()
    root.rmdir()


def test_permission_requires_error_free_snapshot(owned_root):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    config = TemporaryFilesConfig(retain_unused=True)
    assert (
        disposal.dispose_owned(resource, config=config).result
        == "retained_by_configuration"
    )
    errors = ("configuration_read_failed",)
    receipt = disposal.dispose_owned(
        resource, config=config, configuration_errors=errors
    )
    assert receipt.result == "deleted" and receipt.configuration_errors == errors


@pytest.mark.parametrize("mode", ["off", "notify"])
@pytest.mark.parametrize("age", [1, 87600])
def test_notifications_do_not_authorize_retention(owned_root, mode, age):
    resource = disposal.release_owned(disposal.create_owned_file(owned_root / "result"))
    assert (
        disposal.dispose_owned(resource, config=TemporaryFilesConfig(mode, age)).result
        == "deleted"
    )


def test_actual_publisher_success_and_failure(owned_root, monkeypatch):
    publisher = WorkDocumentPublisher(
        text_writer=lambda: None, yaml_formatter=lambda: None
    )
    target = owned_root / "output"
    publisher.write_text(target, "durable")
    assert list(owned_root.iterdir()) == [target]
    original = OSError("original publication failure")

    def fail(*args):
        raise original

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError) as caught:
        publisher.write_text(target, "unpublished")
    assert caught.value is original
    assert target.read_text() == "durable"
    assert list(owned_root.iterdir()) == [target]


def test_cleanup_failure_preserves_primary_and_blocks_success(owned_root, monkeypatch):
    def pending(resource, **kwargs):
        return disposal.CleanupReceipt(
            resource.resource_id, "cleanup_pending", error_code=13
        )

    monkeypatch.setattr(disposal, "dispose_owned", pending)
    original = RuntimeError("producer failed")
    with pytest.raises(RuntimeError) as caught:
        with disposal.atomic_staging(owned_root / "output"):
            raise original
    assert caught.value is original
    assert any("cleanup_pending:13" in note for note in original.__notes__)
    with pytest.raises(disposal.CleanupError, match="cleanup_pending:13"):
        with disposal.atomic_staging(owned_root / "output"):
            pass
