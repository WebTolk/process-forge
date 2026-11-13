"""Physical storage qualification; fixture migration proof is not OS ownership.

The imported harness supplies deterministic migration safety for setup only.
Subsequent selection, filesystem changes, restore and interprocess gates use
the actual production ports. No live project or native publication is adopted.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from processforge_core.database import DatabaseError
from processforge_core.executions.composition import select_execution_storage
from processforge_core.executions.model import ExecutionError
from processforge_core.maintenance import storage_migration as migration
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.runtime.execution_admission import registry_file_lock

from .test_migration import Harness
from .test_storage_uuid import StorageHarness


@pytest.fixture
def fixture_root() -> Path:
    root = Path(os.environ["PF_W4_TEST_ROOT"]) / uuid4().hex
    root.mkdir(parents=True)
    return root


@pytest.fixture
def ready(fixture_root: Path) -> Harness:
    harness = Harness(fixture_root / "sql")
    harness.status("task", attempt=3)
    harness.status("é-ё", run="run-unicode", attempt=2)
    assert harness.apply()["status"] == "ready"
    return harness


def assert_sql(harness: Harness) -> None:
    selected = select_execution_storage(harness.project)
    assert selected.authority == "sql" and selected.repository is not None
    readiness = selected.repository.readiness()
    assert readiness.ready and readiness.store_id == "a" * 32
    assert readiness.generation == 1 and readiness.authority == "sql"
    assert selected.repository.current().records == ()
    assert {
        (item.key.project_id, item.key.run_id, item.key.task_id, item.key.attempt)
        for item in selected.repository.page_history().records
    } == {
        ("exact-project", "run", "task", 3),
        ("exact-project", "run-unicode", "é-ё", 2),
    }


def test_offline_move_uses_fresh_selector_and_ignores_old_projection(
    ready: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed offline project move preserves IDs and immutable fixture bytes."""
    protected = {
        "process-forge.yaml": (ready.flow / "process-forge.yaml").read_bytes(),
        "data/execution-storage.json": (
            ready.flow / "data/execution-storage.json"
        ).read_bytes(),
        "runs/fixture/assignment.yaml": b"stage: completed\n",
        "contexts/fixture-capsule.yaml": b"immutable: true\n",
        "resources/approved/fixture.yaml": b"accepted: exact-fixture-bytes\n",
    }
    for relative, raw in protected.items():
        path = ready.flow / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    evidence = {
        path.relative_to(ready.flow): path.read_bytes()
        for path in (ready.flow / "maintenance").rglob("*")
        if path.is_file()
    }
    source = ready.database.target.path
    physical = (source.stat().st_dev, source.stat().st_ino)
    moved = ready.project.with_name("offline relocated é-ё project")
    ready.project.rename(moved)
    ready.project = moved
    assert not source.exists()
    target = ready.flow / "data/pf.sqlite3"
    assert (target.stat().st_dev, target.stat().st_ino) == physical
    # A SQL reader must not consult this formerly valid migration source.
    (ready.flow / "runtime/agent-runs/run/task/status.json").write_bytes(
        b'{"status":"running",invalid'
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("SQL attach attempted migration or a new backup")

    monkeypatch.setattr(ready.service.__class__, "apply", forbidden)
    monkeypatch.setattr(ready.service.__class__, "resume", forbidden)
    monkeypatch.setattr(ready.service.backup.__class__, "create", forbidden)
    assert_sql(ready)
    assert {name: (ready.flow / name).read_bytes() for name in protected} == protected
    assert {
        path.relative_to(ready.flow): path.read_bytes()
        for path in (ready.flow / "maintenance").rglob("*")
        if path.is_file()
    } == evidence


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "corrupt",
        "foreign-header",
        "future-format",
        "foreign-store",
        "foreign-owner",
        "schema-checksum",
        "future-schema",
        "binding-project",
        "binding-store",
        "binding-profile",
        "binding-target",
        "manifest-owner",
        "unbound-namespace",
    ],
)
def test_bound_sql_refuses_without_json_fallback_or_relabel(
    ready: Harness, fault: str
) -> None:
    target = ready.database.target.path
    binding = ready.flow / "data/execution-storage.json"
    if fault == "missing":
        target.rename(target.with_name("offline-held.sqlite3"))
    elif fault == "corrupt":
        target.write_bytes(b"foreign corrupt SQLite fixture")
    elif fault in {
        "foreign-header",
        "future-format",
        "foreign-store",
        "foreign-owner",
        "schema-checksum",
        "future-schema",
    }:
        statement = {
            "foreign-header": "PRAGMA application_id=99",
            "future-format": "PRAGMA user_version=2",
            "foreign-store": "UPDATE pf_store_meta SET store_id='" + "b" * 32 + "'",
            "foreign-owner": "UPDATE pf_store_meta SET owner_id='other-project'",
            "schema-checksum": "UPDATE pf_schema_versions SET checksum='sha256:"
            + "0" * 64
            + "' WHERE namespace='execution'",
            "future-schema": "UPDATE pf_schema_versions SET version=2 WHERE namespace='execution'",
        }[fault]
        connection = sqlite3.connect(target)
        try:
            connection.execute(statement)
            connection.commit()
        finally:
            connection.close()
    elif fault.startswith("binding-"):
        document = json.loads(binding.read_bytes())
        field, value = {
            "binding-project": ("project_id", "other-project"),
            "binding-store": ("store_id", "b" * 32),
            "binding-profile": ("profile_id", "other-profile"),
            "binding-target": ("target_relative_path", "other/target.sqlite3"),
        }[fault]
        document[field] = value
        binding.write_text(json.dumps(document), encoding="utf-8")
    elif fault == "manifest-owner":
        (ready.flow / "process-forge.yaml").write_text(
            "project:\n  id: other-project\n", encoding="utf-8"
        )
    else:
        binding.unlink()
    before_target = target.read_bytes() if target.exists() else None
    before_binding = binding.read_bytes() if binding.exists() else None
    projection = ready.flow / "runtime/agent-runs/run/task/status.json"
    before_projection = projection.read_bytes()
    with pytest.raises((DatabaseError, ExecutionError)):
        select_execution_storage(ready.project)
    assert (target.read_bytes() if target.exists() else None) == before_target
    assert (binding.read_bytes() if binding.exists() else None) == before_binding
    assert projection.read_bytes() == before_projection
    assert not (ready.flow / "other").exists()


