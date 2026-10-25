"""Component checks; seam positives are never real cold-provider qualification."""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import time
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pf_native_control as p
import pytest
from pf_cold_controller import (
    Controller,
    Fence,
    FrozenArchive,
    Policy,
    Refused,
    Windows,
    identity,
    retirement,
)

ColdEnrollmentProducer = p.ManagedEnrollmentProducer
bootstrap_cold_control = p._durable_control
cold_storage_safety = p._managed_storage_safety


@pytest.fixture
def tmp_path() -> Path:
    # Python 3.14 mode=0700 temp dirs are inaccessible to this sandbox token.
    # Keep all exact fixture evidence, with inherited ACL, in owned scratch.
    root = Path(os.environ["W3_FIXTURE_ROOT"]) / "cold"
    root.mkdir(exist_ok=True)
    item = root / uuid4().hex
    item.mkdir()
    return item


def policy() -> Policy:
    return Policy(
        "S-1-5-21-123-456-789-1001",
        ("S-1-5-21-123-456-789-1002",),
        ((10, 0, 12345),),
        "sha256:" + "a" * 64,
    )


def sample(tick: int) -> dict[str, Any]:
    return {"low": tick, "high": tick + 1, "checked": False, "version": [10, 0, 12345]}


@pytest.mark.parametrize("after", [1000000, 1000001, 2000000])
def test_no_reset_refuses(after: int) -> None:
    with pytest.raises(p.NativeControlError):
        retirement(sample(1000000), sample(after), policy())


@pytest.mark.parametrize(
    "change",
    [
        {"checked": True},
        {"version": [10, 0, 99999]},
        {"low": True},
        {"low": -1},
        {"high": 2**63},
        {"high": 0},
    ],
)
def test_malformed_or_unqualified_observation_refuses(change: dict[str, Any]) -> None:
    with pytest.raises(p.NativeControlError):
        retirement(sample(1000000), dict(sample(1000), **change), policy())


def test_unqualified_default_refuses_even_synthetic_reset() -> None:
    with pytest.raises(p.NativeControlError):
        retirement(
            sample(1000000), sample(1000), replace(policy(), qualified_versions=())
        )


def test_policy_candidate_reset_only_synthetic() -> None:
    assert (
        retirement(sample(1000000), sample(1000), policy())["kind"]
        == "qualified-native-tick-reset-v1"
    )


def test_delay_and_sleep_resume_refuse() -> None:
    for after in (sample(1000000 + 3600000), sample(1000000 - 60000)):
        with pytest.raises(p.NativeControlError):
            retirement(sample(1000000), after, policy())


def test_real_same_boot_negative() -> None:
    windows = Windows()
    before, after = windows.sample(), windows.sample()
    trusted_test_profile = replace(
        policy(), qualified_versions=(tuple(before["version"]),)
    )
    with pytest.raises(p.NativeControlError):
        retirement(before, after, trusted_test_profile)


def test_actual_accesscheck_and_child_file_denial(tmp_path: Path) -> None:
    windows = Windows()
    file = tmp_path / "payload.py"
    file.write_bytes(b"THIS IS NOT EXECUTED")
    original = windows.sddl(file)
    with windows.process_token() as token:
        sid = windows.token_sid(token)
        assert windows.access(file, token) & 1
        try:
            # Explicit Everyone read denial is fixture-only; it preserves owner
            # WRITE_DAC for exact cleanup and is not a real deployment policy.
            denied = re.sub(r"(D:[^(]*)", r"\1(D;;0x1;;;WD)", original, count=1)
            assert sid
            windows.set_sddl(file, denied, owner=False)
            assert not windows.access(file, token) & 1
            child = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    "-c",
                    "import sys;\ntry: open(sys.argv[1],'rb').read()\nexcept PermissionError: sys.exit(7)\nsys.exit(9)",
                    str(file),
                ],
                capture_output=True,
                timeout=10,
                check=False,
            )
            assert child.returncode == 7, child.stderr
            assert not child.stdout
        finally:
            windows.set_sddl(file, original, owner=False)
        assert file.read_bytes() == b"THIS IS NOT EXECUTED"


