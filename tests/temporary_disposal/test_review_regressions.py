"""Real SQL review reproductions and bounded secondary-failure regressions.

W34 originals are pinned in W36 input-pins.json. No product child is launched.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest
from executions.test_lifecycle import isolated_path as isolated_path
from executions.test_lifecycle import sql_cli_fixture as sql_cli_fixture

from processforge_core.agent_entry import migration
from processforge_core.executions.model import ExecutionError
from processforge_core.executions.projection import projected_payload
from processforge_core.maintenance import temporary_disposal as disposal

SqlFixture = tuple[Path, Any, argparse.Namespace, Path]


def stage(resource: disposal.OwnedTemporary) -> None:
    resources = migration._STAGING.get()
    assert resources is not None
    resources.append(resource)


def managed_scope(root: Path) -> None:
    import processforge as core

    from processforge_core.prepared import input as prepared_input

    (root / ".pf/tmp").mkdir()
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    semantic["scope"] = {
        "allowed_files": [".pf/tmp/scratch-owned/**", ".pf/artifacts/report.md"],
        "allowed_read_files": [],
        "forbidden_files": [],
        "forbidden_actions": ["write_product"],
        "allowed_actions": ["read", "write_artifact"],
        "ownership": {
            "writer": True,
            "owner_id": "worker",
            "owned_files": [".pf/tmp/scratch-owned/**"],
        },
    }
    semantic["sources"] = []


@pytest.mark.parametrize("managed", [False, True])
def test_cancelled_never_launched_can_prepare_again(
    sql_cli_fixture: SqlFixture, managed: bool
) -> None:
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    if managed:
        managed_scope(root)
    assert core.command_worker_run_prepare(args) == 0
    ready = repository.load_latest("run", "task")
    assert core.command_worker_run_stop(args) == 0
    stopped = repository.load_latest("run", "task")
    assert stopped.phase == "prepared" and stopped.process is None
    assert stopped.launch_token is None
    assert projected_payload(stopped)["status"] == "cancelled"
    # Cancellation is an atomic SQL fact that excludes both stale and fresh
    # launch reservations. A mere no-PID prepared snapshot is insufficient.
    with pytest.raises(ExecutionError, match="stale_revision"):
        repository.reserve_start(
            ready.key,
            expected_revision=ready.revision,
            generation=ready.generation,
            launch_token="a" * 32,
        )
    with pytest.raises(ExecutionError, match="execution_activity_unknown"):
        repository.reserve_start(
            stopped.key,
            expected_revision=stopped.revision,
            generation=stopped.generation,
            launch_token="b" * 32,
        )
    assert core.command_worker_run_prepare(args) == 0
    assert repository.load_latest("run", "task").key.attempt == 2
    if managed:
        records = list((root / ".pf").rglob("scratch-cleanup.json"))
        assert len(records) == 1
        assert json.loads(records[0].read_text())["result"] == "deleted"
        assert len(list((root / ".pf/tmp/scratch-owned").iterdir())) == 1


@pytest.mark.parametrize("managed", [False, True])
def test_tampered_prepared_launch_preserves_denial_and_scratch_obligation(
    sql_cli_fixture: SqlFixture, managed: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    if managed:
        managed_scope(root)
    assert core.command_worker_run_prepare(args) == 0
    ready = repository.load_latest("run", "task")
    state = projected_payload(ready)
    manifest = root / state["prepared_input"]["path"]
    tampered = manifest.read_bytes() + b" "
    manifest.write_bytes(tampered)
    capsys.readouterr()

    assert core.command_worker_run_start(args) == 1
    assert "prepared_input_checksum_mismatch" in capsys.readouterr().out
    blocked = repository.load_latest("run", "task")
    assert blocked.key == ready.key and blocked.phase == "prepared"
    assert projected_payload(blocked)["status"] == "blocked"
    assert blocked.launch_token is None and blocked.process is None
    assert not (root / ".pf/artifacts/report.md").exists()
    assert core.command_worker_run_start(args) == 1
    assert "explicit worker-run prepare" in capsys.readouterr().out
    assert repository.load_latest("run", "task").key == ready.key

    if managed:
        # Corruption is never authority to release the still-needed allocation.
        scratch = list((root / ".pf/tmp/scratch-owned").iterdir())
        assert len(scratch) == 1
        assert core.command_worker_run_prepare(args) == 1
        assert "temporary_cleanup_needed" in capsys.readouterr().out
        assert repository.load_latest("run", "task").key == ready.key
        assert scratch[0].is_dir()
        assert not manifest.with_name("scratch-release.json").exists()
        assert not manifest.with_name("scratch-cleanup.json").exists()
    else:
        assert core.command_worker_run_prepare(args) == 0
        assert (
            repository.load_latest("run", "task").key.attempt == ready.key.attempt + 1
        )
    assert manifest.read_bytes() == tampered


@pytest.mark.parametrize("actual", ["ready", "blocked", "starting", "stopping"])
def test_cancelled_projection_cannot_prove_uncertain_attempt_unused(
    sql_cli_fixture: SqlFixture, monkeypatch: pytest.MonkeyPatch, actual: str
) -> None:
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    managed_scope(root)
    assert core.command_worker_run_prepare(args) == 0
    ready = repository.load_latest("run", "task")
    stale = dict(
        projected_payload(ready),
        status="cancelled",
        finished_at="2026-10-26T09:00:00+00:00",
    )
    if actual == "blocked":
        repository._update_unlaunched(ready, status="blocked", reason="uncertain")
    elif actual in {"starting", "stopping"}:
        started = repository.reserve_start(
            ready.key,
            expected_revision=ready.revision,
            generation=ready.generation,
            launch_token="a" * 32,
        )
        if actual == "stopping":
            repository.request_stop(
                started.key,
                launch_token=started.launch_token,
                expected_revision=started.revision,
                generation=started.generation,
            )
    monkeypatch.setattr(core, "load_agent_run_state", lambda *args: stale)
    task = core._worker_assignment_service.load(root, "task")
    assert core._finalize_worker_scratch(root, task, trigger="before_retry") is False
    assert len(list((root / ".pf/tmp/scratch-owned").iterdir())) == 1
    assert not list((root / ".pf").rglob("scratch-release.json"))


@pytest.mark.parametrize(
    "point",
    [
        "manifest",
        "workspace",
        "prompt",
        "command",
        "state",
        "committed",
        "projection",
        "event",
    ],
)
def test_preparation_lifetime_transfers_only_with_durable_binding(
    sql_cli_fixture: SqlFixture, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    import processforge as core

    from processforge_core.prepared import input as prepared_input

    root, repository, args, _driver = sql_cli_fixture
    managed_scope(root)
    original_error = PermissionError("publication_denied_" + point)
    write_json = core._core_common_json_io.json_write
    write_once = prepared_input.write_once
    finalize = type(repository)._finalize_prepared
    publish = core._publish_sql_locked
    emit = core._process_event_recorder.emit_process_event
    render = core._worker_assignment_service.render_prompt

    def denied_json(path: Path, value: Any) -> Any:
        if (point == "workspace" and path.name == "workspace-access.json") or (
            point == "command" and path.name == "command.json"
        ):
            raise original_error
        return write_json(path, value)

    def denied_manifest(path: Path, value: Any) -> Any:
        result = write_once(path, value)
        if point == "manifest" and path.name == "prepared-input.json":
            raise original_error
        return result

    def denied_finalize(self: Any, *args: Any, **kwargs: Any) -> Any:
        if point == "state":
            raise original_error
        result = finalize(self, *args, **kwargs)
        if point == "committed":
            raise original_error
        return result

    def denied_publish(*args: Any, **kwargs: Any) -> Any:
        if point == "projection":
            raise original_error
        return publish(*args, **kwargs)

    def denied_event(*args: Any, **kwargs: Any) -> Any:
        if point == "event":
            raise original_error
        return emit(*args, **kwargs)

    def denied_prompt(*args: Any, **kwargs: Any) -> str:
        if point == "prompt":
            raise original_error
        return render(*args, **kwargs)

    with monkeypatch.context() as fault:
        fault.setattr(core._core_common_json_io, "json_write", denied_json)
        fault.setattr(prepared_input, "write_once", denied_manifest)
        fault.setattr(type(repository), "_finalize_prepared", denied_finalize)
        fault.setattr(core, "_publish_sql_locked", denied_publish)
        fault.setattr(core._process_event_recorder, "emit_process_event", denied_event)
        fault.setattr(core._worker_assignment_service, "render_prompt", denied_prompt)
        with pytest.raises((PermissionError, SystemExit)) as caught:
            core.command_worker_run_prepare(args)
    assert caught.value is original_error or caught.value.__cause__ is original_error
    record = repository.load_latest("run", "task")
    bound = point in {"committed", "projection", "event"}
    assert bool(projected_payload(record).get("prepared_input")) is bound
    remaining = list((root / ".pf/tmp/scratch-owned").iterdir())
    assert len(remaining) == int(bound)
    if bound:
        assert not list((root / ".pf").rglob("scratch-cleanup.json"))
        assert core.command_worker_run_stop(args) == 0
    else:
        receipts = list((root / ".pf").rglob("scratch-cleanup.json"))
        assert len(receipts) == 1
        assert json.loads(receipts[0].read_text())["result"] == "deleted"
    # The next large attempt is permitted only after the first resource is gone.
    assert core.command_worker_run_prepare(args) == 0
    assert all(not path.exists() for path in remaining)


@pytest.mark.parametrize(
    "point", ["release", "dispose", "mkdir", "encode", "replace", "residual"]
)
@pytest.mark.parametrize("primary", [True, False])
def test_entry_finalization_preserves_exception_or_incomplete(
    isolated_path: Path, monkeypatch: pytest.MonkeyPatch, point: str, primary: bool
) -> None:
    from processforge_core import diagnostics

    resource = disposal.create_owned_directory(isolated_path)
    journal = isolated_path / "required-recovery.json"
    journal.write_text("required journal proof", encoding="utf8")
    original = RuntimeError("primary_migration_failure")
    result = {
        "action": "incomplete",
        "transaction": "review-transaction",
        "reason": "staging_changed",
        "remediation": "use journal",
    }
    captured: list[dict[str, Any]] = []

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("cleanup_receipt_directory_denied")

    def diagnostic(*args: Any, **kwargs: Any) -> None:
        captured.append({**kwargs, "context": args[2]})

    if point in {"release", "dispose"}:
        monkeypatch.setattr(disposal, point + "_owned", denied)
    elif point == "mkdir":
        monkeypatch.setattr(migration, "_directory", denied)
    elif point == "encode":
        monkeypatch.setattr(migration, "encoded", denied)
    elif point == "replace":
        monkeypatch.setattr(Path, "replace", denied)
    else:
        monkeypatch.setattr(
            disposal,
            "dispose_owned",
            lambda value: disposal.CleanupReceipt(
                value.resource_id, "cleanup_pending", error_code=13
            ),
        )
    monkeypatch.setattr(diagnostics, "emit", diagnostic)
    if primary:
        with pytest.raises(RuntimeError) as caught:
            with migration._transaction_temporaries(isolated_path):
                stage(resource)
                raise original
        assert caught.value is original
        assert "primary_migration_failure" == str(original)
        assert any("temporary_cleanup_receipt:" in note for note in original.__notes__)
    else:
        monkeypatch.setattr(migration, "root_path", lambda path: path)

        def incomplete(*args: Any, **kwargs: Any) -> dict[str, Any]:
            stage(resource)
            return result

        monkeypatch.setattr(migration, "_apply_placement_owned", incomplete)
        actual = migration._apply_placement(
            isolated_path,
            {},
            apply=True,
            targets=migration.TARGETS,
            planner=None,
            source_guard=None,
        )
        assert actual is result
    assert captured and captured[0]["component"] == "agent_entry"
    assert captured[0]["context"]["resource_id"] == resource.resource_id
    assert journal.read_text(encoding="utf8") == "required journal proof"


@pytest.mark.parametrize("committed", [False, True])
def test_ambiguous_publication_readback_preserves_resource_and_primary(
    sql_cli_fixture: SqlFixture, monkeypatch: pytest.MonkeyPatch, committed: bool
) -> None:
    import processforge as core

    root, repository, args, _driver = sql_cli_fixture
    managed_scope(root)
    original = PermissionError("ambiguous_binding")
    finalize = type(repository)._finalize_prepared

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise OSError("readback_denied")

    def uncertain(self: Any, *args: Any, **kwargs: Any) -> Any:
        if committed:
            finalize(self, *args, **kwargs)
        monkeypatch.setattr(core, "load_agent_run_state", denied)
        raise original

    monkeypatch.setattr(type(repository), "_finalize_prepared", uncertain)
    with pytest.raises(PermissionError) as caught:
        core.command_worker_run_prepare(args)
    assert caught.value is original
    assert "scratch_publication_unknown:OSError" in original.__notes__
    assert len(list((root / ".pf/tmp/scratch-owned").iterdir())) == 1
    assert not list((root / ".pf").rglob("scratch-cleanup.json"))


@pytest.mark.parametrize("primary", [False, True])
def test_entry_secondary_diagnostic_failure_cannot_mask_result(
    isolated_path: Path, monkeypatch: pytest.MonkeyPatch, primary: bool
) -> None:
    from processforge_core import diagnostics

    class PrimaryError(RuntimeError):
        def add_note(self, note: str) -> None:
            raise ValueError("note_sink_failed")

    original = PrimaryError("original")
    resource = disposal.create_owned_directory(isolated_path)

    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("secondary_failed")

    monkeypatch.setattr(disposal, "dispose_owned", denied)
    monkeypatch.setattr(diagnostics, "emit", denied)
    if primary:
        with pytest.raises(PrimaryError) as caught:
            with migration._transaction_temporaries(isolated_path):
                stage(resource)
                raise original
        assert caught.value is original
    else:
        with migration._transaction_temporaries(isolated_path) as outcome:
            stage(resource)
            outcome.update(action="incomplete", transaction="preserved")
        assert outcome == {"action": "incomplete", "transaction": "preserved"}


@pytest.mark.parametrize(
    "mode",
    [
        "recovered",
        "retained",
        "unknown",
        "committed",
        "cas_race",
        "cleanup_retry",
        "changed_record",
        "missing_manifest",
    ],
)
def test_ambiguous_publication_reentry_resolves_before_allocation(
    sql_cli_fixture: SqlFixture, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    import processforge as core

    from processforge_core.prepared import command as scratch

    root, repository, args, _driver = sql_cli_fixture
    managed_scope(root)
    primary = PermissionError("publication_ambiguous")
    finalize = type(repository)._finalize_prepared

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        raise OSError("readback_unknown")

    with monkeypatch.context() as fault:

        def uncertain(self: Any, *args: Any, **kwargs: Any) -> Any:
            if mode == "committed":
                finalize(self, *args, **kwargs)
            fault.setattr(core, "load_agent_run_state", unreadable)
            raise primary

        fault.setattr(type(repository), "_finalize_prepared", uncertain)
        with pytest.raises(PermissionError) as caught:
            core.command_worker_run_prepare(args)
        assert caught.value is primary
    # The in-memory guard has ended: only durable attempt records remain.
    assert scratch._PREPARATION.get() is None
    first = repository.load_latest("run", "task")
    previous = set((root / ".pf/tmp/scratch-owned").iterdir())
    assert len(previous) == 1
    task = core._worker_assignment_service.load(root, "task")
    attempt = root / ".pf/runtime/agent-runs/run/task/attempts/1"
    if mode != "committed":
        with pytest.raises(SystemExit, match="temporary_cleanup_needed"):
            core.prepare_worker_run(root, "task", str(_driver), None)
        assert repository.load_latest("run", "task").key == first.key
    if mode == "retained":
        from processforge_core.common.yaml_io import write_yaml_file

        write_yaml_file(
            root / "device.yaml",
            {"runtime": {"temporary_files": {"retain_unused": True}}},
        )
    if mode == "changed_record":
        record_path = attempt / "scratch-resource.json"
        record_path.write_text("{}", encoding="utf8")
    if mode == "missing_manifest":
        (attempt / "prepared-input.json").unlink()
    if mode == "committed":
        assert core._finalize_worker_scratch(root, task, trigger="before_retry")
        assert all(path.exists() for path in previous)
        assert not (attempt / "scratch-cleanup.json").exists()
        return
    if mode in {"unknown", "cas_race"}:
        with monkeypatch.context() as fault:
            if mode == "unknown":
                fault.setattr(type(repository), "load", unreadable)
            else:

                def concurrent(self: Any, *args: Any, **kwargs: Any) -> Any:
                    raise ExecutionError("stale_revision")

                fault.setattr(type(repository), "_update_unlaunched", concurrent)
            if mode == "unknown":
                assert not core._finalize_worker_scratch(
                    root, task, trigger="before_retry"
                )
            else:
                assert core.command_worker_run_prepare(args) == 1
        assert repository.load_latest("run", "task").key == first.key
        assert all(path.exists() for path in previous)
        return
    if mode in {"changed_record", "missing_manifest"}:
        assert core.command_worker_run_prepare(args) == 1
        assert repository.load_latest("run", "task").key == first.key
        assert all(path.exists() for path in previous)
        return
    if mode == "cleanup_retry":
        with monkeypatch.context() as fault:
            fault.setattr(scratch, "dispose_owned", unreadable)
            assert core.command_worker_run_prepare(args) == 1
        cancelled = repository.load_latest("run", "task")
        assert cancelled.key == first.key
        assert projected_payload(cancelled)["status"] == "cancelled"
        with pytest.raises(ExecutionError):
            repository._finalize_prepared(
                first, json.dumps({**projected_payload(first), "status": "ready"})
            )
    assert core.command_worker_run_prepare(args) == 0
    assert repository.load_latest("run", "task").key.attempt == 2
    receipt = json.loads((attempt / "scratch-cleanup.json").read_text())
    assert receipt["result"] == (
        "retained_by_configuration" if mode == "retained" else "deleted"
    )
    assert all(path.exists() == (mode == "retained") for path in previous)
    assert len(list((root / ".pf/tmp/scratch-owned").iterdir())) == (
        2 if mode == "retained" else 1
    )


@pytest.mark.parametrize("retain", [False, True])
def test_committed_ambiguous_retry_preserves_binding_for_start(
    sql_cli_fixture: SqlFixture, monkeypatch: pytest.MonkeyPatch, retain: bool
) -> None:
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file

    root, repository, args, driver = sql_cli_fixture
    managed_scope(root)
    if retain:
        write_yaml_file(
            root / "device.yaml",
            {"runtime": {"temporary_files": {"retain_unused": True}}},
        )
    finalize = type(repository)._finalize_prepared
    primary = PermissionError("committed_publication_ambiguous")

    def unreadable(*args: Any, **kwargs: Any) -> Any:
        raise OSError("readback_unknown")

    with monkeypatch.context() as fault:

        def uncertain(self: Any, *args: Any, **kwargs: Any) -> Any:
            finalize(self, *args, **kwargs)
            fault.setattr(core, "load_agent_run_state", unreadable)
            raise primary

        fault.setattr(type(repository), "_finalize_prepared", uncertain)
        with pytest.raises(PermissionError) as caught:
            core.command_worker_run_prepare(args)
        assert caught.value is primary
    first = repository.load_latest("run", "task")
    assert projected_payload(first)["status"] == "ready"
    previous = set((root / ".pf/tmp/scratch-owned").iterdir())
    assert len(previous) == 1
    assert core.command_worker_run_prepare(args) == 1
    with pytest.raises(SystemExit, match="temporary_cleanup_needed"):
        core.prepare_worker_run(root, "task", str(driver), None)
    assert repository.load_latest("run", "task") == first
    assert set((root / ".pf/tmp/scratch-owned").iterdir()) == previous
    assert not list((root / ".pf").rglob("scratch-release.json"))
    assert not list((root / ".pf").rglob("scratch-cleanup.json"))
    # Start consumes the already committed binding; retention is not admission.
    assert core.command_worker_run_start(args) == 0
    completed = repository.load_latest("run", "task")
    assert completed.key == first.key and completed.outcome == "completed"
    assert (root / ".pf/artifacts/report.md").read_text() == "# fixture result"


@pytest.mark.parametrize("phase", ["starting", "stopping"])
def test_bound_launch_reservation_cannot_be_replaced_or_disposed(
    sql_cli_fixture: SqlFixture, phase: str
) -> None:
    import processforge as core

    root, repository, args, driver = sql_cli_fixture
    managed_scope(root)
    assert core.command_worker_run_prepare(args) == 0
    ready = repository.load_latest("run", "task")
    starting = repository.reserve_start(
        ready.key,
        expected_revision=ready.revision,
        generation=ready.generation,
        launch_token="a" * 32,
    )
    if phase == "stopping":
        repository.request_stop(
            starting.key,
            launch_token=starting.launch_token,
            expected_revision=starting.revision,
            generation=starting.generation,
        )
    bound = repository.load_latest("run", "task")
    with pytest.raises(SystemExit, match="temporary_cleanup_needed"):
        core.prepare_worker_run(root, "task", str(driver), None)
    with pytest.raises(ExecutionError, match="stale_revision"):
        repository.reserve_start(
            ready.key,
            expected_revision=ready.revision,
            generation=ready.generation,
            launch_token="b" * 32,
        )
    assert repository.load_latest("run", "task") == bound
    assert len(list((root / ".pf/tmp/scratch-owned").iterdir())) == 1
    assert not list((root / ".pf").rglob("scratch-release.json"))


@pytest.mark.parametrize("private", [False, True])
def test_owned_creation_security_and_default_cleanup(
    isolated_path: Path, private: bool
) -> None:
    import os

    resource = disposal.create_owned_directory(isolated_path, private=private)
    try:
        info = resource.path.lstat()
        assert resource.identity == (info.st_dev, info.st_ino)
        assert resource.boundary == isolated_path.absolute()
        if private and os.name == "nt":
            from processforge_core.egress.windows import verify_private

            verify_private(resource.path, directory=True)
        elif os.name != "nt":
            assert info.st_mode & 0o077 == 0
        (resource.path / "payload").write_bytes(b"owned staging")
    finally:
        receipt = disposal.dispose_owned(disposal.release_owned(resource))
    assert receipt.result == "deleted" and receipt.complete
    assert receipt.deleted_files == 1 and receipt.deleted_bytes == 13
    assert not resource.path.exists()


@pytest.mark.parametrize(
    ("private", "existing_private"), [(False, False), (True, False), (True, True)]
)
def test_owned_creation_collision_never_adopts_or_changes_existing(
    isolated_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    private: bool,
    existing_private: bool,
) -> None:
    from types import SimpleNamespace

    fixed = SimpleNamespace(hex="c" * 32)
    monkeypatch.setattr(disposal.uuid, "uuid4", lambda: fixed)
    resource = disposal.create_owned_directory(isolated_path, private=existing_private)
    payload = resource.path / "foreign.txt"
    payload.write_bytes(b"preserve")
    before = migration.security(resource.path)
    try:
        with pytest.raises(FileExistsError):
            disposal.create_owned_directory(isolated_path, private=private)
        assert migration.security(resource.path) == before
        assert payload.read_bytes() == b"preserve"
        assert resource.path.lstat().st_ino == resource.identity[1]
    finally:
        receipt = disposal.dispose_owned(disposal.release_owned(resource))
    assert receipt.result == "deleted"


def test_private_creation_failure_preserves_error_and_allocates_nothing(
    isolated_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    if os.name != "nt":
        pytest.skip("Windows private DACL creation")
    from processforge_core.egress import windows
    from processforge_core.egress.contracts import EgressError

    original = EgressError("private_acl_unavailable")

    def denied() -> Any:
        raise original

    with monkeypatch.context() as fault:
        fault.setattr(windows, "current_sid", denied)
        with pytest.raises(EgressError) as caught:
            disposal.create_owned_directory(isolated_path, private=True)
        assert caught.value is original
        # Default callers must not enter the private ACL mechanism.
        resource = disposal.create_owned_directory(isolated_path)
    assert disposal.dispose_owned(disposal.release_owned(resource)).result == "deleted"
    assert list(isolated_path.iterdir()) == []


def test_entry_private_staging_failure_keeps_owned_cleanup(
    isolated_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (isolated_path / ".pf").mkdir()
    with migration.entry_lock(isolated_path):
        pass
    directory = migration._directory
    created: list[Path] = []

    def rejected(root: Path, name: str, *, private: bool = False) -> Path:
        if "pf-scratch-" in name:
            path = root / name
            created.append(path)
            assert private and path.is_dir()
            raise migration.EntryError("private_acl_unavailable")
        return directory(root, name, private=private)

    with monkeypatch.context() as fault:
        fault.setattr(migration, "_directory", rejected)
        with migration._transaction_temporaries(isolated_path) as outcome:
            with pytest.raises(migration.EntryError, match="private_acl_unavailable"):
                migration._stage(isolated_path, "owned", b"must not be written")
            resources = migration._STAGING.get()
            assert resources is not None and len(resources) == 1
            assert list(resources[0].path.iterdir()) == []
            outcome.update(action="incomplete")
    assert len(created) == 1 and not created[0].exists()
    receipts = list((isolated_path / migration.JOURNALS / "cleanup").glob("*.json"))
    assert len(receipts) == 1
    assert json.loads(receipts[0].read_text())["result"] == "deleted"