def test_hardlinked_store_refuses_before_proof_or_uuid(fixture_root: Path) -> None:
    storage = StorageHarness(fixture_root / "hardlink")
    storage.create()
    original = storage.target.target.read_bytes()
    alias = fixture_root / "alias.sqlite3"
    os.link(storage.target.target, alias)
    assert os.path.samefile(storage.target.target, alias)
    result = storage.ensure()
    assert result["blocked"] and result["error"]["code"] == "storage_path_unsafe"
    assert storage.proof_calls == 0 and not storage.slot
    assert storage.target.target.read_bytes() == alias.read_bytes() == original
    assert not (storage.owner / "maintenance").exists()


def directory_redirect(link: Path, destination: Path, owned: Path) -> None:
    assert link.parent.resolve().is_relative_to(owned.resolve())
    assert destination.resolve().is_relative_to(owned.resolve())
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(destination)],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert getattr(link.lstat(), "st_file_attributes", 0) & 0x400
    else:
        link.symlink_to(destination, target_is_directory=True)
        assert link.is_symlink()


@pytest.mark.parametrize("redirect", ["owner", "target-parent"])
def test_real_directory_redirection_refuses_without_mutation(
    fixture_root: Path, redirect: str
) -> None:
    storage = StorageHarness(fixture_root / "redirect")
    storage.create()
    original = storage.target.target.read_bytes()
    link = storage.flow if redirect == "owner" else storage.target.target.parent
    destination = link.with_name(link.name + "-physical")
    link.rename(destination)
    directory_redirect(link, destination, fixture_root)
    try:
        result = storage.ensure()
        assert result["blocked"] and result["error"]["code"] == "storage_path_unsafe"
        assert storage.proof_calls == 0
        assert storage.target.target.read_bytes() == original
        assert not (storage.flow / "data/storage-identities.json").exists()
        assert not (storage.flow / "maintenance").exists()
    finally:
        if os.name == "nt":
            os.rmdir(link)  # Removes the junction only, never its target.
        else:
            link.unlink()
        destination.rename(link)


