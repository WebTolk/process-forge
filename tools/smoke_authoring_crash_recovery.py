#!/usr/bin/env python3
"""Permanent smoke for durable authoring crash recovery from persisted journals."""

from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def load_journal(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def crash_after_publish_rolls_back(processforge: object, root: Path) -> None:
    runtime = root / "runtime"
    existing = root / "authoritative" / "existing.txt"
    created = root / "authoritative" / "nested" / "created.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("before\n", encoding="utf-8")
    plan = processforge.AuthoringPlan(
        transaction_id="crash-after-publish",
        command="smoke-crash-recovery",
        runtime_root=runtime,
        authoritative_writes=[
            processforge.AuthoringWrite(existing, b"after\n", role="entity", allow_replace=True),
            processforge.AuthoringWrite(created, b"created\n", role="entity"),
        ],
        registry_writes=[],
        post_commit_effects=[],
        validation_callbacks=[],
    )
    journal, staged = processforge.stage_authoring_plan(plan)
    processforge.validate_staged_authoring_plan(plan, journal, staged)
    records = journal["writes"]
    processforge.publish_authoring_write(plan, plan.authoritative_writes[0], records[0], staged, journal)
    processforge.publish_authoring_write(plan, plan.authoritative_writes[1], records[1], staged, journal)
    journal_path = processforge.authoring_journal_path(plan)
    assert load_journal(journal_path)["state"] == "prepared"
    assert processforge.recover_authoring_transaction(journal_path, apply=False) == "prepared"
    assert processforge.recover_authoring_transaction(journal_path, apply=True) == "rolled_back"
    assert existing.read_text(encoding="utf-8") == "before\n"
    assert not created.exists(), "created file survived rollback recovery"
    assert not created.parent.exists(), "created directory survived rollback recovery"
    recovered = load_journal(journal_path)
    assert recovered["rollback_verified"] is True
    assert recovered["recovery_errors"] == []


def corrupted_backup_requires_manual_recovery(processforge: object, root: Path) -> None:
    runtime = root / "runtime"
    existing = root / "authoritative" / "corrupted.txt"
    existing.parent.mkdir(parents=True)
    existing.write_text("before\n", encoding="utf-8")
    plan = processforge.AuthoringPlan(
        transaction_id="corrupted-backup",
        command="smoke-crash-recovery",
        runtime_root=runtime,
        authoritative_writes=[
            processforge.AuthoringWrite(existing, b"after\n", role="entity", allow_replace=True),
        ],
        registry_writes=[],
        post_commit_effects=[],
        validation_callbacks=[],
    )
    journal, staged = processforge.stage_authoring_plan(plan)
    processforge.validate_staged_authoring_plan(plan, journal, staged)
    record = journal["writes"][0]
    processforge.publish_authoring_write(plan, plan.authoritative_writes[0], record, staged, journal)
    Path(record["backup_path"]).write_text("corrupt\n", encoding="utf-8")
    journal_path = processforge.authoring_journal_path(plan)
    assert processforge.recover_authoring_transaction(journal_path, apply=True) == "recovery_required"
    recovered = load_journal(journal_path)
    assert recovered["rollback_verified"] is False
    assert recovered["recovery_errors"], "corrupted backup recovery recorded no error"


def main() -> int:
    processforge = importlib.import_module("processforge")
    with tempfile.TemporaryDirectory(prefix="pf-authoring-crash-recovery-") as raw:
        base = Path(raw)
        crash_after_publish_rolls_back(processforge, base / "rollback")
        corrupted_backup_requires_manual_recovery(processforge, base / "corrupted")
    print("PASS: authoring crash-recovery smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
