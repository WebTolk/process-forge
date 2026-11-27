#!/usr/bin/env python3
"""Exercise package update preview, apply and rollback through the public CLI."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
from update_smoke_helpers import (
    first_candidate_id,
    make_update_fixture,
    require_ok,
    run_pf,
    sha256,
    write_json,
)


def update(workplace: Path, *args: str, refusal: str = "") -> None:
    result = run_pf("update", *args, "--workplace", str(workplace))
    if refusal:
        assert result.returncode == 1, result.stdout
        assert refusal in result.stdout and "Traceback" not in result.stdout, (
            result.stdout
        )
    else:
        require_ok(result)


def write_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def snapshot_tree(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        assert not path.is_symlink(), f"unexpected symlink: {relative}"
        if path.is_dir():
            entries[relative] = "directory"
            continue
        assert path.is_file(), f"unexpected entry type: {relative}"
        entries[relative] = f"sha256={sha256(path)}"
        if path.name == "stage-record.yaml":
            entries[relative] += f", mtime_ns={path.stat().st_mtime_ns}"
    return entries


def require_same_tree(before: dict[str, str], after: dict[str, str]) -> None:
    differences = [
        f"{path}: {before.get(path, '<absent>')} -> {after.get(path, '<absent>')}"
        for path in sorted(before.keys() | after.keys())
        if before.get(path) != after.get(path)
    ]
    assert not differences, "\n".join(differences)


def require_verified_stage(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert record.get("verified_at"), "stage-record.yaml is missing verified_at"
    assert record.get("status") == "verified", record.get("status")
    verification = record.get("verification")
    assert verification == {"sha256": "pass", "subject_identity": "pass"}, verification
    return record


def stage_package(workplace: Path, *, custom_policy: bool) -> tuple[str, Path, Path]:
    fixture = make_update_fixture(workplace)
    manifest_path = Path(fixture["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest["channels"]["stable"]["versions"][0]
    if custom_policy:
        version["update_policy"]["mode"] = "custom_command_requires_confirmation"
        write_json(manifest_path, manifest)

    update(workplace, "candidates", "refresh")
    candidate = first_candidate_id(workplace)
    update(workplace, "stage", "--candidate", candidate)
    stage_record = workplace / "runtime/update/staged" / candidate / "stage-record.yaml"
    record = yaml.safe_load(stage_record.read_text(encoding="utf-8"))
    assert "verified_at" not in record
    assert record["verification"] == {"sha256": "pass"}, record["verification"]
    staged_zip = workplace / record["artifact"]["path"]
    assert sha256(staged_zip) == version["sha256"], "staged ZIP SHA-256"

    # Make even a same-byte rewrite distinguishable on a coarse filesystem clock.
    stat = stage_record.stat()
    os.utime(stage_record, ns=(stat.st_atime_ns, stat.st_mtime_ns - 60_000_000_000))
    return candidate, stage_record, staged_zip


def check_preview_and_verification(root: Path) -> bool:
    failures: list[str] = []

    def check(
        name: str,
        command: tuple[str, ...],
        *,
        exit_code: int,
        stdout: tuple[str, ...],
        custom_policy: bool = False,
        tamper_zip: bool = False,
        writes_verification: bool = False,
    ) -> None:
        workplace = root / name
        try:
            candidate, stage_record, staged_zip = stage_package(
                workplace, custom_policy=custom_policy
            )
            if tamper_zip:
                with staged_zip.open("ab") as handle:
                    handle.write(b"changed staged ZIP")

            before = snapshot_tree(workplace)
            result = run_pf(
                "update",
                *command,
                "--candidate",
                candidate,
                "--workplace",
                str(workplace),
                merge_stderr=False,
            )
            expected_stdout = "\n".join(stdout).format(candidate=candidate) + "\n"
            actual = (result.returncode, result.stdout, result.stderr)
            expected = (exit_code, expected_stdout, "")
            assert actual == expected, f"expected CLI {expected!r}, got {actual!r}"
            print(
                f"CLI {name}: exit={result.returncode}, stdout={result.stdout!r}, "
                f"stderr={result.stderr!r}",
                flush=True,
            )

            after = snapshot_tree(workplace)
            if writes_verification:
                require_verified_stage(stage_record)
                stage_path = stage_record.relative_to(workplace).as_posix()
                before_record = before.pop(stage_path)
                after_record = after.pop(stage_path)
                assert before_record != after_record, f"{stage_path} was not updated"
                if command[0] == "apply":
                    # The normal apply lock leaves a permanent empty registry guard.
                    guard = "registries/.installed-subjects.yaml.lock.guard"
                    guard_path = workplace / guard
                    assert guard_path.is_file() and guard_path.stat().st_size == 0, guard
                    del after[guard]
            require_same_tree(before, after)
        except AssertionError as error:
            failures.append(f"FAIL: {name}: {error}")
        else:
            print(f"PASS: {name}", flush=True)

    verified = "VERIFIED: {candidate}"
    policy_refusal = (
        "FAIL: custom command update policy requires explicit --allow-custom-command "
        "and is not executed by default"
    )
    sha_refusal = "FAIL: sha256 mismatch"
    check(
        "preview",
        ("apply", "--confirm", "--dry-run"),
        exit_code=0,
        stdout=(verified, "DRY_RUN: would apply {candidate}"),
    )
    check(
        "preview-policy",
        ("apply", "--confirm", "--dry-run"),
        exit_code=1,
        stdout=(verified, policy_refusal),
        custom_policy=True,
    )
    check(
        "preview-sha",
        ("apply", "--confirm", "--dry-run"),
        exit_code=1,
        stdout=(sha_refusal,),
        tamper_zip=True,
    )
    check(
        "preview-confirm",
        ("apply", "--dry-run"),
        exit_code=1,
        stdout=("FAIL: update apply requires --confirm",),
    )
    check(
        "verify",
        ("verify",),
        exit_code=0,
        stdout=(verified,),
        writes_verification=True,
    )
    check("verify-sha", ("verify",), exit_code=1, stdout=(sha_refusal,), tamper_zip=True)
    check(
        "apply-policy",
        ("apply", "--confirm"),
        exit_code=1,
        stdout=(verified, policy_refusal),
        custom_policy=True,
        writes_verification=True,
    )
    for failure in failures:
        print(failure, file=sys.stderr)
    return not failures


def round_trip(workplace: Path, *, tool: bool) -> None:
    subject_id = "fixture.tool" if tool else "acme.software-processes"
    fixture = make_update_fixture(workplace, subject_id=subject_id, tool=tool)
    payload = (
        workplace / "tools/local-linter.py"
        if tool
        else workplace / "packages" / subject_id / "package.yaml"
    )
    registry = workplace / "registries/installed-subjects.yaml"
    original_payload = payload.read_bytes()
    original_tree = None if tool else snapshot_tree(payload.parent)
    initial = yaml.safe_load(registry.read_text(encoding="utf-8"))
    initial["subjects"][0]["fixture_note"] = "original selected record"
    other = {
        "type": "process_package",
        "id": "fixture.independent",
        "scope": "global",
        "version": "8.0.0",
    }
    initial["subjects"].append(other.copy())
    write_record(registry, initial)
    other_payload = workplace / "packages" / other["id"] / "README.md"
    other_payload.parent.mkdir(parents=True, exist_ok=True)
    other_payload.write_bytes(b"independent package\n")

    update(workplace, "candidates", "refresh")
    candidate = first_candidate_id(workplace)
    selector = ("--candidate", candidate)
    update(workplace, "stage", *selector)
    runtime = workplace / "runtime/update"
    staged = runtime / "staged" / candidate / "stage-record.yaml"
    applied = runtime / "applied" / candidate / "apply-record.yaml"
    backup_dir = runtime / "backups" / candidate
    if tool:
        update(workplace, "verify", *selector)
    else:
        stage = yaml.safe_load(staged.read_text(encoding="utf-8"))
        assert "verified_at" not in stage

    update(workplace, "apply", *selector, refusal="--confirm")
    result = run_pf(
        "update",
        "apply",
        *selector,
        "--confirm",
        "--workplace",
        str(workplace),
        merge_stderr=False,
    )
    assert result.stderr == "", result.stderr
    stdout = require_ok(result).splitlines()
    install_path = payload if tool else payload.parent
    expected_prefix = [
        f"VERIFIED: {candidate}",
        f"APPLIED: {candidate}",
        f"INSTALL_PATH: {install_path.relative_to(workplace).as_posix()}",
        f"BACKUP: {backup_dir.relative_to(workplace).as_posix()}",
    ]
    assert stdout[:4] == expected_prefix, result.stdout
    assert any(line.startswith("SEARCH_INDEX_") for line in stdout[4:]), result.stdout

    if not tool:
        stage = require_verified_stage(staged)
        source_zip = Path(fixture["artifact"])
        assert sha256(workplace / stage["artifact"]["path"]) == sha256(source_zip)
        with zipfile.ZipFile(source_zip) as archive:
            for name in archive.namelist():
                assert (install_path / name).read_bytes() == archive.read(name), name
        assert snapshot_tree(backup_dir / "previous") == original_tree
        print(
            f"CLI apply-directory: exit={result.returncode}, stdout={result.stdout!r}, "
            f"stderr={result.stderr!r}",
            flush=True,
        )

    applied_payload = payload.read_bytes()
    installed = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert applied_payload != original_payload
    assert installed["subjects"][0]["version"] == "1.1.0"
    installed["subjects"][1]["version"] = "8.1.0"
    write_record(registry, installed)

    cache = runtime / "candidates.json"
    source = Path(fixture["manifest"])
    assert source.is_file()
    update(workplace, "candidates", "refresh")
    proposals = json.loads(cache.read_text(encoding="utf-8"))
    assert candidate not in {row["id"] for row in proposals["candidates"]}
    if tool:
        source.unlink()
        update(workplace, "candidates", "refresh")
        proposals = json.loads(cache.read_text(encoding="utf-8"))
        assert proposals["conflicts"], proposals
        cache.unlink()

    preimage = backup_dir / "installed-subject.yaml"
    original_receipt = applied.read_bytes()
    metadata = yaml.safe_load(preimage.read_text(encoding="utf-8"))
    assert metadata["payload_kind"] == ("file" if tool else "tree")
    assert metadata["phase"] == "applied"

    def refuses(reason: str) -> None:
        saved_registry = registry.read_bytes()
        update(workplace, "rollback", *selector, refusal=reason)
        assert payload.read_bytes() == applied_payload
        assert registry.read_bytes() == saved_registry
        assert other_payload.read_bytes() == b"independent package\n"
        assert not (runtime / "rollbacks" / candidate / "rollback-record.yaml").exists()

    applied.write_text("candidate_id: [\n", encoding="utf-8")
    refuses("package_rollback_history_invalid")
    receipt = yaml.safe_load(original_receipt)
    assert receipt["candidate_id"] == candidate
    assert receipt["status"] == "applied"
    assert receipt["installed_version"] == "1.1.0"
    receipt["installed_version"] = "6.0.0"
    write_record(applied, receipt)
    refuses("package_metadata_preimage_mismatch")
    applied.write_bytes(original_receipt)

    assert receipt["previous_version"] == "1.0.0"
    changed_before = {**metadata["before"], "version": "8.0.0"}
    write_record(preimage, {**metadata, "before": changed_before})
    refuses("package_rollback_preimage_version_mismatch")

    write_record(preimage, {**metadata, "phase": ["invalid"]})
    refuses("package_metadata_preimage_mismatch")
    write_record(preimage, {**metadata, "phase": "prepared"})
    refuses("package_payload_backup_incomplete")
    write_record(preimage, metadata)

    changed = yaml.safe_load(registry.read_text(encoding="utf-8"))
    changed["subjects"][0]["version"] = "9.0.0"
    write_record(registry, changed)
    refuses("installed_subject_changed")
    write_record(registry, installed)

    backup = backup_dir / ("previous-file" if tool else "previous")
    held = backup.with_name("held-copy")
    backup.rename(held)
    refuses("package_payload_backup_invalid")
    held.rename(backup)

    # A complete version-one history also works after staging cleanup.
    metadata.pop("payload_kind")
    write_record(preimage, metadata)
    legacy_receipt = yaml.safe_load(original_receipt)
    legacy_receipt.pop("previous_version")
    legacy_receipt.pop("previous_subject_present")
    write_record(applied, legacy_receipt)
    staged.unlink()
    update(workplace, "rollback", *selector)
    restored = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert restored["subjects"] == [initial["subjects"][0], installed["subjects"][1]]
    assert payload.read_bytes() == original_payload
    assert other_payload.read_bytes() == b"independent package\n"
    if not tool:
        assert not (payload.parent / "README.md").exists()
    receipt = yaml.safe_load(
        (runtime / "rollbacks" / candidate / "rollback-record.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["candidate_id"] == candidate and receipt["status"] == "rolled_back"

    restored_registry = registry.read_bytes()
    update(workplace, "rollback", *selector)
    assert registry.read_bytes() == restored_registry
    assert payload.read_bytes() == original_payload
    print(f"PASS: {receipt['status']} {'file' if tool else 'tree'} by retained ID")


def check_initially_absent_package(workplace: Path) -> None:
    subject_id = "fixture.absent"
    make_update_fixture(workplace, subject_id=subject_id)
    registry = workplace / "registries/installed-subjects.yaml"
    before = yaml.safe_load(registry.read_text(encoding="utf-8"))["subjects"]
    package = workplace / "packages" / subject_id
    update(workplace, "candidates", "refresh")
    candidate = first_candidate_id(workplace)
    selector = ("--candidate", candidate)
    update(workplace, "stage", *selector)
    (package / "package.yaml").unlink()
    package.rmdir()
    update(workplace, "apply", *selector, "--confirm")

    runtime = workplace / "runtime/update"
    staged = runtime / "staged" / candidate / "stage-record.yaml"
    applied = runtime / "applied" / candidate / "apply-record.yaml"
    preimage = runtime / "backups" / candidate / "installed-subject.yaml"
    saved_stage = staged.read_bytes()
    saved_registry = registry.read_bytes()
    saved_payload = (package / "package.yaml").read_bytes()
    metadata = yaml.safe_load(preimage.read_text(encoding="utf-8"))
    assert metadata["payload_existed"] is False
    metadata.pop("payload_kind")
    write_record(preimage, metadata)
    receipt = yaml.safe_load(applied.read_text(encoding="utf-8"))
    receipt.pop("previous_version")
    receipt.pop("previous_subject_present")
    write_record(applied, receipt)

    staged.unlink()
    update(
        workplace,
        "rollback",
        *selector,
        refusal="package_rollback_payload_kind_missing",
    )
    assert registry.read_bytes() == saved_registry
    assert (package / "package.yaml").read_bytes() == saved_payload
    staged.write_bytes(saved_stage)
    update(workplace, "rollback", *selector)
    assert not package.exists()
    assert yaml.safe_load(registry.read_text(encoding="utf-8"))["subjects"] == before

    update(workplace, "apply", *selector, "--confirm")
    staged.unlink()
    update(workplace, "rollback", *selector)
    assert not package.exists()
    assert yaml.safe_load(registry.read_text(encoding="utf-8"))["subjects"] == before
    print("PASS: absent original payload and legacy type evidence")


def main() -> int:
    scratch = Path(
        os.environ.get("PF_TEST_SCRATCH_ROOT") or tempfile.gettempdir()
    ).resolve()
    with tempfile.TemporaryDirectory(prefix="pf-update-rollback-", dir=scratch) as raw:
        round_trip(Path(raw) / "directory", tool=False)
        round_trip(Path(raw) / "file", tool=True)
        check_initially_absent_package(Path(raw) / "absent")
        print("PASS: refresh, offline rollback, version-one records, refusals and repeat")
        return 0 if check_preview_and_verification(Path(raw)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
