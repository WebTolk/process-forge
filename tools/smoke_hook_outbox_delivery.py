#!/usr/bin/env python3
"""Verify public outbox dispatch, interrupted journal replay and older deliveries."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from platform import platform as platform_name
from platform import python_version
from typing import Any
from unittest.mock import patch

import yaml
from processforge_subprocess import diagnostic_text, run_command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.agents import hook_outbox  # noqa: E402
from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher  # noqa: E402


def pf(*args: str) -> str:
    result = run_command(
        [sys.executable, str(ROOT / "bin/pf.py"), *args], cwd=ROOT, timeout=120
    )
    assert result.returncode == 0, diagnostic_text(result)
    return result.stdout


def configure(project: Path, *targets: str) -> None:
    path = project / ".pf/hooks.yaml"
    config = yaml.safe_load(path.read_bytes())
    config["hooks"]["targets"] = [
        {
            "id": target,
            "type": "outbox",
            "enabled": True,
            "event_types": ["assignment.completed"],
        }
        for target in targets
    ]
    path.write_text(yaml.safe_dump(config), encoding="utf-8")


def verify(project: Path, receipt_path: Path, target: str) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_bytes())
    raw = (project / receipt["outbox"]).read_bytes()
    payload = json.loads(raw)
    assert receipt["target_id"] == target == payload["target_id"]
    assert receipt["event_id"] == payload["event"]["event_id"]
    assert receipt["delivery_id"] == payload["delivery_id"] == receipt_path.stem
    assert (
        receipt["status"] == "written"
        and receipt["payload_sha256"] == hashlib.sha256(raw).hexdigest()
    )
    return payload


def public_dispatch(project: Path) -> dict[str, Any]:
    targets = ("Build A", "build-a")
    configure(project, *targets)
    args = (
        "hooks-dispatch",
        "--project-root",
        str(project),
        "--event-type",
        "assignment.completed",
    )
    dry = pf(*args, "--dry-run")
    assert all(f"HOOK: {target} outbox dry_run" in dry for target in targets)
    assert "OUTBOX:" not in dry and "RESULT:" not in dry
    output = pf(*args, "--outbox")
    paths = [
        project / line.removeprefix("RESULT: ")
        for line in output.splitlines()
        if line.startswith("RESULT: ")
    ]
    assert len(paths) == len(set(paths)) == 2, output
    first, second = [
        verify(project, path, target)
        for path, target in zip(paths, targets, strict=True)
    ]
    assert first["event"] == second["event"]
    assert len({json.loads(path.read_bytes())["outbox"] for path in paths}) == 2
    # A competing body with the same identity cannot replace a healthy delivery.
    before = {path: path.read_bytes() for path in paths}
    for path in paths:
        payload = project / json.loads(before[path])["outbox"]
        before[payload] = payload.read_bytes()
    try:
        RuntimeHookDispatcher().dispatch_hooks(
            project, {**first["event"], "subject": "changed"}
        )
    except ValueError as error:
        assert str(error) == "outbox_delivery_conflict"
    else:
        raise AssertionError("accepted conflicting event")
    assert all(path.read_bytes() == value for path, value in before.items())
    return first["event"]


def replay_gap(workplace: Path, project: Path, event: dict[str, Any]) -> None:
    target = "Ack Gap"
    configure(project, target)
    results = project / ".pf/runtime/hooks/results"
    database = project / ".pf/runtime/events/events.sqlite3"
    # Restore the pending row for this actually admitted CLI event in the fixture.
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as sql, sql:
        added = sql.execute(
            "INSERT INTO pending_dispatch SELECT event_id, seq, ? FROM admissions WHERE event_id = ?",
            (json.dumps(event), event["event_id"]),
        )
        assert added.rowcount == 1
    receipt = results / f"{hook_outbox.delivery_key(event['event_id'], target)}.json"
    publish = hook_outbox.write_receipt
    captured: dict[Path, bytes] = {}

    def obstruct(path: Path, result: dict[str, Any]) -> Path:
        payload = project / result["outbox"]
        captured[payload] = payload.read_bytes()
        path.mkdir()
        return publish(path, result)  # Real native replacement of a directory fails.

    with patch.object(hook_outbox, "write_receipt", side_effect=obstruct):
        try:
            RuntimeHookDispatcher().dispatch_hooks(project, event)
        except OSError:
            assert receipt.is_dir() and captured
        else:
            raise AssertionError("receipt publication unexpectedly succeeded")
    receipt.rmdir()
    pf(
        "runtime-host",
        "tick",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--json",
    )
    assert verify(project, receipt, target)["event"] == event
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as sql:
        assert not sql.execute(
            "SELECT 1 FROM pending_dispatch WHERE event_id=?", (event["event_id"],)
        ).fetchone()
    assert all(path.read_bytes() == raw for path, raw in captured.items())


def legacy_and_concurrent(project: Path, event: dict[str, Any]) -> None:
    hooks = project / ".pf/runtime/hooks"
    old_key = (
        "del_"
        + hashlib.sha256((event["event_id"] + ":blue-a").encode()).hexdigest()[:32]
    )
    path = hooks / "outbox" / f"{event['event_id']}.blue-a.json"
    receipt = hooks / "results" / f"{old_key}.json"
    old = {
        "schema_version": 1,
        "delivery_id": old_key,
        "target_id": "Blue A",
        "event": event,
        "mode": "outbox",
        "delivery_time": "2026-01-01T00:00:00Z",
    }
    original = (json.dumps(old) + "\r\n").encode()
    path.write_bytes(original)
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "delivery_id": old_key,
                "target_id": "blue-a",
                "status": "written",
                "exit_code": 0,
                "blocking": False,
                "message": "Outbox payload written",
                "outbox": path.relative_to(project).as_posix(),
            }
        ),
        encoding="utf-8",
    )
    configure(project, "blue-a", "Blue A")
    other, legacy = RuntimeHookDispatcher().dispatch_hooks(project, event)
    assert (
        legacy["delivery_id"] == old_key and verify(project, receipt, "Blue A") == old
    )
    verify(project, project / other["result"], "blue-a")
    assert other["outbox"] != legacy["outbox"] and path.read_bytes() == original

    configure(project, "WTAICC Side", "wtaicc-side")
    wtaicc = hooks / "outbox/wtaicc"
    wtaicc.mkdir(exist_ok=True)
    historical = wtaicc / f"{event['event_id']}.wtaicc-side.json"
    old_key = (
        "del_"
        + hashlib.sha256((event["event_id"] + ":wtaicc-side").encode()).hexdigest()[:32]
    )
    historical.write_text(
        json.dumps({"target": "wtaicc", "created_at": "old", "event": event}),
        encoding="utf-8",
    )
    old_receipt = hooks / "results" / f"{old_key}.json"
    old_receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "written",
                "delivery_id": old_key,
                "target_id": "wtaicc-side",
                "outbox": historical.relative_to(project).as_posix(),
            }
        ),
        encoding="utf-8",
    )
    before = historical.read_bytes(), old_receipt.read_bytes()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(RuntimeHookDispatcher().dispatch_hooks, project, event)
            for _ in range(4)
        ]
        rows = [f.result() for f in futures]
    assert all(row == rows[0] for row in rows)
    assert len({action["outbox"] for action in rows[0]}) == 2
    for action in rows[0]:
        payload = verify(project, project / action["result"], action["target_id"])
        assert payload["target"] == "wtaicc" and payload["chat"]["included"] is False
    assert (historical.read_bytes(), old_receipt.read_bytes()) == before


def main() -> None:
    with tempfile.TemporaryDirectory(
        dir=os.environ.get("PF_TEST_SCRATCH_ROOT")
    ) as directory:
        root = Path(directory).resolve()
        workplace, project = root / "workplace", root / "outbox"
        project.mkdir()
        pf("workplace-init", "--workplace", str(workplace), "--apply")
        pf(
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic-software-project",
            "--apply",
        )
        event = public_dispatch(project)
        replay_gap(workplace, project, event)
        legacy_and_concurrent(project, event)
    print(
        f"PASS: outbox dispatch, interrupted replay, legacy and concurrent targets on {platform_name()}, Python {python_version()}"
    )


if __name__ == "__main__":
    main()
