"""Component checks; seam positives are never real cold-provider qualification."""

from __future__ import annotations

import copy
import io
import json
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
        assert not h._body_granted(
            {
                "input": {
                    "sources": [source],
                    "scope": {
                        "allowed_actions": ["read"],
                        "allowed_read_files": ["body.json"],
                    },
                }
            },
            row,
        )


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


@pytest.fixture
def native_fixture(tmp_path: Path, monkeypatch: Any) -> Any:
    """Real Core producer/registry with synthetic management qualification only.

    No Work lifecycle is started. All issuer records are isolated file fixtures.
    The tiny closure is deliberately synthetic, not host/runtime qualification.
    """
    import pf_native_maintenance as h
    import processforge as core

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.prepared.registry_resources import tool_snapshot_record
    from processforge_core.work.context import build_context_fields, fingerprint

    distribution = Path(__file__).resolve().parents[2]
    project = tmp_path / "project"
    project.mkdir()
    (project / ".pf/artifacts").mkdir(parents=True)

    def put(name: str, raw: bytes) -> dict[str, Any]:
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"path": name, "sha256": h.digest(raw), "size": len(raw)}

    # A venv redirector permits an isolated executable location without installing.
    runtime_source = Path(os.environ["NATIVE_FIXTURE_PYTHON"])
    interpreter = put("runtime/python.exe", runtime_source.read_bytes())
    (project / "runtime/pyvenv.cfg").write_text(
        "home = " + sys.base_prefix + "\ninclude-system-site-packages = true\n",
        encoding="utf-8",
    )
    executable = str(project / interpreter["path"])
    closure = [dict(interpreter, role="interpreter")]
    for role in ("dll", "stdlib", "bootstrap"):
        closure.append(dict(put("runtime/" + role, b"synthetic fixture"), role=role))
    namespace = {
        key: str(project / ("namespace/" + key))
        for key in (
            "bundle",
            "workplace",
            "device",
            "accounting",
            "execution",
            "control",
        )
    }
    namespace["project"] = str(project)
    qualification = put(
        "qualification.json",
        h.canonical(
            {
                "management_namespace": namespace,
                "runtime_closure_sha256": h.digest(h.canonical(closure)),
                "runtime_version": sys.version.split()[0],
            }
        ),
    )
    spec = {
        "schema_version": 1,
        "namespace": namespace,
        "target_roots": [str(tmp_path / "target")],
        "runtime_closure": closure,
        "qualification": qualification,
        "deployment": {"fixture": "not real cold authority"},
    }
    bodies = {"management": put("management.json", h.canonical(spec))}
    for role, name in {
        "harness": "pf_native_maintenance.py",
        "controller": "pf_cold_controller.py",
        "native": "pf_native_control.py",
        "wrapper": "prepared_executor.py",
    }.items():
        bodies[role] = put(
            "tools/" + name, (distribution / "tools" / name).read_bytes()
        )
    driver = json.loads(
        (
            distribution / "templates/runtime-drivers/native-maintenance-fixed-v1.json"
        ).read_bytes()
    )
    bodies["descriptor"] = put("driver.json", h.canonical(driver))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("hello.txt", b"hello")
    bodies["archive"] = put("archive.zip", stream.getvalue())
    bodies["manifest"] = put(
        "manifest.json",
        h.canonical(
            {
                "schema_version": 1,
                "files": [
                    {"path": "hello.txt", "sha256": h.digest(b"hello"), "size": 5}
                ],
            }
        ),
    )
    selected = {
        "kind": "work",
        "project_id": "fixture",
        "run_id": "fixture-run",
        "assignment_id": "fixture-task",
        "context_id": "fixture-task-capsule",
        "attempt": 1,
    }
    runtime = {
        "resource_id": "management-python",
        "access": ["body", "execute"],
        "sha256": interpreter["sha256"],
        "version": sys.version.split()[0],
    }
    job = {
        "schema_version": 1,
        "identity": selected,
        "operation": "qualify-archive",
        "resources": [
            dict(row, role=role, access="body") for role, row in bodies.items()
        ],
        "runtime": runtime,
        "report": ".pf/artifacts/report.json",
    }
    binding = {
        "schema_version": 1,
        "identity": selected,
        "job_sha256": h.digest(h.canonical(job)),
        "descriptor_sha256": bodies["descriptor"]["sha256"],
        "runtime": runtime,
        "execute_sources": [
            dict(bodies[role], role=role)
            for role in ("wrapper", "harness", "controller", "native")
        ],
        "operation": job["operation"],
        "management_sha256": bodies["management"]["sha256"],
        "qualification_sha256": qualification["sha256"],
        "deployment": None,
    }
    request = {
        "id": "fixture-native",
        "path_ref": {"registry": "tools", "id": "fixture-native"},
        "native_maintenance": binding,
    }
    definition = {
        "id": request["id"],
        "status": "configured",
        "capability": "processforge.native-maintenance.fixed-v1",
        "command": "NEVER EXECUTED",
        "native_maintenance": {
            "schema_version": 1,
            "profile": "native-maintenance-fixed-v1",
            "bindings": [copy.deepcopy(binding)],
        },
    }
    write_yaml_file(project / "workplace.yaml", {"schema_version": 1})
    write_yaml_file(
        project / "registries/tools.yaml", {"schema_version": 1, "tools": [definition]}
    )
    write_yaml_file(
        project / ".pf/process-forge.yaml",
        {"project": {"id": "fixture"}, "workplace": {"reference": "auto"}},
    )
    snapshot = {
        "snapshot": {"id": "fixture-snapshot"},
        "resolved": {
            "tools": [
                tool_snapshot_record(project / "workplace.yaml", request["id"], set())
            ],
            "knowledge_resources": [],
        },
    }
    snapshot_path = project / ".pf/contexts/project-context.snapshot.yaml"
    write_yaml_file(snapshot_path, snapshot)
    pin = {
        "process_id": "fixture-process",
        "process_version": "1",
        "process_fingerprint": fingerprint({"stages": []}),
        "definition": {"stages": []},
        "selected_resource_ids": [],
    }
    task = {
        "id": "fixture-task",
        "run_id": "fixture-run",
        "process": "fixture-process",
        "execution_mode": {
            "kind": "implementation",
            "code_changes_allowed": True,
            "artifact_changes_allowed": True,
        },
        "objective": "synthetic authority fixture",
        "allowed_actions": ["read", "write_artifact", "write_product"],
        "allowed_files": [job["report"], "namespace/bundle/**"],
        "allowed_read_files": [row["path"] for row in bodies.values()]
        + [row["path"] for row in closure]
        + [qualification["path"]],
        "required_sources": [row["path"] for row in bodies.values()]
        + [row["path"] for row in closure]
        + [qualification["path"]],
        "expected_report": {"artifact": job["report"]},
        "required_outputs": [{"id": "report", "path": job["report"], "required": True}],
        "workspace_access": {"tools": [request]},
        "parameters": {"native_maintenance_job": job},
    }
    run = {
        "id": task["run_id"],
        "process": task["process"],
        "tasks": [{"id": task["id"]}],
    }
    write_yaml_file(project / ".pf/runs/fixture-run/run.yaml", run)
    assignment = project / ".pf/assignments/fixture-task.yaml"
    write_yaml_file(assignment, task)

    class FixtureCore:
        # Only workplace health is synthetic. No producer/validator is mocked.
        def __getattr__(self, name: str) -> Any:
            return getattr(core, name)

        def project_context_check_result(
            self, *args: Any, **kwargs: Any
        ) -> dict[str, str]:
            return {"status": "fresh"}

        def resolve_workplace_root(self, *args: Any, **kwargs: Any) -> Path:
            return project

    selected_core = FixtureCore()
    fields = build_context_fields(
        project,
        assignment,
        task,
        snapshot,
        selected_core,
        workplace=project,
        pin=pin,
        run_record=run,
    )
    capsule = {
        **fields,
        "capsule": {"id": selected["context_id"]},
        "context_snapshot": {
            "id": "fixture-snapshot",
            "sha256": h.digest(snapshot_path.read_bytes()),
        },
    }
    assert capsule["execution_contract"]["readiness"] == {
        "status": "ready",
        "blockers": [],
    }
    write_yaml_file(
        project / ".pf/contexts/assignment-capsules/fixture-task.capsule.yaml", capsule
    )
    monkeypatch.setattr(h, "__file__", str(project / "tools/pf_native_maintenance.py"))
    monkeypatch.setattr(sys, "executable", executable)
    return SimpleNamespace(
        project=project,
        task=task,
        capsule=capsule,
        core=selected_core,
        driver=driver,
        definition=definition,
        binding=binding,
        spec=spec,
        distribution=distribution,
    )


