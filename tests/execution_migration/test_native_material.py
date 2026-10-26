"""Bounded material fixtures; synthetic issuer/closure is never Q0 qualification."""

from __future__ import annotations

import copy
import io
import json
import os
import struct
import zipfile
from pathlib import Path
from typing import Any

import pytest

from .test_cold_handoff import (
    make_archive,
    prepare_native,
)
from .test_cold_handoff import (
    native_fixture as native_fixture,
)
from .test_cold_handoff import (
    tmp_path as tmp_path,
)


def envelope(f: Any) -> dict[str, Any]:
    from processforge_core.prepared.input import build

    return build(f.project, f.task, f.capsule, 1, f.core)


def issue_material(prepared: dict[str, Any], change: Any) -> None:
    """Synthetic unit issuer only; no on-disk capsule/prepared file is changed."""
    semantic = prepared["input"]
    binding = semantic["resources"]["requested"]["tools"][0]["native_maintenance"]
    change(binding["material"])
    semantic["resources"]["grants"]["tools"][0]["resolution"]["entry"][
        "native_maintenance"
    ]["bindings"] = [copy.deepcopy(binding)]


def issue_manifest(f: Any, prepared: dict[str, Any], change: Any) -> None:
    import pf_native_maintenance as h

    name = "native-material.json"
    manifest = json.loads((f.project / name).read_bytes())
    change(manifest)
    raw = h.canonical(manifest)
    (f.project / name).write_bytes(raw)
    declaration = next(
        row for row in prepared["input"]["sources"] if row["path"] == name
    )
    declaration.update(checksum=h.digest(raw), size=len(raw))
    issue_material(
        prepared,
        lambda material: material["body_manifest"].update(
            sha256=h.digest(raw), size=len(raw)
        ),
    )


