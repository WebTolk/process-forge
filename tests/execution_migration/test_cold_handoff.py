"""Component checks; seam positives are never real cold-provider qualification."""

from __future__ import annotations

import copy
import importlib.util
import inspect
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
    with pytest.raises((ValueError, KeyError)):
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
    project = tmp_path / "project with spaces"
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
    archive_raw, built = make_archive()
    bodies["archive"] = put("payloads/archive.zip", archive_raw)
    bodies["manifest"] = put("manifest.json", built.manifest)
    material_rows = [
        dict(
            bodies["archive"],
            resource_id="target-archive",
            role="archive",
            root_id="archive",
        )
    ]
    material_rows += [
        dict(row, resource_id="runtime-" + str(i), root_id="runtime")
        for i, row in enumerate(closure)
    ]
    material_manifest = put(
        "native-material.json",
        h.canonical(
            {
                "schema_version": 1,
                "kind": "pf.native-material.manifest",
                "members": material_rows,
            }
        ),
    )
    capture = (
        ".pf/runtime/agent-runs/fixture-run/fixture-task/attempts/1/native-material"
    )
    material = {
        "schema_version": 1,
        "body_manifest": dict(material_manifest, resource_id="native-material"),
        "roots": [
            {"id": "archive", "base": "project", "relative_path": "payloads"},
            {"id": "runtime", "base": "project", "relative_path": "runtime"},
        ],
        "permission": "body-and-qualified-runtime-load",
        "capture": {
            "directory": capture,
            "access": ["create_once", "read", "remove_own_partial"],
        },
        "quotas": {
            "manifest_bytes": 1048576,
            "receipt_index_bytes": 1048576,
            "members": 4096,
            "root_prefixes": 2,
            "path_utf8_bytes": 1024,
            "resource_id_bytes": 160,
            "member_bytes": 134217728,
            "interpreter_bytes": 33554432,
            "total_material_bytes": 536870912,
            "copy_chunk_bytes": 65536,
            "capture_working_buffer_bytes": 1048576,
            "capture_metadata_accounted_bytes": 16777216,
            "capture_directory_disk_bytes": 536870912,
            "zip_central_directory_bytes": 4194304,
            "zip_header_member_bytes": 16384,
            "zip_header_total_bytes": 4194304,
            "zip_tail_probe_bytes": 65557,
            "native_consumer_payload_reservation_bytes": 67108864,
        },
    }
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
        "schema_version": 2,
        "identity": selected,
        "operation": "qualify-archive",
        "resources": [
            dict(row, role=role, access="body") for role, row in bodies.items()
        ],
        "runtime": runtime,
        "report": ".pf/artifacts/report.json",
    }
    binding = {
        "schema_version": 2,
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
        "material": material,
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
            "schema_version": 2,
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
        "process_version": "1.0.0",
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
        "allowed_files": [job["report"], "namespace/bundle/**", capture + "/**"],
        "allowed_read_files": [row["path"] for row in bodies.values()]
        + [row["path"] for row in closure]
        + [qualification["path"], material_manifest["path"], capture + "/**"],
        "required_sources": [
            row["path"] for role, row in bodies.items() if role != "archive"
        ]
        + [qualification["path"], material_manifest["path"]],
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
    # Import the actual pinned file, rather than relabeling an ambient module.
    module_spec = importlib.util.spec_from_file_location(
        "pf_native_maintenance", project / "tools/pf_native_maintenance.py"
    )
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "pf_native_maintenance", module)
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
        expected_summary={
            "files": len(built.payload),
            "expanded_bytes": sum(map(len, built.payload.values())),
        },
    )


def prepare_native(f: Any) -> dict[str, Any]:
    import pf_native_maintenance as h

    from processforge_core.prepared.input import build

    prepared = build(f.project, f.task, f.capsule, 1, f.core)
    h.bind_preparation(prepared, f.project, f.project, f.driver)
    return prepared