_ACCESS_CHILD = """
import sys,time
from pathlib import Path
from processforge_core.maintenance.contracts import StorageMigrationContext,StoreTarget
from processforge_core.maintenance.storage_migration import storage_identity_access
from processforge_core.runtime.execution_admission import registry_file_lock
project=Path(sys.argv[1]); relative=sys.argv[2]
target=StoreTarget("events",project/".pf"/relative,relative,"project","stable-project")
context=StorageMigrationContext(project,None,project.parent/"device.yaml",(target,))
try:
    with storage_identity_access(context,target,registry_lock=registry_file_lock,deadline=time.monotonic()+.3) as identity:
        print("identity:"+str(identity))
except SystemExit as error:
    if getattr(error,"registry_lock_reason",None)!="contention_timeout":raise
    print("identity-gate-busy")
"""


def test_adapter_identity_gate_excludes_another_process(fixture_root: Path) -> None:
    storage = StorageHarness(fixture_root / "gate")
    storage.create()
    assert storage.ensure()["status"] == "ready"
    original_pin = (storage.owner / "data/storage-identities.json").read_bytes()
    original_database = storage.target.target.read_bytes()
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        str(root / name) for name in ("src", "tools")
    )

    def child() -> str:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                _ACCESS_CHILD,
                str(storage.project),
                storage.target.target_relative_path,
            ],
            cwd=root,
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()

    with migration.storage_identity_access(
        storage.context,
        storage.target,
        registry_lock=registry_file_lock,
        deadline=time.monotonic() + 2,
    ) as identity:
        assert identity == storage.slot["store_id"]
        assert child() == "identity-gate-busy"
    assert child() == "identity:" + storage.slot["store_id"]
    assert (storage.owner / "data/storage-identities.json").read_bytes() == original_pin
    assert storage.target.target.read_bytes() == original_database


def test_restore_preserves_uuid_without_switching_binding(fixture_root: Path) -> None:
    storage = StorageHarness(fixture_root / "restore")
    storage.create()
    assert storage.ensure()["status"] == "ready"
    pins = storage.owner / "data/storage-identities.json"
    original_pin = pins.read_bytes()
    bundle = fixture_root / "backup"
    restored = storage.target.target.with_name("restored.sqlite3")
    storage.backup.create(storage.target.target, bundle)
    storage.backup.restore(bundle, restored)
    with pytest.raises(MaintenanceError, match="backup_output_exists"):
        storage.backup.restore(bundle, restored)
    restored_target = replace(
        storage.target,
        target=restored,
        target_relative_path=restored.relative_to(storage.owner).as_posix(),
    )
    context = replace(storage.context, targets=(restored_target,))
    with pytest.raises(MaintenanceError, match="storage_pin_missing"):
        with migration.storage_identity_access(
            context, restored_target, registry_lock=registry_file_lock
        ):
            pytest.fail("restore invented a binding")
    assert pins.read_bytes() == original_pin
    connection = sqlite3.connect(restored)
    try:
        assert connection.execute(
            "SELECT store_id,scope,owner_id FROM pf_store_meta"
        ).fetchone() == (storage.slot["store_id"], "project", "stable-project")
    finally:
        connection.close()
    with migration.storage_identity_access(
        storage.context, storage.target, registry_lock=registry_file_lock
    ) as identity:
        assert identity == storage.slot["store_id"]