@pytest.mark.parametrize(
    "case",
    [
        "absent",
        "metadata",
        "permission",
        "capture",
        "capture-deny",
        "read-deny",
        "attempt",
        "old",
        "mixed",
        "unknown",
        "body-only",
        "execute-only",
        "manifest-size",
        "quota",
        "bool-quota",
    ],
)
def test_no_native_io_before_issued_authority(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    prepared = envelope(f)
    semantic = prepared["input"]
    binding = semantic["resources"]["requested"]["tools"][0]["native_maintenance"]
    if case == "absent":
        del binding["material"]
    elif case == "metadata":
        next(s for s in semantic["sources"] if s["path"] == "native-material.json")[
            "delivery"
        ] = "metadata"
    elif case == "permission":
        issue_material(prepared, lambda m: m.update(permission="body"))
    elif case == "capture":
        semantic["scope"]["allowed_files"] = [
            semantic["outputs"]["expected_report"]["artifact"]
        ]
    elif case == "capture-deny":
        semantic["scope"]["forbidden_files"] = [
            binding["material"]["capture"]["directory"] + "/archive.snapshot"
        ]
    elif case == "read-deny":
        semantic["scope"]["forbidden_files"] = ["runtime/*"]
    elif case == "attempt":
        prepared["identity"]["attempt"] = 2
    elif case == "old":
        semantic["parameters"]["native_maintenance_job"]["schema_version"] = 1
    elif case == "mixed":
        binding["schema_version"] = 1
    elif case == "unknown":
        issue_material(prepared, lambda m: m.update(available=True))
    elif case in {"body-only", "execute-only"}:
        binding["runtime"]["access"] = ["body" if case == "body-only" else "execute"]
    elif case == "manifest-size":
        issue_material(prepared, lambda m: m["body_manifest"].update(size=1048577))
    elif case == "quota":
        issue_material(
            prepared, lambda m: m["quotas"].update(total_material_bytes=536870913)
        )
    else:
        issue_material(prepared, lambda m: m["quotas"].update(members=True))

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("native member IO/compile before admission")

    monkeypatch.setattr(h, "_safe_material_file", forbidden)
    monkeypatch.setattr(h, "_captured_module", forbidden)
    with pytest.raises(ValueError):
        h.capture_material(prepared, f.project)


@pytest.mark.parametrize(
    "case",
    [
        "extra-key",
        "duplicate",
        "id-case",
        "path-case",
        "role",
        "zero",
        "bool-size",
        "large",
        "root",
        "runtime-row",
        "nfc",
        "device",
        "ads",
        "dotdot",
        "unc",
        "path-long",
    ],
)
def test_bad_manifest_denied_before_any_member_open(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    prepared = envelope(f)

    def mutate(manifest: dict[str, Any]) -> None:
        rows = manifest["members"]
        if case == "extra-key":
            manifest["available"] = True
        elif case == "duplicate":
            rows.append(copy.deepcopy(rows[0]))
        elif case == "id-case":
            rows[2]["resource_id"] = rows[1]["resource_id"].upper()
        elif case == "path-case":
            rows[2]["path"] = rows[1]["path"].upper()
        elif case == "role":
            rows[0]["role"] = "execute"
        elif case == "zero":
            rows[0]["size"] = 0
        elif case == "bool-size":
            rows[2]["size"] = True
        elif case == "large":
            rows[0]["size"] = 134217729
        elif case == "root":
            rows[0]["root_id"] = "runtime"
        elif case == "runtime-row":
            rows[2]["sha256"] = "sha256:" + "0" * 64
        else:
            rows[2]["path"] = {
                "nfc": "runtime/e\u0301",
                "device": "runtime/CON.txt",
                "ads": "runtime/x:stream",
                "dotdot": "runtime/../x",
                "unc": "//host/x",
                "path-long": "runtime/" + "a" * 1025,
            }[case]

    issue_manifest(f, prepared, mutate)
    monkeypatch.setattr(
        h,
        "_safe_material_file",
        lambda *a, **k: pytest.fail("member opened before whole manifest validation"),
    )
    with pytest.raises(ValueError):
        h.capture_material(prepared, f.project)


def test_actual_streaming_large_data_vs_unchanged_work_budget(
    native_fixture: Any,
) -> None:
    import pf_native_control as native
    import pf_native_maintenance as h

    from processforge_core.work.context import ContextContractError, _source

    f = native_fixture
    prepared = envelope(f)
    # Synthetic release-shaped payload, no executable code loaded from archive.
    built = native.build_publication(
        {
            native.LEAF: Path(native.__file__).read_bytes(),
            native.INVENTORY: b"",
            "data.bin": b"x" * 2097152,
        },
        version="1.3.0-alpha6",
        source={},
        generated_at="2026-10-26T00:00:00Z",
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        for name, raw in {
            **dict(built.payload),
            native.MANIFEST: built.manifest,
        }.items():
            package.writestr(name, raw)
    archive = output.getvalue()
    (f.project / "payloads/archive.zip").write_bytes(archive)
    (f.project / "manifest.json").write_bytes(built.manifest)
    job = prepared["input"]["parameters"]["native_maintenance_job"]
    for row in job["resources"]:
        if row["role"] in {"archive", "manifest"}:
            raw = archive if row["role"] == "archive" else built.manifest
            row.update(size=len(raw), sha256=h.digest(raw))
    for row in prepared["input"]["sources"]:
        if row["path"] == "manifest.json":
            row.update(size=len(built.manifest), checksum=h.digest(built.manifest))
    binding = prepared["input"]["resources"]["requested"]["tools"][0][
        "native_maintenance"
    ]
    binding["job_sha256"] = h.digest(h.canonical(job))
    issue_manifest(
        f,
        prepared,
        lambda m: m["members"][0].update(size=len(archive), sha256=h.digest(archive)),
    )
    with pytest.raises(ContextContractError, match="required_source_budget_exceeded"):
        _source(f.project, "payloads/archive.zip")
    receipt = h.capture_material(prepared, f.project)
    assert receipt["totals"]["bytes"] > 2097152
    assert h.validate_material(prepared, f.project, receipt)
    assert all(
        row["path"] != "payloads/archive.zip" for row in prepared["input"]["sources"]
    )
    from pf_cold_controller import FrozenArchive

    assert (
        FrozenArchive.capture(
            archive, built.manifest, expected_sha256=h.digest(archive)
        ).payload
        == built.payload
    )
    assert h.qualify_archive(archive, built.manifest, native)["files"] == 3


@pytest.mark.parametrize(
    "case",
    [
        "original",
        "runtime",
        "snapshot",
        "index",
        "snapshot-same-bytes",
        "missing",
        "attempt",
    ],
)
def test_frozen_material_changes_never_repaired(
    native_fixture: Any, monkeypatch: Any, case: str
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    prepared = prepare_native(f)
    receipt = prepared["native_launch"]["maintenance"]["material"]
    directory = f.project / receipt["index"]["path"]
    if case == "original":
        (f.project / "payloads/archive.zip").write_bytes(b"changed")
    elif case == "runtime":
        (f.project / "runtime/dll").write_bytes(b"changed")
    elif case in {"snapshot", "snapshot-same-bytes"}:
        target = directory.with_name("archive.snapshot")
        if case == "snapshot-same-bytes":
            raw = target.read_bytes()
            target.rename(target.with_name("old.snapshot"))
            target.write_bytes(raw)
        else:
            target.write_bytes(b"changed")
    elif case == "index":
        directory.write_bytes(b"{}")
    elif case == "missing":
        del prepared["native_launch"]["maintenance"]["material"]
    else:
        prepared["identity"]["attempt"] = 2
    before = {
        path.name: path.read_bytes()
        for path in directory.parent.iterdir()
        if path.is_file()
    }
    monkeypatch.setattr(
        h,
        "_captured_module",
        lambda *a, **k: pytest.fail("compile before revalidation"),
    )
    with pytest.raises((ValueError, OSError)):
        h.execute(prepared, f.project)
    assert before == {
        path.name: path.read_bytes()
        for path in directory.parent.iterdir()
        if path.is_file()
    }


def test_create_once_exact_reuse_and_partial_refusal(
    native_fixture: Any, monkeypatch: Any
) -> None:
    import pf_native_maintenance as h

    f = native_fixture
    prepared = envelope(f)
    real = os.fsync
    monkeypatch.setattr(
        h.os,
        "fsync",
        lambda fd: (_ for _ in ()).throw(OSError("fixture fsync interruption")),
    )
    with pytest.raises(OSError):
        h.capture_material(prepared, f.project)
    monkeypatch.setattr(h.os, "fsync", real)
    with pytest.raises(h.Rejected, match="material_partial"):
        h.capture_material(prepared, f.project)
    assert "material" not in prepared.get("native_launch", {}).get("maintenance", {})


def test_actual_windows_handles_block_writer_rename_and_parent_swap(
    tmp_path: Path,
) -> None:
    import pf_native_maintenance as h

    directory = tmp_path / "runtime"
    directory.mkdir()
    file = directory / "member"
    file.write_bytes(b"actual Windows sharing test")
    with h._safe_material_file(tmp_path, "runtime/member") as stream:
        assert stream.read() == b"actual Windows sharing test"
        with pytest.raises(OSError):
            file.write_bytes(b"changed")
        with pytest.raises(OSError):
            file.rename(directory / "other")
        with pytest.raises(OSError):
            directory.rename(tmp_path / "swapped")
    os.link(file, directory / "alias")
    with pytest.raises(h.Rejected, match="material_redirected"):
        with h._safe_material_file(tmp_path, "runtime/member"):
            pytest.fail("hardlinked member admitted")


def test_payload_budget_applies_before_effect_module(
    native_fixture: Any, monkeypatch: Any
) -> None:
    import pf_native_maintenance as h

    prepared = envelope(native_fixture)
    issue_material(
        prepared,
        lambda m: m["quotas"].update(native_consumer_payload_reservation_bytes=1),
    )
    receipt = h.capture_material(prepared, native_fixture.project)
    job = prepared["input"]["parameters"]["native_maintenance_job"]
    prepared["native_launch"] = {
        "maintenance": {
            "runtime": job["runtime"],
            "job_sha256": h.digest(h.canonical(job)),
            "material": receipt,
        }
    }
    monkeypatch.setattr(
        h,
        "_captured_module",
        lambda *a, **k: pytest.fail("compiled above issued memory budget"),
    )
    with pytest.raises(h.Rejected, match="native_payload_peak"):
        h.execute(prepared, native_fixture.project)


@pytest.mark.parametrize(
    "case",
    [
        "extra",
        "embedded",
        "duplicate",
        "header",
        "zip64",
        "multidisk",
        "overlap",
        "compressed",
        "expanded",
    ],
)
def test_release_archive_parser_bounds(case: str) -> None:
    import pf_native_control as native
    import pf_native_maintenance as h

    raw, built = make_archive()
    output = io.BytesIO()
    if case in {"extra", "embedded", "duplicate"}:
        with zipfile.ZipFile(output, "w") as package:
            for name, content in {
                **dict(built.payload),
                native.MANIFEST: built.manifest,
            }.items():
                package.writestr(
                    name,
                    b"{}"
                    if case == "embedded" and name == native.MANIFEST
                    else content,
                )
            if case == "extra":
                package.writestr("extra", b"x")
            elif case == "duplicate":
                package.writestr("SRC/EXAMPLE.PY", b"x")
        raw = output.getvalue()
    else:
        data = bytearray(raw)
        central = data.find(b"PK\x01\x02")
        eocd = data.rfind(b"PK\x05\x06")
        if case == "header":
            struct.pack_into("<H", data, central + 30, 65535)
        elif case == "zip64":
            struct.pack_into("<I", data, central + 20, 0xFFFFFFFF)
        elif case == "multidisk":
            struct.pack_into("<H", data, eocd + 4, 1)
        elif case == "overlap":
            struct.pack_into("<I", data, central + 42, 1)
        elif case == "compressed":
            struct.pack_into("<H", data, central + 10, 99)
        else:
            struct.pack_into("<I", data, central + 24, 33554433)
        raw = bytes(data)
    with pytest.raises(ValueError):
        h.qualify_archive(raw, built.manifest, native)


def test_real_lease_and_guard_generation_lifetime(
    native_fixture: Any, monkeypatch: Any
) -> None:
    """Real Windows lease/handles with synthetic entry; never Q0 authority."""
    import sys
    import threading

    import pf_native_control as native
    import pf_native_maintenance as h

    from processforge_core.prepared.input import write_once
    from processforge_core.prepared.resources import _NativeStartPreflight
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
    assert command["command"]["argv"][0] == sys.executable
    base = f.project / ".pf/lease-fixture"
    guard = base / "native-control/installation.guard"
    guard.parent.mkdir(parents=True)
    guard.write_bytes(b"guard")
    epoch = guard.with_name("epoch")
    epoch.write_text("fixture-epoch", encoding="ascii")
    head = base / "managed-ingress/adoption.json"
    head.parent.mkdir()
    head.write_bytes(
        h.canonical(
            {
                "installation": "synthetic",
                "archive": "synthetic",
                "generation": 1,
                "phase": "bound",
                "epoch": "fixture-epoch",
            }
        )
    )
    control = native.NativeControl(guard, epoch, "fixture-epoch")
    entry = native.NativeEntry(f.project, None, None, control)
    monkeypatch.setattr(native, "_ENTRY", entry)
    blocked = []

    def mutate():
        for name, path in (("epoch", epoch), ("generation", head)):
            try:
                path.write_bytes(b"changed")
            except OSError:
                blocked.append(name)
        try:
            guard.rename(guard.with_name("replaced.guard"))
        except OSError:
            blocked.append("guard")

    with h.hold_start_material(prepared, f.project, f.project, command):
        assert native._native_life_held(control)
        thread = threading.Thread(target=mutate)
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and set(blocked) == {
            "guard",
            "epoch",
            "generation",
        }
        # A caller dictionary and even a material-holding harness cannot issue
        # the Core current-policy seal or bypass its operation-local issuer.
        fake = _NativeStartPreflight(command, prepared, entry)
        with pytest.raises(ValueError, match="native_preflight_not_held"):
            fake.admit(command, 1, command["prepared_input"])
    assert not native._native_life_held(control)
    epoch.write_text("next-generation", encoding="ascii")
    with pytest.raises(OSError):
        with h.hold_start_material(prepared, f.project, f.project, command):
            pytest.fail("stale guard epoch admitted")
