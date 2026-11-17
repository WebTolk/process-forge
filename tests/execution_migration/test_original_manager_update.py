"""Refusals are real negative evidence, not native upgrade qualification."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pf_native_control as native
import pytest

from processforge_core.maintenance.file_update import (
    checked_owned_paths,
    require_unmanaged_target,
)
from processforge_core.maintenance.original_manager_update import (
    OriginalManagerUpdateService,
    OriginalRelease,
)
from processforge_core.maintenance.update import CoreUpdateError


def manifest(*names: str, version: str = "1.2.0") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "version": version,
        "files": [
            {"relative_path": name, "sha256": native.digest(b"old"), "size": 3}
            for name in names
        ],
    }


@pytest.mark.parametrize(
    "name", [".pf/AGENTS.md", ".pf/hooks.yaml", ".pf/process-forge.yaml"]
)
def test_only_exact_historical_entries_may_be_removed(
    tmp_path: Path, name: str
) -> None:
    checked_owned_paths(tmp_path, manifest(name), installed_legacy=True)
    with pytest.raises(CoreUpdateError):
        checked_owned_paths(tmp_path, manifest(name))
    with pytest.raises(CoreUpdateError):
        checked_owned_paths(
            tmp_path, manifest(name, version="1.3.0"), installed_legacy=True
        )


@pytest.mark.parametrize(
    "name",
    [
        ".pf/agents.md",
        ".pf/user-history.json",
        ".PF/hooks.yaml",
        "runtime/user.bin",
        ".git/config",
    ],
)
def test_no_observed_private_bytes_become_release_ownership(
    tmp_path: Path, name: str
) -> None:
    with pytest.raises(CoreUpdateError):
        checked_owned_paths(tmp_path, manifest(name), installed_legacy=True)


@pytest.mark.parametrize("marker", ["managed-ingress", "native-control"])
def test_partial_managed_marker_never_gets_file_only_route(
    tmp_path: Path, marker: str
) -> None:
    directory = tmp_path / "runtime" / marker
    directory.mkdir(parents=True)
    (tmp_path / "unknown.bin").write_bytes(b"preserved")
    with pytest.raises(CoreUpdateError):
        require_unmanaged_target(tmp_path)
    assert (tmp_path / "unknown.bin").read_bytes() == b"preserved"
    assert not tuple(directory.iterdir())


@pytest.mark.parametrize(
    "archive,sidecar",
    [
        (b"observed installed hashes", b"{}"),
        (b"repacked genuine archive with a native leaf", b"{}"),
        (b"", b"issuer: true"),
    ],
)
def test_observed_or_repacked_release_is_not_original_provenance(
    archive: bytes, sidecar: bytes
) -> None:
    with pytest.raises(CoreUpdateError, match="pin differs"):
        OriginalRelease.public_1_2(archive, sidecar)


def test_supplied_public_release_member_and_manifest_parity() -> None:
    # Optional source-data check, never a positive authority/upgrade assertion.
    public = os.environ.get("PF_ORIGINAL_PUBLIC_INPUT")
    if public is None:
        pytest.skip("genuine public release input is not supplied")
        return
    directory = Path(public)
    archive = (directory / "processforge-1.2.0.zip").read_bytes()
    sidecar = (directory / "processforge-1.2.0.manifest.json").read_bytes()
    accepted = OriginalRelease.public_1_2(archive, sidecar)
    assert len(accepted.members) == 1318
    assert native.LEAF not in accepted.members
    assert json.loads(accepted.manifest)["version"] == "1.2.0"
    with pytest.raises(TypeError):
        accepted.members["observed.txt"] = b"not accepted"  # type: ignore[index]
    with pytest.raises(CoreUpdateError):
        OriginalRelease.public_1_2(archive, sidecar + b" ")


@pytest.fixture
def original_boundary(tmp_path: Path):
    if os.name != "nt":
        pytest.skip("real Windows retained Job test")
    core = tmp_path / "core"
    core.mkdir()
    (core / "owned.txt").write_bytes(b"original")
    controls = tmp_path / "original-gate"
    controls.mkdir()
    guard, epoch = controls / "guard", controls / "epoch"
    guard.write_bytes(b"0")
    epoch.write_text("original-profile", encoding="ascii")
    boundary = native.LegacyManagedBoundary(
        core,
        existing_gate=native.NativeControl(guard, epoch, "original-profile"),
        accepted_archive={"owned.txt": b"original"},
    )
    try:
        yield boundary
    finally:
        for owners in boundary.owners.values():
            for process in owners:
                job = getattr(process, "native_job")
                if job.active():
                    assert job.stop(deadline=time.monotonic() + 5)
                process.wait(timeout=10)
                job.close()
        boundary.anchor.close()


def unissued_plan(boundary: native.LegacyManagedBoundary) -> native.LegacyUpdatePlan:
    return native.LegacyUpdatePlan(
        root=boundary.root,
        archive=b"not accepted",
        frozen=native.Build(MappingProxyType({}), b"{}", "0" * 64),
        old_manifest=b"{}",
        plan=b"{}",
        initial=MappingProxyType({"owned.txt": b"original"}),
        selection=native.ManagedSelection("", "", "", "", "", ()),
        profile=b"{}",
        workplace=None,
        selection_files=MappingProxyType({}),
    )


def test_plan_value_cannot_create_original_authority(original_boundary) -> None:
    boundary = original_boundary
    prepared = unissued_plan(boundary)
    with pytest.raises(native.NativeControlError):
        native.replace_legacy_core(boundary, prepared)
    # Even a registered data value is not an issuer-bound first-writer profile.
    boundary.prepared_update = prepared
    with pytest.raises(native.NativeControlError):
        native.replace_legacy_core(boundary, prepared)
    assert (boundary.root / "owned.txt").read_bytes() == b"original"
    assert not (boundary.root / "runtime").exists()


def test_resume_receipt_cannot_reconstruct_manager(
    original_boundary, tmp_path: Path
) -> None:
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"not accepted")
    with pytest.raises(native.NativeControlError):
        native.resume_legacy_core(
            original_boundary, archive, update_id="core-update-receipt"
        )
    assert not (original_boundary.root / "runtime").exists()


@pytest.mark.parametrize("ingress", sorted(native.LegacyManagedBoundary.INGRESS))
def test_all_retained_ingress_jobs_block_replacement(
    original_boundary, ingress: str
) -> None:
    boundary = original_boundary
    process = boundary.launch(
        [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
        ingress=ingress,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with boundary.held():
        assert boundary.facts()[0] == "active"
        prepared = unissued_plan(boundary)
        boundary.prepared_update = prepared
        with pytest.raises(native.NativeControlError):
            native.replace_legacy_core(boundary, prepared)
    assert process.native_job.stop(deadline=time.monotonic() + 5)
    process.wait(timeout=10)
    deadline = time.monotonic() + 5
    while process.native_job.active() and time.monotonic() < deadline:
        time.sleep(0.01)
    with boundary.held():
        assert boundary.facts()[0] == "proven"
        with pytest.raises(native.NativeControlError):
            boundary.original_profile()
    assert not (boundary.root / "runtime").exists()


def test_detached_descendant_keeps_original_manager_active(
    original_boundary, tmp_path: Path
) -> None:
    boundary = original_boundary
    ready = tmp_path / "descendant-ready"
    child = (
        "import pathlib,time; pathlib.Path("
        + repr(str(ready))
        + ").write_text('ready'); time.sleep(30)"
    )
    parent = (
        "import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c',"
        + repr(child)
        + "])"
    )
    process = boundary.launch([sys.executable, "-B", "-c", parent], ingress="worker")
    assert process.wait(timeout=10) == 0
    deadline = time.monotonic() + 5
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready.exists()
    with boundary.held():
        assert boundary.facts()[0] == "active"
        prepared = unissued_plan(boundary)
        boundary.prepared_update = prepared
        with pytest.raises(native.NativeControlError):
            native.replace_legacy_core(boundary, prepared)
    assert getattr(process, "native_job").stop(deadline=time.monotonic() + 5)
    assert not (boundary.root / "runtime").exists()


def test_uncertain_spawn_poison_is_not_retired_by_empty_owner_list(
    original_boundary, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed_spawn(*args: Any, **kwargs: Any) -> Any:
        raise OSError("injected spawn publication failure")

    boundary = original_boundary
    monkeypatch.setattr(native, "spawn_owned", failed_spawn)
    with pytest.raises(OSError):
        boundary.launch([sys.executable, "-B", "-c", "pass"], ingress="cli")
    with boundary.held():
        assert not any(boundary.owners.values())
        assert boundary.facts()[0] == "unknown"
        with pytest.raises(native.NativeControlError):
            boundary.launch([sys.executable, "-B", "-c", "pass"], ingress="worker")
    assert not (boundary.root / "runtime").exists()


def test_lost_original_anchor_does_not_mean_idle(original_boundary) -> None:
    boundary = original_boundary
    boundary.anchor.close()
    with boundary.held():
        assert boundary.facts()[0] == "unknown"
        boundary.prepared_update = unissued_plan(boundary)
        with pytest.raises(native.NativeControlError):
            native.replace_legacy_core(boundary, boundary.prepared_update)
    assert not (boundary.root / "runtime").exists()


@pytest.mark.parametrize("ingress", sorted(native.LegacyManagedBoundary.INGRESS))
def test_durable_intent_closes_every_old_route(original_boundary, ingress: str) -> None:
    boundary = original_boundary
    marker = boundary.root / "runtime/managed-ingress/legacy-replacement.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{}", encoding="ascii")
    before = marker.read_bytes()
    with pytest.raises(native.NativeControlError):
        boundary.launch([sys.executable, "-B", "-c", "pass"], ingress=ingress)
    assert not any(boundary.owners.values())
    assert marker.read_bytes() == before
    assert (boundary.root / "owned.txt").read_bytes() == b"original"


def test_prejournal_resume_cannot_replace_missing_original_profile(
    original_boundary, tmp_path: Path
) -> None:
    boundary = original_boundary
    prepared = unissued_plan(boundary)
    boundary.update_plan = prepared
    archive = tmp_path / "same-archive.zip"
    archive.write_bytes(prepared.archive)
    with pytest.raises(native.NativeControlError):
        native.resume_legacy_core(boundary, archive, update_id=prepared.update_id)
    assert boundary.update_journal is None
    assert not (boundary.root / "runtime").exists()


def test_uncertain_child_does_not_replay_even_in_live_manager(
    original_boundary,
) -> None:
    boundary = original_boundary
    prepared = unissued_plan(boundary)
    boundary.update_plan = prepared
    boundary.update_child_started = True
    # This path is deliberately absent: refusal must precede any archive read.
    with pytest.raises(native.NativeControlError):
        native.resume_legacy_core(
            boundary, boundary.root / "absent.zip", update_id=prepared.update_id
        )
    assert not (boundary.root / "runtime").exists()


def test_genuine_archive_alone_cannot_issue_original_manager_authority(
    tmp_path: Path,
) -> None:
    if os.name != "nt":
        pytest.skip("real Windows original manager refusal")
    supplied = os.environ.get("PF_ORIGINAL_PUBLIC_INPUT")
    if supplied is None:
        pytest.skip("genuine public release input is not supplied")
        return
    public = Path(supplied)
    release = OriginalRelease.public_1_2(
        (public / "processforge-1.2.0.zip").read_bytes(),
        (public / "processforge-1.2.0.manifest.json").read_bytes(),
    )
    core = tmp_path / "genuine-core"
    core.mkdir()
    for name, raw in release.members.items():
        path = core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    guard, epoch = tmp_path / "guard", tmp_path / "epoch"
    guard.write_bytes(b"0")
    epoch.write_bytes(b"original")
    boundary = native.LegacyManagedBoundary(
        core,
        existing_gate=native.NativeControl(guard, epoch, "original"),
        accepted_archive=release.members,
    )
    try:
        with pytest.raises(native.NativeControlError):
            OriginalManagerUpdateService(
                boundary,
                release,
                selection=native.ManagedSelection("", "", "", "", "", ()),
            )
        assert not (core / "runtime").exists()
        assert all(
            (core / name).read_bytes() == raw for name, raw in release.members.items()
        )
    finally:
        boundary.anchor.close()


@pytest.fixture
def control_file_plan(original_boundary):
    """Real target archive as data; this fixture issues no profile or authority."""
    import io
    import zipfile

    supplied = os.environ.get("PF_ORIGINAL_TARGET_ARCHIVE")
    if supplied is None:
        pytest.skip("accepted target archive is not supplied for control-file tests")
        return
    archive = Path(supplied).read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        raw = bundle.read(native.MANIFEST)
    frozen = native._freeze_update_archive(
        archive, {"new_manifest": native.parse_manifest(raw)}
    )
    boundary = original_boundary
    # Only the file-publication helper is exercised. Neither replace nor resume
    # accepts this data fixture as an original-manager operation.
    return boundary, native.LegacyUpdatePlan(
        root=boundary.root,
        archive=archive,
        frozen=frozen,
        old_manifest=b"old control bytes",
        plan=b"retained plan bytes",
        initial=MappingProxyType({"owned.txt": b"original"}),
        selection=native.ManagedSelection("", "", "", "", "", ()),
        profile=b"{}",
        workplace=None,
        selection_files=MappingProxyType({}),
    )


@pytest.mark.parametrize("cutpoint", ["old-manifest", "new-manifest", "plan"])
def test_control_publication_retries_real_filesystem_failure(
    control_file_plan, monkeypatch: pytest.MonkeyPatch, cutpoint: str
) -> None:
    boundary, prepared = control_file_plan
    prefix = f"runtime/core-update/backups/{prepared.update_id}"
    directory = boundary.root / prefix
    blocked = directory / "control" / (cutpoint + ".json.pf-update-tmp")
    write = native._update_atomic

    def fail_with_directory(path: Path, raw: bytes) -> None:
        if path.name == cutpoint + ".json" and not blocked.exists():
            blocked.parent.mkdir(parents=True, exist_ok=True)
            blocked.mkdir()
        write(path, raw)

    monkeypatch.setattr(native, "_update_atomic", fail_with_directory)
    with pytest.raises(OSError):
        native._publish_legacy_controls(boundary, prepared, prefix)
    identity = boundary.update_directory_identity
    assert identity is not None and blocked.is_dir()
    fence = boundary.root / "runtime/managed-ingress/legacy-replacement.json"
    assert fence.is_file()
    assert (boundary.root / "owned.txt").read_bytes() == b"original"
    retained = {p.name: p.read_bytes() for p in (directory / "control").glob("*.json")}
    with pytest.raises(OSError):
        native._publish_legacy_controls(boundary, prepared, prefix)
    monkeypatch.setattr(native, "_update_atomic", write)
    blocked.rmdir()  # Only this test's own empty fault object is removed.
    native._publish_legacy_controls(boundary, prepared, prefix)
    assert boundary.update_directory_identity == identity
    assert all(
        (directory / "control" / name).read_bytes() == raw
        for name, raw in retained.items()
    )
    for name, expected in {
        "old-manifest": prepared.old_manifest,
        "new-manifest": prepared.frozen.manifest,
        "plan": prepared.plan,
    }.items():
        assert (directory / "control" / (name + ".json")).read_bytes() == expected
    assert boundary.update_plan is None and boundary.update_journal is None
    assert (boundary.root / "owned.txt").read_bytes() == b"original"


@pytest.mark.parametrize("conflict", ["control", "directory", "foreign-directory"])
def test_control_publication_preserves_conflicting_objects(
    control_file_plan, conflict: str
) -> None:
    boundary, prepared = control_file_plan
    prefix = f"runtime/core-update/backups/{prepared.update_id}"
    directory = boundary.root / prefix
    if conflict == "foreign-directory":
        directory.mkdir(parents=True)
        (directory / "unknown").write_bytes(b"preserve")
    else:
        native._publish_legacy_controls(boundary, prepared, prefix)
        if conflict == "control":
            (directory / "control/plan.json").write_bytes(b"foreign plan")
        else:
            directory.rename(directory.with_name(directory.name + "-preserved"))
            directory.mkdir()
            (directory / "unknown").write_bytes(b"preserve")
    before = {
        p.relative_to(directory): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    }
    with pytest.raises(OSError):
        native._publish_legacy_controls(boundary, prepared, prefix)
    assert {
        p.relative_to(directory): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file()
    } == before
    assert (boundary.root / "owned.txt").read_bytes() == b"original"
