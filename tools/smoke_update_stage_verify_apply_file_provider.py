#!/usr/bin/env python3
"""Exercise package rollback by applied ID through the public CLI."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml
from update_smoke_helpers import (
    first_candidate_id,
    make_update_fixture,
    require_ok,
    run_pf,
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
    update(workplace, "verify", *selector)
    update(workplace, "apply", *selector, refusal="--confirm")
    update(workplace, "apply", *selector, "--confirm")
    applied_payload = payload.read_bytes()
    installed = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert applied_payload != original_payload
    assert installed["subjects"][0]["version"] == "1.1.0"
    installed["subjects"][1]["version"] = "8.1.0"
    write_record(registry, installed)

    runtime = workplace / "runtime/update"
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

    applied = runtime / "applied" / candidate / "apply-record.yaml"
    backup_dir = runtime / "backups" / candidate
    preimage = backup_dir / "installed-subject.yaml"
    original_receipt = applied.read_bytes()
    metadata = yaml.safe_load(preimage.read_text(encoding="utf-8"))
    assert metadata["payload_kind"] == ("file" if tool else "tree")

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
    (runtime / "staged" / candidate / "stage-record.yaml").unlink()
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
