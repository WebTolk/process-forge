#!/usr/bin/env python3
"""Failure-injection regression for transactional platform/knowledge authoring."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"
sys.path.insert(0, str(ROOT / "tools"))


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def fingerprint(root: Path, *, exclude_transactions: bool = True) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if exclude_transactions and "/authoring-transactions/" in f"/{relative}":
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def init_workplace(path: Path) -> None:
    result = run("workplace-init", "--workplace", str(path), "--apply")
    assert result.returncode == 0, result.stdout + result.stderr


def test_modes(root: Path) -> None:
    workplace = root / "modes-workplace"
    init_workplace(workplace)
    before = fingerprint(workplace)
    missing = run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "missing-mode",
        "--title",
        "Missing Mode",
    )
    assert missing.returncode != 0, missing.stdout
    assert fingerprint(workplace) == before, "missing mode mutated workplace"
    both = run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "ambiguous",
        "--title",
        "Ambiguous",
        "--dry-run",
        "--apply",
    )
    assert both.returncode != 0
    assert fingerprint(workplace) == before, "ambiguous mode mutated workplace"
    explicit = run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "explicit",
        "--title",
        "Explicit",
        "--dry-run",
    )
    assert explicit.returncode == 0, explicit.stdout
    assert fingerprint(workplace) == before, "explicit dry-run mutated workplace"
    legacy_alias = run(
        "platform-create",
        "--workplace",
        str(workplace),
        "--id",
        "legacy-alias",
        "--title",
        "Legacy Alias",
        "--package",
        "docs.example-legacy",
        "--dry-run",
    )
    assert legacy_alias.returncode != 0, "platform-create accepted deprecated --package alias"


def test_knowledge_parent_failure(root: Path) -> None:
    workplace = root / "knowledge-workplace"
    init_workplace(workplace)
    created = run(
        "knowledge-package-create",
        "--workplace",
        str(workplace),
        "--id",
        "docs.atomic",
        "--title",
        "Atomic docs",
        "--package-root",
        "global",
        "--apply",
    )
    assert created.returncode == 0, created.stdout
    package = workplace / "packages" / "docs.atomic"
    index_dir = package / "indexes"
    for child in index_dir.iterdir():
        child.unlink()
    index_dir.rmdir()
    index_dir.write_text("parent collision\n", encoding="utf-8")
    resource = root / "private-resource.yaml"
    resource.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": "private-docs",
                "kind": "documentation",
                "title": "Private docs",
                "path": str(root / "private-docs"),
                "load_policy": "on_demand",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    before = fingerprint(workplace)
    result = run(
        "knowledge-add-resource",
        "--workplace",
        str(workplace),
        "--package",
        "docs.atomic",
        "--package-root",
        "global",
        "--resource-file",
        str(resource),
        "--apply",
    )
    assert result.returncode != 0, result.stdout
    assert fingerprint(workplace) == before, "knowledge preflight failure mutated authoritative/audit state"


def test_injected_platform_rollback(root: Path) -> None:
    processforge = importlib.import_module("processforge")
    assert hasattr(processforge, "AUTHORING_FAILURE_INJECTOR")
    workplace = root / "platform-workplace"
    init_workplace(workplace)
    before = fingerprint(workplace)

    def inject(phase: str, _plan: object, _write: object | None = None) -> None:
        if phase == "after_entity_publish:1":
            raise RuntimeError("injected platform failure")

    processforge.AUTHORING_FAILURE_INJECTOR = inject
    try:
        args = processforge.build_parser().parse_args(
            [
                "platform-create",
                "--workplace",
                str(workplace),
                "--id",
                "rollback",
                "--title",
                "Rollback",
                "--apply",
            ]
        )
        try:
            args.func(args)
        except (RuntimeError, SystemExit):
            pass
        else:
            raise AssertionError("injected platform failure returned success")
    finally:
        processforge.AUTHORING_FAILURE_INJECTOR = None
    assert fingerprint(workplace) == before, "platform rollback did not restore exact state"
    registry = yaml.safe_load((workplace / "registries" / "platforms.yaml").read_text(encoding="utf-8"))
    assert not any(item.get("id") == "rollback" for item in registry.get("platforms", []))


def test_platform_staged_semantics(root: Path) -> None:
    processforge = importlib.import_module("processforge")
    workplace = root / "platform-semantics-workplace"
    init_workplace(workplace)
    before = fingerprint(workplace)
    original = processforge.platform_contract_from_values

    def with_missing_parent(values: dict) -> dict:
        contract = original(values)
        contract.setdefault("requires", {})["platforms"] = [
            {"id": "platform.missing-parent", "required": True}
        ]
        return contract

    processforge.platform_contract_from_values = with_missing_parent
    try:
        args = processforge.build_parser().parse_args(
            [
                "platform-create",
                "--workplace",
                str(workplace),
                "--id",
                "semantic",
                "--title",
                "Semantic",
                "--apply",
            ]
        )
        try:
            args.func(args)
        except SystemExit:
            pass
        else:
            raise AssertionError("schema-valid platform with missing parent was committed")
    finally:
        processforge.platform_contract_from_values = original
    assert fingerprint(workplace) == before, "staged semantic failure mutated workplace"


def test_post_commit_replay(root: Path) -> None:
    processforge = importlib.import_module("processforge")
    workplace = root / "post-commit-workplace"
    init_workplace(workplace)
    original_append = processforge.append_workplace_resource_event
    calls = {"count": 0}

    def flaky_append(workplace_root: Path, event: dict) -> Path:
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("injected audit failure")
        return original_append(workplace_root, event)

    transaction_id = "platform-audit-replay"
    effect_payload = {
        "workplace_root": str(workplace),
        "command": "platform-create",
        "contract_id": "platform.example-replay",
        "proposal_payload": {"transaction_id": transaction_id, "platform": "platform.example-replay"},
        "events": [
            {
                "event_type": "platform.contract.created",
                "status": "created",
                "message": "created",
                "target": {"platform": "platform.example-replay", "transaction_id": transaction_id},
            },
            {
                "event_type": "platform.authoring.completed",
                "status": "completed",
                "message": "completed",
                "target": {"platform": "platform.example-replay", "transaction_id": transaction_id},
            },
        ],
    }
    plan = processforge.AuthoringPlan(
        transaction_id=transaction_id,
        command="platform-create",
        runtime_root=workplace / "runtime",
        authoritative_writes=[],
        registry_writes=[],
        post_commit_effects=[
            processforge.AuthoringEffect(
                "platform-audit-events",
                "runtime/resource-management/proposals/<transaction>.yaml and runtime/events/events.ndjson",
                kind="platform_audit",
                payload=effect_payload,
            )
        ],
        validation_callbacks=[],
    )
    processforge.append_workplace_resource_event = flaky_append
    try:
        try:
            processforge.execute_authoring_plan(plan)
        except RuntimeError:
            pass
        else:
            raise AssertionError("post-commit failure returned success")
    finally:
        processforge.append_workplace_resource_event = original_append
    journal_path = workplace / "runtime" / "authoring-transactions" / transaction_id / "journal.yaml"
    journal = yaml.safe_load(journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "committed_audit_pending"
    state = processforge.recover_authoring_transaction(journal_path, apply=True)
    assert state == "committed_audit_complete"
    events_path = workplace / "runtime" / "events" / "events.ndjson"
    event_ids = [
        json.loads(line)["event_id"]
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(event_ids) == len(set(event_ids)), "post-commit replay duplicated event ids"


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pf-remediation-transactional-") as raw:
        root = Path(raw)
        for name, test in [
            ("modes", test_modes),
            ("knowledge-parent-failure", test_knowledge_parent_failure),
            ("platform-injected-rollback", test_injected_platform_rollback),
            ("platform-staged-semantics", test_platform_staged_semantics),
            ("post-commit-replay", test_post_commit_replay),
        ]:
            try:
                test(root)
            except Exception as exc:
                failures.append(f"{name}: {exc}")
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1
    print("PASS: transactional platform/knowledge authoring smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
