"""Maintained W69s2 semantic matrix; Q65 F66-02 equivalent reconstruction.

Faults touch actual publication IO. Assertions inspect stored bytes, immutable
references and allocation numbers, rather than accepting mock call counts.
"""

from __future__ import annotations

import itertools
import os
from pathlib import Path
from typing import Any

import processforge as core
import pytest

from processforge_core.common.yaml_io import write_yaml_file
from processforge_core.executions.model import ExecutionError
from processforge_core.prepared import input as prepared_input
from processforge_core.prepared import retry_publication as rp
from tests.worker_retry_state.test_retry import isolated_path as isolated_path
from tests.worker_retry_state.test_retry import legacy as legacy
from tests.worker_retry_state.test_retry import sql_cli_fixture as sql_cli_fixture


def capture(root: Path, paths: dict[str, Path]) -> dict[str, bytes | None]:
    result = {key: rp.read_raw(root, paths[key]) for key in rp.OBSERVATIONS}
    result["workspace_access"] = rp.read_raw(root, paths["workspace_access"])
    result["prompt"] = rp.read_raw(
        root, core._work_paths.worker_prompt(root, "run", "task")
    )
    return result


def pending(legacy: Any, monkeypatch: pytest.MonkeyPatch) -> rp.Publication:
    root, args, paths = legacy

    def fail(*a: Any, **k: Any) -> None:
        raise OSError("after intent before projections")

    with monkeypatch.context() as patch:
        patch.setattr(rp, "apply_publication", fail)
        with pytest.raises(OSError, match="after intent"):
            core.command_worker_run_prepare(args)
    found = core._retry_pending(root, "run", "task")
    assert found is not None and found.intent["identity"]["attempt"] == 2
    return found


@pytest.mark.parametrize("slot", ["workspace_access", "prompt", "status", "command"])
@pytest.mark.parametrize("after", [False, True])
def test_public_prepare_same_n_after_each_replace(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    slot: str,
    after: bool,
) -> None:
    root, args, paths = legacy
    paths["workspace_access"].write_bytes(b'{"old":true}')
    originals = capture(root, paths)
    target = (
        core._work_paths.worker_prompt(root, "run", "task")
        if slot == "prompt"
        else paths[slot]
    )
    real_replace = os.replace

    def replace(source: Any, destination: Any) -> None:
        if Path(destination) == target:
            if after:
                real_replace(source, destination)
            raise OSError("projection interruption")
        real_replace(source, destination)

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", replace)
        with pytest.raises(OSError, match="projection interruption"):
            core.command_worker_run_prepare(args)
    publication = core._retry_pending(root, "run", "task")
    assert publication is not None
    reference = publication.intent["new_reference"]
    if slot == "status" and after:
        assert core.json_read(paths["status"])["attempt"] == 2
        assert core.json_read(paths["command"])["attempt"] == "1"
    assert core.command_worker_run_prepare(args) == 0
    assert core.load_agent_run_state(root, "run", "task")["prepared_input"] == reference
    assert sorted(p.name for p in publication.directory.parent.iterdir()) == ["1", "2"]
    final = capture(root, paths)
    assert all(final[key] == publication.new[key] for key in rp.PROJECTIONS)
    assert publication.old == originals
    assert (publication.directory / rp.APPLIED).read_bytes() == publication.receipt