@pytest.mark.parametrize(
    "case", ["same-body-wrong-root", "harness-body", "qualified-root", "runtime-origin"]
)
def test_native_actual_origin_and_body_reference(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    """A body pin never substitutes for the actual admitted execution origin."""
    import pf_native_maintenance as h

    f = native_fixture
    prepared = prepare_native(f)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("effect module compiled before origin/body denial")

    monkeypatch.setattr(h, "_captured_module", forbidden)
    if case == "same-body-wrong-root":
        path = f.project.parent / "unauthorized" / "pf_native_maintenance.py"
        path.parent.mkdir()
        path.write_bytes(Path(h.__file__).read_bytes())
        spec = importlib.util.spec_from_file_location("foreign_harness", path)
        assert spec is not None and spec.loader is not None
        foreign = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foreign)
        assert path.read_bytes() == Path(h.__file__).read_bytes()
        monkeypatch.setattr(foreign, "_captured_module", forbidden)
        with pytest.raises(foreign.Rejected, match="harness_path_mismatch"):
            foreign.execute(prepared, f.project)
    elif case == "harness-body":
        path = f.project / "tools/pf_native_maintenance.py"
        path.write_bytes(path.read_bytes() + b"\n# changed body\n")
        with pytest.raises(h.Rejected, match="resource_pin_mismatch"):
            h.execute(prepared, f.project)
    elif case == "qualified-root":
        _, captured = h.capture_job(prepared, f.project)
        changed = copy.deepcopy(f.spec)
        changed["namespace"]["project"] = str(f.project.parent / "unqualified")
        captured["management"] = h.canonical(changed)
        # Isolate the namespace gate; capture_job separately enforces body pins.
        with pytest.raises(h.Rejected, match="management_project_binding"):
            h.management(prepared, f.project, captured)
    else:
        path = f.project.parent / "unqualified-python.exe"
        path.write_bytes(Path(sys.executable).read_bytes())
        monkeypatch.setattr(sys, "executable", str(path))
        with pytest.raises(h.Rejected, match="executing_runtime_not_bound"):
            h.execute(prepared, f.project)
    assert not (f.project / ".pf/artifacts/report.json").exists()


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
    assert json.loads(result)["summary"] == f.expected_summary
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
    target = command["command"]["argv"]
    assert target[-2:] == [
        str(f.project / "tools/pf_native_maintenance.py"),
        str(path),
    ]
    for mutation in ("script", "argv", "environment"):
        changed = copy.deepcopy(command)
        if mutation == "script":
            changed["command"]["argv"][-2] += ".tampered"
            changed["command"]["args"][-2] += ".tampered"
        elif mutation == "argv":
            changed["command"]["argv"].append("--extra")
        else:
            changed["command"]["environment"]["PYTHONPATH"] = str(f.project)
        with pytest.raises(h.Rejected):
            h.validate_command(prepared, f.project, f.project, changed)


@pytest.mark.parametrize("fixed", [False, True])
def test_fixed_path_composition_preserves_other_arguments(
    tmp_path: Path, fixed: bool
) -> None:
    from processforge_core.runtime.command import WorkerCommandBuilder
    from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy

    driver = RuntimeDriverDefinitionPolicy().default_documents()["generic-shell"]
    driver["id"] = "native-maintenance-fixed-v1" if fixed else "generic-shell"
    driver["prepared_lifecycle_wrapper"] = False
    driver["command"] = {
        "executable": "{python_executable}",
        "args": [
            "-I",
            "-B",
            "{processforge_root}/tools/pf_native_maintenance.py",
            "literal/a\\b",
        ],
    }
    task = {"id": "task", "run_id": "run"}
    command, _ = WorkerCommandBuilder(tmp_path).build(tmp_path, task, driver)
    expected = (
        str(tmp_path / "tools/pf_native_maintenance.py")
        if fixed
        else str(tmp_path) + "/tools/pf_native_maintenance.py"
    )
    assert command["command"]["args"] == ["-I", "-B", expected, "literal/a\\b"]
    # A different template must stay visible to strict consumer validation.
    driver["command"]["args"][2] = "{processforge_root}/tools/../other.py"
    command, _ = WorkerCommandBuilder(tmp_path).build(tmp_path, task, driver)
    assert command["command"]["args"][2] == str(tmp_path) + "/tools/../other.py"