def prepare_native(f: Any) -> dict[str, Any]:
    import pf_native_maintenance as h

    from processforge_core.prepared.input import build

    prepared = build(f.project, f.task, f.capsule, 1, f.core)
    h.bind_preparation(prepared, f.project, f.project, f.driver)
    return prepared


def test_normal_native_producer_schema_consumer(native_fixture: Any) -> None:
    import pf_native_maintenance as h

    from processforge_core.maintenance.schema_checks import UpdateSchemaChecks
    from processforge_core.prepared.input import write_once
    from processforge_core.runtime.command import WorkerCommandBuilder

    f = native_fixture
    prepared = prepare_native(f)
    assert set(prepared["input"]["resources"]["grants"]) == {
        "tools",
        "mcp",
        "templates",
        "knowledge_resources",
    }
    schema = json.loads(
        (f.distribution / "schemas/prepared-input.schema.json").read_bytes()
    )
    assert not UpdateSchemaChecks(f.distribution).validate(
        prepared, schema, schema, "$"
    )
    path = (
        f.project
        / ".pf/runtime/agent-runs/fixture-run/fixture-task/attempts/1/prepared-input.json"
    )
    checksum = write_once(path, prepared)
    with pytest.raises(FileExistsError):
        write_once(path, prepared)
    report, result = h.execute(prepared, f.project)
    assert report == ".pf/artifacts/report.json"
    assert json.loads(result)["summary"] == {"files": 1, "expanded_bytes": 5}
    # Standalone fixed harness validates the same immutable bytes and emits report.
    command, _ = WorkerCommandBuilder(f.project).build(
        f.project,
        f.task,
        f.driver,
        prepared_input={
            "path": path.relative_to(f.project).as_posix(),
            "checksum": checksum,
        },
    )
    env = command["command"]["environment"]
    child = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(f.project / "tools/pf_native_maintenance.py"),
            str(path),
        ],
        env=env,
        cwd=f.project,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert child.returncode == 0, child.stderr
    assert (f.project / report).read_bytes() == result