@pytest.mark.parametrize("after", [False, True])
@pytest.mark.parametrize("name", [rp.INTENT, rp.APPLIED])
def test_intent_applied_link_boundaries(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    after: bool,
    name: str,
) -> None:
    root, args, paths = legacy
    before = capture(root, paths)
    real_link = os.link

    def link(source: Any, target: Any) -> None:
        if Path(target).name == name:
            if after:
                real_link(source, target)
            raise OSError("journal link interruption")
        real_link(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(OSError, match="journal link interruption"):
            core.command_worker_run_prepare(args)
    publication = core._retry_pending(root, "run", "task")
    if name == rp.INTENT and not after:
        assert publication is None and capture(root, paths) == before
    elif name == rp.APPLIED and after:
        assert publication is None  # Exact committed receipt is historical.
        assert core.load_agent_run_state(root, "run", "task")["attempt"] == 2
    else:
        assert publication is not None
    assert core.command_worker_run_prepare(args) == 0
    attempt = core.load_agent_run_state(root, "run", "task")["attempt"]
    assert attempt == (2 if publication is not None else 3)


@pytest.mark.parametrize("slot", ["status", "command"])
def test_partial_mutable_staging_never_becomes_current(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    slot: str,
) -> None:
    root, args, paths = legacy
    real_full = rp._full_write
    before = paths[slot].read_bytes()

    def write(stream: Any, raw: bytes) -> None:
        # Sidecar writes precede intent; interrupt only the mutable stage.
        if core._retry_pending(root, "run", "task") is not None and raw.startswith(
            b"{"
        ):
            value = rp.strict_json(raw)
            if value.get("attempt") == (2 if slot == "status" else "2"):
                stream.write(raw[:17])
                raise OSError("mutable 17 bytes")
        real_full(stream, raw)

    with monkeypatch.context() as patch:
        patch.setattr(rp, "_full_write", write)
        with pytest.raises(OSError, match="mutable 17 bytes"):
            core.command_worker_run_prepare(args)
    assert paths[slot].read_bytes() == before
    assert core.command_worker_run_prepare(args) == 0
    assert core.json_read(paths["status"])["attempt"] == 2


def test_full_prefix_matrix(tmp_path: Path) -> None:
    project = tmp_path
    directory = project / ".pf/runtime/agent-runs/run/task/attempts/2"
    directory.mkdir(parents=True)
    paths = {key: directory.parent.parent / key for key in rp.SLOTS}
    old: dict[str, bytes | None] = {key: (key + "-old").encode() for key in rp.SLOTS}
    new = {key: (key + "-new").encode() for key in rp.PROJECTIONS}

    def reference(n: int) -> dict[str, str]:
        return {
            "path": (directory.parent / str(n) / "prepared-input.json")
            .relative_to(project)
            .as_posix(),
            "checksum": "sha256:" + "a" * 64,
        }

    publication = rp.create_publication(
        project,
        directory,
        {
            "project_id": "p",
            "run_id": "run",
            "assignment_id": "task",
            "context_id": "c",
            "attempt": 2,
        },
        reference(1),
        1,
        reference(2),
        {},
        {},
        old,
        new,
    )
    rp._aliases(project, publication, publish=True)
    reachable = {tuple([1] * n + [0] * (6 - n)) for n in range(7)}
    for bits in itertools.product((0, 1), repeat=6):
        vector = dict(old)
        for key, changed in zip(rp.ORDER, bits):
            if changed:
                vector[key] = new.get(key)
        for key, raw in vector.items():
            if raw is None:
                paths[key].unlink(missing_ok=True)
            else:
                paths[key].write_bytes(raw)
        before = {key: rp.read_raw(project, path) for key, path in paths.items()}
        if bits in reachable:
            assert rp.prefix(project, paths, publication) == sum(bits)
        else:
            with pytest.raises(ExecutionError, match="execution_identity_conflict"):
                rp.apply_publication(project, paths, publication)
            assert {
                key: rp.read_raw(project, path) for key, path in paths.items()
            } == before


@pytest.mark.parametrize(
    "damage",
    [
        "sidecar",
        "duplicate",
        "foreign-reference",
        "foreign-identity",
        "new-launch",
        "two-intents",
        "bad-receipt",
    ],
)
def test_damaged_pending_refuses_without_mutation(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    root, args, paths = legacy
    publication = pending(legacy, monkeypatch)
    if damage == "sidecar":
        (publication.directory / rp.SIDECARS["command"]).write_bytes(b"different")
    elif damage == "duplicate":
        (publication.directory / rp.INTENT).write_bytes(
            publication.raw.replace(
                b'"schema_version": 2', b'"schema_version": 2, "schema_version": 2'
            )
        )
    elif damage == "new-launch":
        (publication.directory / "native-tree.json").write_bytes(b"{}")
    elif damage == "bad-receipt":
        (publication.directory / rp.APPLIED).write_bytes(b"{}")
    else:
        intent = dict(publication.intent)
        if damage == "foreign-reference":
            intent["new_reference"] = {
                "path": ".pf/foreign/prepared-input.json",
                "checksum": intent["new_reference"]["checksum"],
            }
        elif damage == "foreign-identity":
            intent["identity"] = {**intent["identity"], "context_id": "foreign"}
        elif damage == "two-intents":
            # A second complete syntactic journal with its own reference is still
            # ambiguous before semantic/authenticity checks can choose either.
            other = publication.directory.with_name("3")
            other.mkdir()
            for file in publication.directory.iterdir():
                if file.is_file():
                    (other / file.name).write_bytes(file.read_bytes())
            intent["identity"] = {**intent["identity"], "attempt": 3}
            intent["new_reference"] = {
                **intent["new_reference"],
                "path": intent["new_reference"]["path"].replace("/2/", "/3/"),
            }
            intent.pop("operation")
            intent["operation"] = prepared_input.digest(prepared_input.encoded(intent))
            (other / rp.INTENT).write_bytes(prepared_input.encoded(intent))
        if damage != "two-intents":
            intent.pop("operation")
            intent["operation"] = prepared_input.digest(prepared_input.encoded(intent))
            (publication.directory / rp.INTENT).write_bytes(
                prepared_input.encoded(intent)
            )
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before
    assert not (publication.directory.parent / "4").exists()


@pytest.mark.parametrize(
    "operation", ["start", "stop", "status", "observe", "write", "cleanup"]
)
def test_pending_readers_never_mutate_or_launch(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    root, args, paths = legacy
    pending(legacy, monkeypatch)
    before = capture(root, paths)
    task = core._worker_assignment_service.load(root, "task")
    state = core.load_agent_run_state(root, "run", "task")
    driver = core._runtime_driver_selection_service.for_task(root, task, args.driver)
    calls = {
        "start": lambda: core.command_worker_run_start(args),
        "stop": lambda: core.command_worker_run_stop(args),
        "status": lambda: core.command_worker_run_status(args),
        "observe": lambda: core.observe_worker_run(root, task, driver, state),
        "write": lambda: core.write_agent_run_state(root, task, driver, "blocked"),
        "cleanup": lambda: core._finalize_worker_scratch(
            root, task, trigger="before_retry"
        ),
    }
    if operation in {"start", "stop", "status"}:
        assert calls[operation]() == 1
    else:
        with pytest.raises(ExecutionError, match="execution_activity_unknown"):
            calls[operation]()
    assert capture(root, paths) == before
    assert not (root / "target-count").exists()


@pytest.mark.parametrize("priority", ["cancel", "terminal"])
def test_cancellation_terminal_priority(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, priority: str
) -> None:
    root, args, paths = legacy
    publication = pending(legacy, monkeypatch)
    if priority == "cancel":
        path = root / ".pf/runs/run/cancellation-test.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pending: true\n")
    else:
        monkeypatch.setattr(
            core._worker_observation_inputs,
            "worker_run_work_is_terminal",
            lambda *a: True,
        )
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before
    assert not (publication.directory / rp.APPLIED).exists()


@pytest.mark.parametrize(
    "drift", ["driver", "options", "configuration", "semantic", "assignment", "capsule"]
)
def test_current_authenticity_and_request_drift(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    root, args, paths = legacy
    pending(legacy, monkeypatch)
    if drift == "driver":
        driver = core.load_yaml_document(Path(args.driver))
        driver["command"]["args"] = ["-c", "raise SystemExit(99)"]
        write_yaml_file(Path(args.driver), driver)
    elif drift == "options":
        args.executable = "other-executable"
    elif drift == "configuration":
        path = root / "device.yaml"
        write_yaml_file(path, {"runtime": {"temporary_files": {"mode": "off"}}})
    elif drift == "semantic":
        original = prepared_input.semantic_input
        monkeypatch.setattr(
            prepared_input,
            "semantic_input",
            lambda *a, **k: {**original(*a, **k), "parameters": {"drift": True}},
        )
    else:
        path = (
            core._work_paths.assignment_document(root, "task")
            if drift == "assignment"
            else core.assignment_capsule_path(root, "task")
        )
        with path.open("a", encoding="utf8") as stream:
            stream.write("\n# byte drift\n")
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before


def test_applied_history_allows_start_then_retry(legacy: Any) -> None:
    root, args, paths = legacy
    assert core.command_worker_run_prepare(args) == 0
    history = (paths["root"] / "attempts/2" / rp.APPLIED).read_bytes()
    assert core.command_worker_run_start(args) == 1
    assert core.command_worker_run_prepare(args) == 0
    assert core.load_agent_run_state(root, "run", "task")["attempt"] == 3
    assert (paths["root"] / "attempts/2" / rp.APPLIED).read_bytes() == history


@pytest.mark.parametrize(
    "damage", ["missing", "replaced", "released", "cleaned", "record"]
)
def test_pending_scratch_exact_binding(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    root, args, paths = legacy
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    namespace = ".pf/tmp/test-retry"
    (root / ".pf/tmp").mkdir(parents=True, exist_ok=True)
    semantic["scope"] = {
        "allowed_actions": ["write_product"],
        "allowed_files": [namespace + "/**"],
        "ownership": {
            "writer": True,
            "owner_id": "test-retry",
            "owned_files": [namespace + "/**"],
        },
    }
    publication = pending(legacy, monkeypatch)
    document = rp.strict_json(
        (publication.directory / "prepared-input.json").read_bytes()
    )
    marker = document["managed_scratch"]
    target = root / marker["path"]
    assert target.is_dir()
    # The publication exception must have disarmed in-memory abort cleanup.
    assert not (publication.directory / "scratch-preparation-failure.json").exists()
    if damage == "missing":
        target.rmdir()
    elif damage == "replaced":
        target.rename(target.with_name("saved-original"))
        target.mkdir()
    elif damage in {"released", "cleaned"}:
        (
            publication.directory
            / (
                "scratch-release.json"
                if damage == "released"
                else "scratch-cleanup.json"
            )
        ).write_bytes(b"{}")
    else:
        (root / marker["record"]["path"]).write_bytes(b"{}")
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before
    assert target.exists() is (damage != "missing")


@pytest.mark.parametrize("slot", ["process", "exit"])
@pytest.mark.parametrize("after", [False, True])
def test_real_native_retirement_unlink_replays_same_attempt(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    slot: str,
    after: bool,
) -> None:
    root, args, paths = legacy
    # Real bounded failing child establishes the old ownership and exit evidence.
    assert core.command_worker_run_start(args) == 1
    originals = capture(root, paths)
    real_unlink = Path.unlink

    def unlink(path: Path, *a: Any, **k: Any) -> None:
        if path == paths[slot]:
            if after:
                real_unlink(path, *a, **k)
            raise OSError("unlink interruption")
        real_unlink(path, *a, **k)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", unlink)
        with pytest.raises(OSError, match="unlink interruption"):
            core.command_worker_run_prepare(args)
    publication = core._retry_pending(root, "run", "task")
    assert publication is not None
    assert publication.old == originals
    assert core.command_worker_run_prepare(args) == 0
    assert core.json_read(paths["status"])["attempt"] == 2
    assert not paths["process"].exists() and not paths["exit"].exists()
    assert (root / "target-count").read_bytes() == b"x"


@pytest.mark.parametrize("name", list(rp.SIDECARS.values()))
@pytest.mark.parametrize("after", [False, True])
def test_sidecar_failure_has_no_replay_authority(
    legacy: Any,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    after: bool,
) -> None:
    root, args, paths = legacy
    before = capture(root, paths)
    real_link = os.link

    def link(source: Any, target: Any) -> None:
        if Path(target).name == name:
            if after:
                real_link(source, target)
            raise OSError("sidecar interruption")
        real_link(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(OSError, match="sidecar interruption"):
            core.command_worker_run_prepare(args)
    assert capture(root, paths) == before
    assert core._retry_pending(root, "run", "task") is None
    assert core.command_worker_run_prepare(args) == 0
    # Existing allocator skips an uncommitted directory; it is never reused.
    assert core.json_read(paths["status"])["attempt"] == 3


def test_direct_internal_prepare_uses_serialized_recovery(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    pending(legacy, monkeypatch)
    core.prepare_worker_run(root, "task", args.driver)
    assert core.json_read(paths["status"])["attempt"] == 2


def test_ambiguous_intent_link_retains_scratch(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    namespace = ".pf/tmp/test-retry"
    (root / ".pf/tmp").mkdir(parents=True, exist_ok=True)
    semantic["scope"] = {
        "allowed_actions": ["write_product"],
        "allowed_files": [namespace + "/**"],
        "ownership": {
            "writer": True,
            "owner_id": "test-retry",
            "owned_files": [namespace + "/**"],
        },
    }
    real_link, real_read = os.link, rp.read_raw
    committed = False

    def link(source: Any, target: Any) -> None:
        nonlocal committed
        real_link(source, target)
        if Path(target).name == rp.INTENT:
            committed = True
            raise OSError("ambiguous committed intent")

    def read(project: Path, path: Path, maximum: int | None = None) -> bytes | None:
        if committed and path.name == rp.INTENT:
            raise OSError("ambiguous readback")
        return real_read(project, path, maximum)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        patch.setattr(rp, "read_raw", read)
        with pytest.raises(OSError, match="ambiguous committed intent"):
            core.command_worker_run_prepare(args)
    publication = core._retry_pending(root, "run", "task")
    assert publication is not None
    document = rp.strict_json(
        (publication.directory / "prepared-input.json").read_bytes()
    )
    assert (root / document["managed_scratch"]["path"]).is_dir()
    assert not (publication.directory / "scratch-preparation-failure.json").exists()
    assert core.command_worker_run_prepare(args) == 0
    assert core.json_read(paths["status"])["attempt"] == 2


@pytest.mark.parametrize("after_intent", [False, True])
def test_scratch_lifetime_transfer_at_intent(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, after_intent: bool
) -> None:
    root, args, paths = legacy
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    namespace = ".pf/tmp/test-retry"
    (root / ".pf/tmp").mkdir(parents=True, exist_ok=True)
    semantic["scope"] = {
        "allowed_actions": ["write_product"],
        "allowed_files": [namespace + "/**"],
        "ownership": {
            "writer": True,
            "owner_id": "test-retry",
            "owned_files": [namespace + "/**"],
        },
    }
    real_link = os.link

    def link(source: Any, target: Any) -> None:
        if Path(target).name == rp.INTENT:
            if after_intent:
                real_link(source, target)
            raise OSError("scratch intent boundary")
        real_link(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", link)
        with pytest.raises(OSError, match="scratch intent boundary"):
            core.command_worker_run_prepare(args)
    directory = paths["root"] / "attempts/2"
    document = rp.strict_json((directory / "prepared-input.json").read_bytes())
    target = root / document["managed_scratch"]["path"]
    assert target.exists() == after_intent
    assert (directory / "scratch-preparation-failure.json").exists() is not after_intent
    assert (core._retry_pending(root, "run", "task") is not None) == after_intent
    if after_intent:
        assert core.command_worker_run_prepare(args) == 0
        assert core.json_read(paths["status"])["attempt"] == 2


@pytest.mark.parametrize("name", ["process.json", "exit.json"])
def test_new_attempt_launch_facts_refuse_replay(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    root, args, paths = legacy
    publication = pending(legacy, monkeypatch)
    path = publication.directory / name
    path.write_bytes(b"{}")
    before = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 1
    assert path.read_bytes() == b"{}" and capture(root, paths) == before


@pytest.mark.parametrize("probe", [False, None])
def test_pending_rechecks_old_native_quiescence(
    legacy: Any, monkeypatch: pytest.MonkeyPatch, probe: bool | None
) -> None:
    root, args, paths = legacy
    assert core.command_worker_run_start(args) == 1
    publication = pending(legacy, monkeypatch)
    before = capture(root, paths)
    monkeypatch.setattr(core, "_legacy_tree_probe", lambda *a, **k: probe)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before
    assert not (publication.directory / rp.APPLIED).exists()


def test_real_work_kind_identity_same_n(
    sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from processforge_core.executions.composition import ExecutionStorage

    root, _, args, _ = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    semantic = prepared_input.semantic_input(root, {}, {}, core)
    semantic["identity"]["kind"] = "work"
    capsule_path = core.assignment_capsule_path(root, "task")
    capsule = core.load_yaml_document(capsule_path)
    capsule["execution_contract"]["identity"]["kind"] = "work"
    write_yaml_file(capsule_path, capsule)
    assert core.command_worker_run_prepare(args) == 0
    publication = pending(
        (root, args, core._work_paths.worker_run(root, "run", "task")), monkeypatch
    )
    assert core.command_worker_run_prepare(args) == 0
    document = rp.strict_json(
        (publication.directory / "prepared-input.json").read_bytes()
    )
    assert (
        document["identity"]["kind"] == "work" and document["identity"]["attempt"] == 2
    )


def test_revoked_current_access_precedes_effects(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    pending(legacy, monkeypatch)
    before = capture(root, paths)

    def denied(*a: Any, **k: Any) -> Any:
        raise ValueError("current_action_denied")

    monkeypatch.setattr(prepared_input, "semantic_input", denied)
    assert core.command_worker_run_prepare(args) == 1
    assert capture(root, paths) == before


def test_changed_driver_log_path_preserves_old_raw_stream(
    legacy: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, args, paths = legacy
    paths["stdout"].write_bytes(b"old\xff\x00\r\n")
    driver = core.load_yaml_document(Path(args.driver))
    driver.setdefault("io", {})["stdout"] = (
        ".pf/runtime/agent-runs/run/task/new-stdout.log"
    )
    write_yaml_file(Path(args.driver), driver)
    publication = pending(legacy, monkeypatch)
    assert publication.old["stdout"] == b"old\xff\x00\r\n"
    assert core.command_worker_run_prepare(args) == 0
    assert paths["stdout"].read_bytes() == b"old\xff\x00\r\n"
    assert not paths["stdout"].with_name("new-stdout.log").exists()
    assert core.json_read(paths["status"])["stdout_path"].endswith("/new-stdout.log")


@pytest.mark.parametrize("stop", [False, True])
def test_completed_then_retry_has_blank_new_ownership(
    sql_cli_fixture: Any, monkeypatch: pytest.MonkeyPatch, stop: bool
) -> None:
    from processforge_core.executions.composition import ExecutionStorage

    root, _, args, _ = sql_cli_fixture
    monkeypatch.setattr(
        core, "_execution_storage", lambda *a, **k: ExecutionStorage("legacy")
    )
    monkeypatch.setattr(core, "_storage_first_write", lambda *a, **k: (None, None))
    assert core.command_worker_run_prepare(args) == 0
    assert core.command_worker_run_start(args) == 0
    paths = core._work_paths.worker_run(root, "run", "task")
    originals = capture(root, paths)
    assert core.command_worker_run_prepare(args) == 0
    state = core.json_read(paths["status"])
    assert state["attempt"] == 2 and state["status"] == "ready"
    assert all(
        state[key] is None
        for key in (
            "pid",
            "started_at",
            "finished_at",
            "exit_code",
            "last_heartbeat_at",
        )
    )
    assert not paths["process"].exists() and not paths["exit"].exists()
    previous = paths["root"] / "attempts/1"
    for key in rp.OBSERVATIONS:
        if originals[key] is not None:
            assert (
                previous / ("retry-previous-" + key + ".json")
            ).read_bytes() == originals[key]
    assert core.command_worker_run_status(args) == 0
    assert (
        core.command_worker_run_stop(args)
        if stop
        else core.command_worker_run_start(args)
    ) == 0
    assert core.json_read(paths["status"])["attempt"] == 2