def _isolated_normal_route(project: str, backend: str, attack: str) -> None:
    """Run from the independent fixture distribution in a fresh interpreter."""
    import json
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    root = Path(project)
    assert not any(
        name in sys.modules
        for name in ("processforge", "pf_native_maintenance", "processforge_core")
    )
    sys.path[:0] = [str(root / "tools"), str(root / "src")]
    import pf_native_maintenance as h
    import processforge as core

    from processforge_core.configuration import DeviceConfigurationSource
    from processforge_core.maintenance.schema_checks import UpdateSchemaChecks
    from processforge_core.prepared import input as prepared_input
    from processforge_core.work.context import validate_execution_contract

    # Only health, device location and event recording are synthetic seams.
    core.project_context_check_result = lambda *a, **k: {"status": "fresh"}
    core.resolve_workplace_root = lambda *a, **k: root
    DeviceConfigurationSource.default_path = staticmethod(lambda: root / "device.yaml")
    core._process_event_recorder.emit_process_event = lambda *a, **k: {}
    assert core.ROOT == root
    assert Path(core.__file__) == root / "tools/processforge.py"
    assert Path(h.__file__) == root / "tools/pf_native_maintenance.py"
    assert Path(sys.executable) == root / "runtime/python.exe"
    for name, module in tuple(sys.modules.items()):
        if name.startswith("processforge_core"):
            if module.__file__ is not None:
                assert Path(module.__file__).is_relative_to(root / "src")
            else:
                assert all(
                    Path(path).is_relative_to(root / "src") for path in module.__path__
                )
    disk_capsule = core.load_yaml_document(
        core.assignment_capsule_path(root, "fixture-task")
    )
    disk_task = core.extract_assignment_front_matter(
        root / ".pf/assignments/fixture-task.yaml"
    )
    validation = validate_execution_contract(
        root,
        root / ".pf/assignments/fixture-task.yaml",
        disk_task,
        disk_capsule,
        core,
        require_ready=True,
    )
    assert validation["status"] == "valid", validation
    if backend == "sql":
        # Synthetic issuer storage setup; the actual SQL adapter/CAS is exercised.
        from uuid import uuid4

        from processforge_core.database import (
            Database,
            DatabaseIdentity,
            DatabaseTarget,
            SchemaManager,
            SQLiteDriver,
            SqlStatement,
        )
        from processforge_core.executions.schema import EXECUTION_SCHEMA

        store_id = uuid4().hex
        database = Database(
            SQLiteDriver(),
            DatabaseTarget(
                root / ".pf/data/pf.sqlite3",
                DatabaseIdentity(store_id, "project", "fixture"),
            ),
        )
        SchemaManager().initialize(database, (EXECUTION_SCHEMA,))
        with database.transaction() as session:
            session.execute(
                SqlStatement(
                    "INSERT INTO execution_state VALUES(1,'fixture',1,'sql','ready','complete',0,1,NULL,NULL)"
                )
            )
        core._core_common_json_io.json_write(
            root / ".pf/data/execution-storage.json",
            {
                "schema_version": 1,
                "project_id": "fixture",
                "store_id": store_id,
                "profile_id": "project_main",
                "target_relative_path": "data/pf.sqlite3",
            },
        )
    task, driver, paths = core.prepare_worker_run(root, "fixture-task", "driver.json")
    command = core.json_read(paths["command"])
    document = prepared_input.load(root, task, command, core)
    schema = json.loads((root / "schemas/prepared-input.schema.json").read_bytes())
    assert not UpdateSchemaChecks(root).validate(document, schema, schema, "$")
    args = SimpleNamespace(
        project_root=str(root),
        task=task["id"],
        driver="driver.json",
        executable=None,
        model=None,
        reasoning_effort=None,
        detach=False,
    )
    if attack == "detach":
        args.detach = True
        assert core.command_worker_run_start(args) == 1
        assert (
            not paths["process"].exists()
            and not (root / ".pf/artifacts/report.json").exists()
        )
        (root / "denied-route-evidence.json").write_text(
            json.dumps(
                {
                    "backend": backend,
                    "attack": attack,
                    "spawned": False,
                    "thread_created": False,
                }
            ),
            encoding="utf-8",
        )
        return
    import contextlib

    if attack in {"preflight-cancellation", "preflight-config"}:
        original_hold = h.hold_start_material

        @contextlib.contextmanager
        def mutate_during_preflight(*a, **kw):
            with original_hold(*a, **kw) as entry:
                if attack == "preflight-cancellation":
                    (root / ".pf/runs/fixture-run/cancellation-other.yaml").write_text(
                        "new intent", encoding="utf-8"
                    )
                else:
                    (root / ".pf/process-forge.local.yaml").write_text(
                        "workplace: {}", encoding="utf-8"
                    )
                yield entry

        h.hold_start_material = mutate_during_preflight
        assert core.command_worker_run_start(args) == 1
        assert (
            not paths["process"].exists()
            and not (root / ".pf/artifacts/report.json").exists()
        )
        (root / "denied-route-evidence.json").write_text(
            json.dumps(
                {
                    "backend": backend,
                    "attack": attack,
                    "spawned": False,
                    "thread_created": False,
                }
            ),
            encoding="utf-8",
        )
        return
    import threading
    import time

    import pf_native_control as native

    from processforge_core.executions.sqlite_repository import SQLiteExecutionRepository

    inside = False
    scans = {}
    timings = []
    operations = []
    blocked = []
    consume_blocked = []
    seals = []
    proceed = threading.Event()
    done = threading.Event()
    material = document["native_launch"]["maintenance"]["material"]
    request = document["input"]["resources"]["requested"]["tools"][0][
        "native_maintenance"
    ]
    capture = request["material"]["capture"]["directory"]
    protected = [
        material["index"]["path"],
        capture + "/archive.snapshot",
        "runtime/python.exe",
        "payloads/archive.zip",
        "tools/pf_native_maintenance.py",
        "management.json",
        "qualification.json",
        "registries/tools.yaml",
        ".pf/assignments/fixture-task.yaml",
        ".pf/contexts/project-context.snapshot.yaml",
        command["prepared_input"]["path"],
        paths["command"].relative_to(root).as_posix(),
        document["native_launch"]["configuration"]["path"],
    ]

    def writer():
        assert proceed.wait(20)
        try:
            for name in protected:
                try:
                    with (root / name).open("r+b") as stream:
                        stream.write(b"tampered")
                except OSError:
                    blocked.append(name)
                else:
                    raise AssertionError("preflight input was writable: " + name)
        finally:
            done.set()

    thread = threading.Thread(target=writer)
    thread.start()

    def spy(owner, name):
        original = getattr(owner, name)

        def checked(*a, **kw):
            assert not inside, "expensive scan inside admission: " + name
            scans[name] = scans.get(name, 0) + 1
            return original(*a, **kw)

        setattr(owner, name, checked)

    for name in (
        "_stream_material",
        "_zip_preflight",
        "digest",
        "read_file",
        "_material_plan",
    ):
        spy(h, name)
    spy(prepared_input, "load")
    spy(core, "_observe_sql_locked")
    spy(core, "_legacy_tree_probe")
    spy(SQLiteExecutionRepository, "page_history")
    real_gate = core._worker_start_admission
    real_spawn = native.spawn_owned

    @contextlib.contextmanager
    def gate(project_root):
        nonlocal inside
        assert (
            scans.get("_stream_material", 0) > 0 and scans.get("_zip_preflight", 0) > 0
        )
        proceed.set()
        assert done.wait(20)
        thread.join(5)
        assert not thread.is_alive() and len(blocked) == len(protected)
        if attack == "attempt":
            if backend == "sql":
                repository = core._execution_storage(root).repository
                old = repository.load_latest("fixture-run", "fixture-task")
                repository.allocate_attempt(
                    "fixture-run",
                    "fixture-task",
                    old.payload_json,
                    generation=old.generation,
                )
            else:
                state = core.json_read(paths["status"])
                state["attempt"] = 2
                core._core_common_json_io.json_write(paths["status"], state)
        elif attack == "entry":
            native._ENTRY = native.NativeEntry(root, None, None, None)
        elif attack == "cancellation":
            (root / ".pf/runs/fixture-run/cancellation-other.yaml").write_text(
                "new intent", encoding="utf-8"
            )
        with real_gate(project_root):
            before = time.monotonic()
            inside = True
            try:
                from processforge_core.prepared.resources import _ACTIVE_START

                seal = _ACTIVE_START.get()
                assert seal is not None
                seals.append(seal)
                try:
                    seal.admit(command, 999, command["prepared_input"])
                except ValueError:
                    pass
                else:
                    raise AssertionError("wrong attempt admitted")
                changed = dict(command, agent_model="late override")
                try:
                    seal.admit(changed, 1, command["prepared_input"])
                except ValueError:
                    pass
                else:
                    raise AssertionError("mutated command admitted")
                yield
            finally:
                inside = False
                timings.append(time.monotonic() - before)

    def spawn(*a, **kw):
        assert inside
        if backend == "sql":
            record = core._execution_storage(root).repository.load_latest(
                "fixture-run", "fixture-task"
            )
            assert record.phase == "starting" and record.launch_token == kw["token"]
        else:
            assert core.json_read(paths["status"])["status"] == "starting"
        operations.append("reserved-before-spawn")
        process = real_spawn(*a, **kw)
        actual_wait = process.wait

        def wait(*wa, **wk):
            assert not inside
            # Parent retains input handles through actual child consumption.
            for name in protected:
                if name == paths["command"].relative_to(root).as_posix():
                    continue
                try:
                    with (root / name).open("r+b") as stream:
                        stream.write(b"late tamper")
                except OSError:
                    consume_blocked.append(name)
                else:
                    raise AssertionError("consumer input became writable")
            return actual_wait(*wa, **wk)

        process.wait = wait
        try:
            seals[-1].admit(command, 1, command["prepared_input"])
        except ValueError:
            pass
        else:
            raise AssertionError("preflight used twice")
        return process

    core._worker_start_admission = gate
    native.spawn_owned = spawn
    result = core.command_worker_run_start(args)
    if attack:
        assert result == 1 and not operations
        assert not (root / ".pf/artifacts/report.json").exists()
        (root / "denied-route-evidence.json").write_text(
            json.dumps(
                {
                    "backend": backend,
                    "attack": attack,
                    "blocked_writers": blocked,
                    "consume_blocked": consume_blocked,
                    "scan_counts": scans,
                    "gate_seconds": timings,
                    "spawned": False,
                    "thread_joined": not thread.is_alive(),
                }
            ),
            encoding="utf-8",
        )
        return
    assert result == 0, (
        paths["stderr"].read_text(encoding="utf-8", errors="replace")
        if paths["stderr"].is_file()
        else "start refused"
    )
    assert operations == ["reserved-before-spawn"]
    assert len(consume_blocked) >= len(protected) - 1
    try:
        seals[-1].admit(command, 1, command["prepared_input"])
    except ValueError:
        pass
    else:
        raise AssertionError("expired seal admitted")
    assert timings and scans and len(blocked) == len(protected)
    assert core.json_read(paths["exit"])["exit_code"] == 0
    receipt_path, receipt = prepared_input.collection_receipt(root, task, command, core)
    assert receipt_path.is_file()
    assert receipt["identity"] == document["identity"]
    assert receipt["outputs"][0]["status"] == "present"
    report = json.loads((root / ".pf/artifacts/report.json").read_bytes())
    assert report["identity"] == document["identity"]
    assert report["operation"] == "qualify-archive"
    assert report["summary"]["files"] >= 3
    assert report["summary"]["expanded_bytes"] > 100000
    assert report["actual_provider_qualified"] is False
    assert report["production_ready"] is False
    job = document["input"]["parameters"]["native_maintenance_job"]
    rows = {row["role"]: row for row in job["resources"]}
    assert root / rows["harness"]["path"] == Path(h.__file__)
    assert h.digest(Path(h.__file__).read_bytes()) == rows["harness"]["sha256"]
    management = json.loads((root / rows["management"]["path"]).read_bytes())
    assert Path(management["namespace"]["project"]) == core.ROOT
    assert not any(
        core.ROOT == Path(target) or core.ROOT.is_relative_to(Path(target))
        for target in management["target_roots"]
    )
    process = core.json_read(paths["process"])
    assert int(process["pid"]) > 0
    (root / "normal-route-evidence.json").write_text(
        json.dumps(
            {
                "backend": backend,
                "scan_counts": scans,
                "gate_seconds": timings,
                "operations": operations,
                "blocked_writers": blocked,
                "consume_blocked": consume_blocked,
                "thread_joined": not thread.is_alive(),
                "identity": document["identity"],
                "prepared_checksum": command["prepared_input"]["checksum"],
                "stages": [
                    "contract",
                    "prepare",
                    "schema",
                    "start",
                    "wrapper",
                    "harness",
                    "collection",
                ],
                "exit": core.json_read(paths["exit"]),
                "process_pid": process["pid"],
                "report_sha256": h.digest(
                    (root / ".pf/artifacts/report.json").read_bytes()
                ),
                "body_reference": rows["harness"],
                "runtime": job["runtime"],
                "descriptor_sha256": rows["descriptor"]["sha256"],
                "source_root_equals_management_project": core.ROOT == root,
                "module_cache_isolated": True,
                "synthetic_qualification": True,
                "synchronous_start": args.detach is False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("backend", ["legacy", "sql"])
@pytest.mark.parametrize(
    "attack",
    [
        "",
        "attempt",
        "cancellation",
        "entry",
        "detach",
        "preflight-cancellation",
        "preflight-config",
    ],
)
def test_normal_fixed_prepare_start_collection(
    native_fixture: Any, backend: str, attack: str
) -> None:
    """Actual producer/wrapper/harness, independent Core, no module path seam."""
    f = native_fixture
    # The four-file construct inventory is insufficient: provide all Python
    # bootstrap/Core/tool sources and distribution data as fixture material.
    for directory in ("src", "tools", "schemas", "templates"):
        for source in (f.distribution / directory).rglob("*"):
            if source.is_file() and "__pycache__" not in source.parts:
                destination = f.project / source.relative_to(f.distribution)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
    for name in ("VERSION",):
        source = f.distribution / name
        if source.is_file():
            (f.project / name).write_bytes(source.read_bytes())
    script = f.project / "normal-route-fixture.py"
    script.write_text(
        inspect.getsource(_isolated_normal_route)
        + "\n_isolated_normal_route("
        + repr(str(f.project))
        + ", "
        + repr(backend)
        + ", "
        + repr(attack)
        + ")\n",
        encoding="utf-8",
    )
    child = subprocess.run(
        [sys.executable, "-I", "-B", str(script)],
        cwd=f.project,
        env={
            key: value for key, value in os.environ.items() if not key.startswith("PF_")
        },
        capture_output=True,
        timeout=60,
        check=False,
    )
    (f.project / "normal-route.stdout").write_bytes(child.stdout)
    (f.project / "normal-route.stderr").write_bytes(child.stderr)
    assert child.returncode == 0, child.stderr.decode("utf-8", errors="replace")
    if attack:
        evidence = json.loads((f.project / "denied-route-evidence.json").read_bytes())
        assert evidence["spawned"] is False
        if attack not in {"detach", "preflight-cancellation", "preflight-config"}:
            assert evidence["thread_joined"]
    else:
        evidence = json.loads((f.project / "normal-route-evidence.json").read_bytes())
        assert evidence["exit"]["exit_code"] == 0 and evidence["backend"] == backend


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