@pytest.mark.parametrize(
    "case",
    [
        "id-only",
        "no-policy",
        "revoked",
        "changed-policy",
        "duplicate-policy",
        "body-only",
        "execute-only",
        "metadata",
        "scope",
        "attempt",
        "job",
        "operation",
        "source",
        "version",
    ],
)
def test_native_authority_denied_before_read(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    prepared = prepare_native(f)
    semantic = prepared["input"]
    request = semantic["resources"]["requested"]["tools"][0]
    entry = semantic["resources"]["grants"]["tools"][0]["resolution"]["entry"]
    if case == "id-only":
        semantic["resources"]["requested"]["tools"] = [request["id"]]
    elif case == "no-policy":
        del entry["native_maintenance"]
    elif case == "revoked":
        entry["status"] = "revoked"
    elif case == "changed-policy":
        entry["native_maintenance"]["bindings"][0]["qualification_sha256"] = (
            "sha256:" + "0" * 64
        )
    elif case == "duplicate-policy":
        entry["native_maintenance"]["bindings"] *= 2
    elif case in {"body-only", "execute-only"}:
        request["native_maintenance"]["runtime"]["access"] = [
            "body" if case == "body-only" else "execute"
        ]
    elif case == "metadata":
        semantic["sources"][0]["delivery"] = "metadata"
    elif case == "scope":
        semantic["scope"]["forbidden_actions"] = ["read"]
    elif case == "attempt":
        prepared["identity"]["attempt"] = 2
    elif case == "job":
        semantic["parameters"]["native_maintenance_job"]["report"] += "-other"
    elif case == "operation":
        semantic["parameters"]["native_maintenance_job"]["operation"] = "cold-stage"
    elif case == "source":
        request["native_maintenance"]["execute_sources"][0]["sha256"] = (
            "sha256:" + "0" * 64
        )
    elif case == "version":
        request["native_maintenance"]["runtime"]["version"] = "0.0"

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("read or compile before denial")

    monkeypatch.setattr(h, "read_file", unexpected)
    monkeypatch.setattr(h, "_captured_module", unexpected)
    with pytest.raises(ValueError):
        h.execute(prepared, f.project)


@pytest.mark.parametrize("case", ["revoked", "changed", "duplicate"])
def test_normal_producer_current_policy_denial(native_fixture: Any, case: str) -> None:
    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.prepared.input import build

    f = native_fixture
    definition = copy.deepcopy(f.definition)
    if case == "revoked":
        definition["status"] = "revoked"
    if case == "changed":
        definition["native_maintenance"]["bindings"][0]["job_sha256"] = (
            "sha256:" + "0" * 64
        )
    write_yaml_file(
        f.project / "registries/tools.yaml",
        {
            "schema_version": 1,
            "tools": [definition] * (2 if case == "duplicate" else 1),
        },
    )
    with pytest.raises(
        ValueError,
        match="resource_access_revoked|resource_generation_changed|resource_scope_invalid",
    ):
        build(f.project, f.task, f.capsule, 1, f.core)


def test_normal_fixed_command_acceptance(native_fixture: Any) -> None:
    """Acceptance gate: Windows normal builder must pass the fixed validator."""
    import pf_native_maintenance as h

    from processforge_core.prepared.input import write_once
    from processforge_core.runtime.command import WorkerCommandBuilder

    f = native_fixture
    prepared = prepare_native(f)
    path = (
        f.project
        / ".pf/runtime/agent-runs/fixture-run/fixture-task/attempts/1/prepared-input.json"
    )
    checksum = write_once(path, prepared)
    command, _ = WorkerCommandBuilder(f.project).build(
        f.project,
        f.task,
        f.driver,
        prepared_input={
            "path": path.relative_to(f.project).as_posix(),
            "checksum": checksum,
        },
    )
    h.validate_command(prepared, f.project, f.project, command)


def test_native_schema_rejects_widening(native_fixture: Any) -> None:
    from processforge_core.maintenance.schema_checks import UpdateSchemaChecks

    f = native_fixture
    prepared = prepare_native(f)
    schema = json.loads(
        (f.distribution / "schemas/prepared-input.schema.json").read_bytes()
    )
    check = UpdateSchemaChecks(f.distribution)
    for mutate in (
        lambda d: d["native_launch"].update(arbitrary=True),
        lambda d: d["native_launch"]["maintenance"]["runtime"].update(
            access=["execute"]
        ),
        lambda d: d["native_launch"]["maintenance"].update(permission=True),
    ):
        changed = copy.deepcopy(prepared)
        mutate(changed)
        assert check.validate(changed, schema, schema, "$")


def test_fixed_authority_checks_stay_equivalent() -> None:
    import ast
    import inspect

    import pf_native_maintenance as h

    from processforge_core.prepared.resources import _native_authority

    # Standalone held management has no Core imports; compare its repeated gate.
    assert ast.dump(ast.parse(inspect.getsource(h._native_authority))) == ast.dump(
        ast.parse(inspect.getsource(_native_authority))
    )


def reissue_fixture(f: Any, operation: str) -> None:
    """Issue fresh synthetic fixture policy/context without mutating old inputs."""
    import pf_native_maintenance as h

    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.prepared.registry_resources import tool_snapshot_record
    from processforge_core.work.context import build_context_fields

    f.task = copy.deepcopy(f.task)
    binding = f.task["workspace_access"]["tools"][0]["native_maintenance"]
    job = f.task["parameters"]["native_maintenance_job"]
    job["operation"] = operation
    binding["operation"] = operation
    binding["job_sha256"] = h.digest(h.canonical(job))
    binding["deployment"] = (
        {
            "access": ["read", "write", "acl"],
            "operations": [operation],
            "management_sha256": binding["management_sha256"],
            "spec_sha256": h.digest(h.canonical(f.spec["deployment"])),
        }
        if operation.startswith("cold-")
        else None
    )
    f.definition = copy.deepcopy(f.definition)
    f.definition["native_maintenance"]["bindings"] = [copy.deepcopy(binding)]
    write_yaml_file(f.project / "registries/tools.yaml", {"tools": [f.definition]})
    snapshot_path = f.project / ".pf/contexts/project-context.snapshot.yaml"
    snapshot = f.core.load_yaml_document(snapshot_path)
    snapshot["resolved"]["tools"] = [
        tool_snapshot_record(f.project / "workplace.yaml", f.definition["id"], set())
    ]
    write_yaml_file(snapshot_path, snapshot)
    assignment = f.project / ".pf/assignments/fixture-task.yaml"
    write_yaml_file(assignment, f.task)
    fields = build_context_fields(
        f.project,
        assignment,
        f.task,
        snapshot,
        f.core,
        workplace=f.project,
        pin=f.capsule["process_execution"],
        run_record=f.core.load_run(f.project, "fixture-run"),
    )
    f.capsule = {
        **fields,
        "capsule": {"id": "fixture-task-capsule"},
        "context_snapshot": {
            "id": "fixture-snapshot",
            "sha256": h.digest(snapshot_path.read_bytes()),
        },
    }
    write_yaml_file(
        f.project / ".pf/contexts/assignment-capsules/fixture-task.capsule.yaml",
        f.capsule,
    )


def test_normal_construct_management_requires_own_scope(native_fixture: Any) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    reissue_fixture(f, "construct-management")
    prepared = prepare_native(f)
    denied = copy.deepcopy(prepared)
    denied["input"]["scope"]["allowed_files"].remove("namespace/bundle/**")
    with pytest.raises(h.Rejected, match="bundle_write_grant"):
        h.execute(denied, f.project)
    destination = f.project / "namespace/bundle"
    assert not destination.exists()
    _, result = h.execute(prepared, f.project)
    assert json.loads(result)["summary"]["files"] == 9
    assert (destination / "bundle.json").is_file()


@pytest.mark.parametrize("case", ["spec", "qualification", "closure-scope"])
def test_synthetic_cold_denies_before_compile(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    reissue_fixture(f, "cold-stage")
    prepared = prepare_native(f)
    if case == "spec":
        f.spec["deployment"]["fixture"] = "different destination"
        # Altering pinned management bytes cannot gain new operational scope.
        (f.project / "management.json").write_bytes(h.canonical(f.spec))
    elif case == "qualification":
        prepared["input"]["sources"] = [
            s for s in prepared["input"]["sources"] if s["path"] != "qualification.json"
        ]
    else:
        prepared["input"]["scope"]["allowed_read_files"].remove("runtime/dll")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("captured module compiled before permission denial")

    monkeypatch.setattr(h, "_captured_module", forbidden)
    with pytest.raises(ValueError):
        h.execute(prepared, f.project)


def test_ordinary_file_only_build_has_no_native_authority(native_fixture: Any) -> None:
    from processforge_core.common.yaml_io import write_yaml_file
    from processforge_core.prepared.input import build
    from processforge_core.work.context import build_context_fields

    f = native_fixture
    f.task = copy.deepcopy(f.task)
    f.task["parameters"] = {}
    f.task["workspace_access"] = {}
    assignment = f.project / ".pf/assignments/fixture-task.yaml"
    write_yaml_file(assignment, f.task)
    snapshot = f.core.load_yaml_document(
        f.project / ".pf/contexts/project-context.snapshot.yaml"
    )
    fields = build_context_fields(
        f.project,
        assignment,
        f.task,
        snapshot,
        f.core,
        workplace=f.project,
        pin=f.capsule["process_execution"],
        run_record=f.core.load_run(f.project, "fixture-run"),
    )
    capsule = {
        **fields,
        "capsule": f.capsule["capsule"],
        "context_snapshot": f.capsule["context_snapshot"],
    }
    write_yaml_file(
        f.project / ".pf/contexts/assignment-capsules/fixture-task.capsule.yaml",
        capsule,
    )
    prepared = build(f.project, f.task, capsule, 1, f.core)
    assert "native_launch" not in prepared
    assert all(not rows for rows in prepared["input"]["resources"]["grants"].values())