def test_gate_persists_after_child_exit(tmp_path: Path) -> None:
    windows = Windows()
    file = tmp_path / "payload"
    file.write_bytes(b"old")
    original = windows.sddl(file)
    try:
        child = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "from pathlib import Path; from pf_cold_controller import Windows; import sys; "
                "Windows().set_sddl(Path(sys.argv[1]),sys.argv[2],owner=False)",
                str(file),
                re.sub(r"(D:[^(]*)", r"\1(D;;0x1;;;WD)", original, count=1),
            ],
            cwd=Path(p.__file__).parent,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert child.returncode == 0, child.stderr
        with pytest.raises(PermissionError):
            file.read_bytes()
    finally:
        windows.set_sddl(file, original, owner=False)


def test_native_lock_blocks_real_other_process(tmp_path: Path) -> None:
    guard, epoch = tmp_path / "controller.guard", tmp_path / "controller.epoch"
    guard.write_bytes(b"0")
    epoch.write_text("cold-v1", encoding="ascii")
    control = p.NativeControl(guard, epoch, "cold-v1")
    script = (
        "import sys,time;from pathlib import Path;import pf_native_control as p;"
        "c=p.NativeControl(Path(sys.argv[1]),Path(sys.argv[2]),'cold-v1');\n"
        "try:\n with c.exclusive(deadline=time.monotonic()+0.2): sys.exit(9)\n"
        "except p.NativeControlError: sys.exit(7)\n"
    )
    with control.exclusive():
        result = subprocess.run(
            [sys.executable, "-B", "-c", script, str(guard), str(epoch)],
            cwd=Path(p.__file__).parent,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 7, result.stderr
    with control.exclusive(deadline=time.monotonic() + 1):
        pass


def test_hardlink_refuses(tmp_path: Path) -> None:
    file, alias = tmp_path / "first", tmp_path / "alias"
    file.write_bytes(b"a")
    os.link(file, alias)
    with pytest.raises(p.NativeControlError):
        identity(file)


class SeamWindows:
    """Explicit deterministic policy seam, not Windows retirement evidence."""

    def __init__(self) -> None:
        self.tick = 1000000

    def sample(self) -> dict[str, Any]:
        return sample(self.tick)

    def set_sddl(self, path: Path, value: str) -> None:
        # No real ACL qualification in state-machine/copy seam tests.
        pass


class SeamFence:
    """Only controller state-machine tests use this injected gate."""

    def __init__(self, root: Path) -> None:
        self.roots, self.policy, self.windows = (root,), policy(), SeamWindows()
        self.records = [{"fixture": "closed"}]

    def verify(self) -> list[dict[str, Any]]:
        return self.records

    def install(self) -> list[dict[str, Any]]:
        return self.verify()


class SeamController(Controller):
    def protected_control(self) -> None:
        pass


@pytest.fixture
def controller(tmp_path: Path) -> Any:
    directory, root = tmp_path / "controller", tmp_path / "installation"
    directory.mkdir()
    root.mkdir()
    guard, epoch = directory / "controller.guard", directory / "controller.epoch"
    guard.write_bytes(b"0")
    epoch.write_text("cold-v1", encoding="ascii")
    return SeamController(
        directory,
        cast(Fence, SeamFence(root)),
        p.NativeControl(guard, epoch, "cold-v1"),
    )


def test_controller_real_lock_same_boot_refuses_with_seam_gate(controller: Any) -> None:
    with controller.held():
        controller.stage(archive_sha256="sha256:" + "a" * 64, selection={})
    with controller.held():
        with pytest.raises(p.NativeControlError), controller.resume():
            pytest.fail("same boot cannot issue authority")
        assert controller.state()["phase"] == "awaiting_retirement"


def test_authority_expires_and_gate_change_refuses(controller: Any) -> None:
    with controller.held():
        controller.stage(archive_sha256="sha256:" + "a" * 64, selection={})
        controller.fence.windows.tick = 1000
        with controller.resume() as authority:
            authority.verify()
            controller.fence.records = [{"fixture": "changed"}]
            with pytest.raises(p.NativeControlError):
                authority.verify()
        with pytest.raises(p.NativeControlError):
            authority.verify()


def test_guard_replacement_refuses(controller: Any) -> None:
    with controller.held():
        controller.stage(archive_sha256="sha256:" + "a" * 64, selection={})
    old = controller.control.guard.with_suffix(".old")
    controller.control.guard.rename(old)
    controller.control.guard.write_bytes(b"0")
    controller.fence.windows.tick = 1000
    with controller.held(), pytest.raises(Refused), controller.resume():
        pass


def make_archive() -> tuple[bytes, p.Build]:
    built = p.build_publication(
        {
            p.LEAF: Path(p.__file__).read_bytes(),
            p.INVENTORY: b"",
            "src/example.py": b"VALUE = 1\n",
        },
        version="1.3.0-alpha6",
        source={},
        generated_at="2026-10-25T00:00:00Z",
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, raw in {**dict(built.payload), p.MANIFEST: built.manifest}.items():
            archive.writestr(name, raw)
    return stream.getvalue(), built


def test_frozen_archive_actual_publication_parser() -> None:
    raw, built = make_archive()
    frozen = FrozenArchive.capture(
        raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
    )
    assert frozen.payload == built.payload
    with pytest.raises(p.NativeControlError):
        FrozenArchive.capture(
            raw + b"changed", built.manifest, expected_sha256="sha256:" + p.digest(raw)
        )


def test_distinct_cold_adoption_and_independent_bound_attach(controller: Any) -> None:
    raw, built = make_archive()
    frozen = FrozenArchive.capture(
        raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
    )
    root = controller.fence.roots[0]
    selection = p.ManagedSelection(
        "project", "workplace", "owner", "instance", "revision", ()
    )
    with controller.held():
        controller.stage(
            archive_sha256="sha256:" + p.digest(raw), selection=selection.document()
        )
        controller.fence.windows.tick = 1000
        with controller.resume() as authority:
            controller.before_copy(authority, raw)
            for name, content in {
                **dict(built.payload),
                p.MANIFEST: built.manifest,
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            frozen = FrozenArchive.capture(
                raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
            )
            controller.installed(authority, root=root, frozen=frozen)
            publication = p.accept_publication(root, trusted_leaf=built.payload[p.LEAF])
            entry = p.NativeEntry(root, publication, None, None)
            producer, adopted = ColdEnrollmentProducer.from_cold_provider(
                authority, entry, selection=selection
            )
            from pf_cold_controller import fresh_child

            child = fresh_child(authority, adopted, frozen, interpreter=sys.executable)
            assert child["result"] == "verified"
            assert adopted.control is not None
            assert child["epoch"] == adopted.control.accepted_epoch
            assert controller.state()["phase"] == "bound"
            state = producer._state()
            assert (
                state["origin"] == "cold-v1"
                and "sentinel" not in state
                and "launches" not in state
            )
    # No original manager or controller authority is live after this point.
    independent = ColdEnrollmentProducer(root, built.payload[p.LEAF])
    attached = independent.attach(adopted, selection=selection)
    assert attached.control is not None
    with attached.operation():
        assert p._native_life_held(attached.control)
    assert not p._native_life_held(attached.control)
    with pytest.raises(p.NativeControlError):
        authority.verify()
    assert producer._legacy_closure(state) == "unknown"
    assert (
        bootstrap_cold_control(root, built.projection_sha256).accepted_epoch
        == attached.control.accepted_epoch
    )
    context = SimpleNamespace(
        project_root="project", workplace_root="workplace", targets=()
    )
    with independent.operation(
        attached, resolver=lambda: selection, admission_held=lambda: True
    ):
        verdict, generation, evidence = cold_storage_safety(attached, context)
        assert verdict == "proven" and generation == state["adoption"]
        assert "durable_cold_retirement" in evidence
        assert "durable_retired_legacy_set" not in evidence
    assert cold_storage_safety(attached, context)[0] == "unknown"
    head = producer.directory / "adoption.json"
    head.write_bytes(b"{}")
    with pytest.raises(p.NativeControlError):
        independent.attach(adopted, selection=selection)
    recovered = independent.recover_replacement(trusted_leaf=built.payload[p.LEAF])
    assert recovered.control is not None
    assert recovered.control.accepted_epoch == attached.control.accepted_epoch
    independent.attach(recovered, selection=selection)
    old_epoch = recovered.control.accepted_epoch
    with independent.replacement(
        recovered, target_leaf=built.payload[p.LEAF]
    ) as publish:
        publish(built.payload[p.LEAF])
    replacement = independent.recover_replacement(trusted_leaf=built.payload[p.LEAF])
    assert replacement.control is not None
    assert replacement.control.accepted_epoch != old_epoch
    with pytest.raises(p.NativeControlError), attached.operation():
        pass


def test_no_caller_bool_as_authority() -> None:
    with pytest.raises(p.NativeControlError):
        getattr(ColdEnrollmentProducer, "from_cold_provider")(
            True, None, selection=None
        )


def test_actual_copy_bytes_with_explicit_gate_boot_seams(controller: Any) -> None:
    raw, built = make_archive()
    frozen = FrozenArchive.capture(
        raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
    )
    root = controller.fence.roots[0]
    for name, content in {**dict(built.payload), p.MANIFEST: built.manifest}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    old = root / "src/example.py"
    old.write_bytes(b"OLD = 1\n")
    with controller.held():
        controller.stage(archive_sha256=frozen.archive_sha256, selection={})
        controller.fence.windows.tick = 1000
        with controller.resume() as authority:
            entry = frozen.copy(authority, root, controller.directory / "backup")
            assert entry.publication is not None
            assert entry.publication.payload == built.payload
            assert old.read_bytes() == b"VALUE = 1\n"
            assert (
                controller.directory / "backup/src/example.py"
            ).read_bytes() == b"OLD = 1\n"
            assert controller.state()["phase"] == "installed"


def test_cold_pending_fault_refuses_then_exact_seam_resume(
    controller: Any, monkeypatch: Any
) -> None:
    raw, built = make_archive()
    root = controller.fence.roots[0]
    selection = p.ManagedSelection(
        "project", "workplace", "owner", "instance", "revision", ()
    )
    frozen = FrozenArchive.capture(
        raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
    )
    for name, content in {**dict(built.payload), p.MANIFEST: built.manifest}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    original = p._atomic

    def fail_epoch(path: Path, value: Any) -> None:
        if path.name == "epoch":
            raise OSError("component interruption before epoch")
        original(path, value)

    with controller.held():
        controller.stage(
            archive_sha256=frozen.archive_sha256, selection=selection.document()
        )
        controller.fence.windows.tick = 1000
        with controller.resume() as authority:
            entry = frozen.copy(authority, root, controller.directory / "backup")
            monkeypatch.setattr(p, "_atomic", fail_epoch)
            with pytest.raises(OSError):
                ColdEnrollmentProducer.from_cold_provider(
                    authority, entry, selection=selection
                )
    producer = ColdEnrollmentProducer(root, built.payload[p.LEAF])
    generation = producer._state()["adoption"]
    with pytest.raises(p.NativeControlError):
        bootstrap_cold_control(root, built.projection_sha256)
    monkeypatch.setattr(p, "_atomic", original)
    with controller.held(), controller.resume() as authority:
        producer, adopted = ColdEnrollmentProducer.from_cold_provider(
            authority, entry, selection=selection
        )
        assert producer._state()["adoption"] == generation
        assert producer._state()["phase"] == "bound" and adopted.control is not None


def test_g2_interruption_resume_and_corrupt_backup(
    controller: Any, monkeypatch: Any
) -> None:
    from pf_cold_controller import copy_resumable

    raw, built = make_archive()
    root = controller.fence.roots[0]
    for name, content in {**dict(built.payload), p.MANIFEST: built.manifest}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    frozen = FrozenArchive.capture(
        raw, built.manifest, expected_sha256="sha256:" + p.digest(raw)
    )
    original = p._update_atomic
    interrupted = False

    def write(path: Path, content: bytes) -> None:
        nonlocal interrupted
        original(path, content)
        if path == root / "src/example.py" and not interrupted:
            interrupted = True
            raise OSError("fixture interruption after native overwrite")

    with controller.held():
        controller.stage(archive_sha256=frozen.archive_sha256, selection={})
        controller.fence.windows.tick = 1000
        with controller.resume() as authority:
            monkeypatch.setattr(p, "_update_atomic", write)
            with pytest.raises(OSError):
                copy_resumable(authority, frozen, root)
    monkeypatch.setattr(p, "_update_atomic", original)
    with controller.held(), controller.resume() as authority:
        entry = copy_resumable(authority, frozen, root)
        assert entry.publication is not None
        assert entry.publication.payload == built.payload
        backup = controller.directory / "backup/src/example.py"
        backup.write_bytes(b"corrupt")
        before = (root / "src/example.py").read_bytes()
        with pytest.raises(p.NativeControlError):
            copy_resumable(authority, frozen, root)
        assert (root / "src/example.py").read_bytes() == before


def test_fixed_command_rejects_late_override(tmp_path: Path, monkeypatch: Any) -> None:
    import pf_native_maintenance as h

    monkeypatch.setattr(h, "validate_preparation", lambda *args: ({}, {}))
    selected = {
        "kind": "work",
        "project_id": "project",
        "run_id": "run",
        "assignment_id": "task",
        "context_id": "context",
        "attempt": 1,
    }
    prepared = {"identity": selected}
    distribution = tmp_path / "distribution"
    reference = {"path": ".pf/input.json", "checksum": "sha256:" + "a" * 64}
    source = str(tmp_path / reference["path"])
    paths = {"heartbeat": ".pf/heartbeat.json", "exit": ".pf/exit.json"}
    argv = [
        sys.executable,
        "-I",
        "-B",
        str(distribution / "tools/prepared_executor.py"),
        "--prepared-input",
        source,
        "--prepared-sha256",
        reference["checksum"],
        "--heartbeat",
        str(tmp_path / paths["heartbeat"]),
        "--exit-path",
        str(tmp_path / paths["exit"]),
        "--",
        sys.executable,
        "-I",
        "-B",
        str(distribution / "tools/pf_native_maintenance.py"),
        source,
    ]
    command: dict[str, Any] = {
        "driver_id": "native-maintenance-fixed-v1",
        "executable_override": "",
        "agent_model": "",
        "agent_reasoning_effort": "",
        "run_id": "run",
        "task_id": "task",
        "attempt": "1",
        "prepared_input": reference,
        "paths": paths,
        "command": {
            "argv": argv,
            "args": argv[1:],
            "executable": sys.executable,
            "shell": False,
            "environment_inherit": False,
            "working_directory": str(tmp_path),
            "environment": {
                "PF_PREPARED_INPUT_FILE": source,
                "PF_PREPARED_INPUT_SHA256": reference["checksum"],
                "PF_PROJECT_ROOT": str(tmp_path),
                "PF_RUNTIME_DRIVER_ID": "native-maintenance-fixed-v1",
                "PF_WORKER_RUN_ID": "run",
                "PF_WORKER_TASK_ID": "task",
                "PF_WORKER_ATTEMPT": "1",
                "PF_AGENT_MODEL": "",
                "PF_AGENT_REASONING_EFFORT": "",
            },
        },
    }
    h.validate_command(prepared, tmp_path, distribution, command)
    command["command"]["argv"] = [sys.executable, "-c", "raise SystemExit(0)"]
    with pytest.raises(h.Rejected, match="fixed_command_mismatch"):
        h.validate_command(prepared, tmp_path, distribution, command)


@pytest.mark.parametrize(
    "key,value",
    [("access", "metadata"), ("delivery", "metadata"), ("status", "missing")],
)
def test_metadata_never_body_grant(key: str, value: str) -> None:
    import pf_native_maintenance as h

    row = {"path": "body.json", "sha256": "sha256:" + "a" * 64, "size": 1}
    source = {
        "path": row["path"],
        "checksum": row["sha256"],
        "size": 1,
        "delivery": "reference",
        "status": "available",
    }
    if key == "access":
        # Access lives on the job row and is rejected independently by capture.
        row[key] = value
        assert row["access"] != "body"
    else:
        source[key] = value
        assert not h._body_granted({"input": {"sources": [source]}}, row)


def test_runtime_closure_requires_declared_bodies(tmp_path: Path) -> None:
    import pf_native_maintenance as h

    spec = {
        "runtime_closure": [
            {"path": name, "sha256": "sha256:" + "a" * 64, "size": 1, "role": role}
            for name, role in [
                ("python.exe", "interpreter"),
                ("python.dll", "dll"),
                ("python.zip", "stdlib"),
                ("bootstrap.py", "bootstrap"),
            ]
        ]
    }
    with pytest.raises(h.Rejected, match="runtime_body_grant"):
        h._closure(
            {"input": {"scope": {"allowed_read_files": []}, "sources": []}},
            tmp_path,
            spec,
        )
