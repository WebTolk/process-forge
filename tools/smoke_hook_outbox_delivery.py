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

from pf_runtime.host import normalize_event  # noqa: E402

from processforge_core.agents import hook_outbox  # noqa: E402
from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher  # noqa: E402
from processforge_core.agents.process_events import (  # noqa: E402
    PendingDispatchError,
    ProcessEventRecorder,
)
from processforge_core.common import ids  # noqa: E402


def pf(*args: str, expect: int = 0) -> str:
    result = run_command(
        [sys.executable, str(ROOT / "bin/pf.py"), *args], cwd=ROOT, timeout=120
    )
    assert result.returncode == expect, diagnostic_text(result)
    return result.stdout


def configure(
    project: Path, *targets: str, overrides: dict[str, dict[str, Any]] | None = None
) -> None:
    path = project / ".pf/hooks.yaml"
    config = yaml.safe_load(path.read_bytes())
    config["hooks"]["targets"] = [
        {
            "id": target,
            "type": "outbox",
            "enabled": True,
            "event_types": ["assignment.completed"],
            **(overrides or {}).get(target, {}),
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
    assert receipt["delivery_id"] == receipt_path.stem
    assert (
        receipt.get("payload_delivery_id", receipt["delivery_id"])
        == payload["delivery_id"]
    )
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


def replay_gap(workplace: Path, project: Path) -> None:
    target = "Ack Gap"
    other = "Disabled Gap"
    configure(project, target, other)
    results = project / ".pf/runtime/hooks/results"
    database = project / ".pf/runtime/events/events.sqlite3"
    # Remove only the receipt volume from this disposable consumer. Reading a
    # missing receipt returns ENOENT; publishing it after the envelope fails.
    saved = results.with_name("saved-results")
    volume = results.with_name("fixture-volume")
    results.rename(saved)
    volume.mkdir()
    if os.name == "nt":
        linked = run_command(
            ["cmd", "/d", "/c", "mklink", "/J", results.name, volume.name],
            cwd=results.parent,
            timeout=20,
        )
        assert linked.returncode == 0, diagnostic_text(linked)
    else:
        results.symlink_to(volume, target_is_directory=True)
    volume.rmdir()
    failed = run_command(
        [
            sys.executable,
            str(ROOT / "bin/pf.py"),
            "hooks-dispatch",
            "--project-root",
            str(project),
            "--event-type",
            "assignment.completed",
            "--outbox",
        ],
        cwd=ROOT,
        timeout=120,
    )
    if os.name == "nt":
        results.rmdir()
    else:
        results.unlink()
    saved.rename(results)
    assert failed.returncode != 0
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as sql:
        pending = sql.execute("SELECT record FROM pending_dispatch").fetchall()
    assert len(pending) == 1, diagnostic_text(failed)
    event, targets = json.loads(pending[0][0])
    assert [route["id"] for route in targets] == [target, other]
    key = hook_outbox.delivery_key(event["event_id"], target)
    receipt = results / f"{key}.json"
    payload = project / f".pf/runtime/hooks/outbox/{key}.outbox.json"
    captured = payload.read_bytes()
    assert not receipt.exists() and json.loads(captured)["event"] == event
    configure(
        project,
        target,
        other,
        overrides={target: {"path": "changed-outbox"}, other: {"enabled": False}},
    )
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
    other_key = hook_outbox.delivery_key(event["event_id"], other)
    assert verify(project, results / f"{other_key}.json", other)["event"] == event
    assert not (project / ".pf/changed-outbox").exists()
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as sql:
        assert not sql.execute(
            "SELECT 1 FROM pending_dispatch WHERE event_id=?", (event["event_id"],)
        ).fetchone()
    assert payload.read_bytes() == captured


def unavailable_first_target(workplace: Path, project: Path) -> None:
    blocked = project / ".pf/blocked-route"
    healthy = project / ".pf/healthy-route"
    blocked.write_text("temporarily unavailable", encoding="utf-8")
    configure(
        project,
        "first",
        "second",
        overrides={"first": {"path": blocked.name}, "second": {"path": healthy.name}},
    )
    pf(
        "hooks-dispatch",
        "--project-root",
        str(project),
        "--event-type",
        "assignment.completed",
        "--outbox",
        expect=1,
    )
    (published,) = healthy.glob("*.json")
    original = published.read_bytes()
    event = json.loads(original)["event"]
    results = project / ".pf/runtime/hooks/results"
    second = results / (hook_outbox.delivery_key(event["event_id"], "second") + ".json")
    proof = second.read_bytes()
    assert verify(project, second, "second")["event"] == event
    tick = (
        "runtime-host",
        "tick",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--json",
    )
    outcome = json.loads(pf(*tick, expect=1))
    assert [
        failure["event_id"] for failure in outcome["projects"][0]["dispatch_failures"]
    ] == [event["event_id"]]
    blocked.unlink()
    pf(*tick)
    first = results / (hook_outbox.delivery_key(event["event_id"], "first") + ".json")
    assert verify(project, first, "first")["event"] == event
    assert list(healthy.glob("*.json")) == [published]
    assert published.read_bytes() == original and second.read_bytes() == proof
    journal = ProcessEventRecorder().event_journal_for_project(project, workplace)
    assert not journal.pending_dispatch(project / ".pf/runtime/events/events.sqlite3")


def check_conflict(project: Path, event: dict[str, Any], reason: str) -> None:
    try:
        RuntimeHookDispatcher().dispatch_hooks(project, event)
    except ValueError as error:
        assert str(error) == reason
    else:
        raise AssertionError(f"expected {reason}")


def runtime_correlations(project: Path) -> None:
    target = "Runtime correlations"
    configure(project, target)
    raw = {
        "event_type": "assignment.completed",
        "event_id": "evt_fallback",
        "payload": {"run_id": "payload-run"},
    }
    first = normalize_event(raw, project, ids)
    replay = normalize_event(raw, project, ids)
    assert first["correlation_id"] == replay["correlation_id"]
    dispatcher = RuntimeHookDispatcher()
    assert dispatcher.dispatch_hooks(project, first) == dispatcher.dispatch_hooks(
        project, replay
    )
    supplied = {
        **raw,
        "event_id": "evt_explicit",
        "correlation_id": "corr-111111111111",
    }
    event = normalize_event(supplied, project, ids)
    (action,) = dispatcher.dispatch_hooks(project, event)
    receipt = project / action["result"]
    original = receipt.read_bytes()
    assert (
        verify(project, receipt, target)["event"]["correlation_id"]
        == supplied["correlation_id"]
    )
    changed = normalize_event(
        {**supplied, "correlation_id": "corr-222222222222"}, project, ids
    )
    check_conflict(project, changed, "outbox_delivery_conflict")
    assert receipt.read_bytes() == original


def v1_file(
    directory: Path, target: str, event: dict[str, Any]
) -> tuple[Path, bytes, str]:
    event_id = event["event_id"]
    slug = ids.safe_id(target, "hook")
    key = "del_" + hashlib.sha256(f"{event_id}:{slug}".encode()).hexdigest()[:32]
    path = directory / f"{event_id}.{slug}.json"
    original = (
        json.dumps(
            {
                "schema_version": 1,
                "delivery_id": key,
                "target_id": target,
                "mode": "outbox",
                "delivery_time": "2026-01-01T00:00:00Z",
                "event": event,
            },
            ensure_ascii=False,
        ).encode()
        + b"\r\n"
    )
    directory.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original)
    return path, original, key


def chat_recovery(project: Path) -> None:
    target = "chat-recovery"
    configure(
        project, target, overrides={target: {"event_types": ["chat.message.recorded"]}}
    )
    dispatcher = RuntimeHookDispatcher()
    ref_path = ".pf/runtime/chat/transcripts/chat-recovery.ndjson"

    def chat_event(
        line: int,
        observation_time: str,
        *,
        event_id: str = "evt_chat_recovery",
        content_hash: str = "original",
        path: str = ref_path,
    ) -> dict[str, Any]:
        return {
            "source": "processforge.cli",
            "event_type": "chat.message.recorded",
            "event_id": event_id,
            "time": observation_time,
            "correlation_id": "chat-session",
            "data": {
                "message": {
                    "content_hash": content_hash,
                    "content_ref": {
                        "path": path,
                        "message_id": "message",
                        "line": line,
                    },
                }
            },
        }

    first_time = "2026-01-01T00:00:00Z"
    retry_time = "2026-01-01T00:01:00Z"
    (action,) = dispatcher.dispatch_hooks(project, chat_event(1, first_time))
    outbox, receipt = (project / action[key] for key in ("outbox", "result"))
    original_payload, original_receipt = outbox.read_bytes(), receipt.read_bytes()
    replay = chat_event(0, retry_time)
    assert dispatcher.dispatch_hooks(project, replay) == [action]
    assert outbox.read_bytes() == original_payload
    assert receipt.read_bytes() == original_receipt

    outbox.unlink()
    assert dispatcher.dispatch_hooks(project, replay) == [action]
    assert outbox.read_bytes() == original_payload
    assert receipt.read_bytes() == original_receipt
    assert len(list(outbox.parent.glob(f"{action['delivery_id']}.*"))) == 1
    verify(project, receipt, target)

    for conflict in (
        chat_event(2, retry_time),
        chat_event(0, retry_time, content_hash="changed"),
        chat_event(0, retry_time, path=ref_path + ".other"),
        {**replay, "correlation_id": "different-session"},
    ):
        check_conflict(project, conflict, "outbox_delivery_conflict")
    assert outbox.read_bytes() == original_payload
    assert receipt.read_bytes() == original_receipt

    outbox.unlink()
    older_receipt = json.loads(original_receipt)
    del older_receipt["runtime_observation"]
    older_bytes = json.dumps(older_receipt).encode("utf-8")
    receipt.write_bytes(older_bytes)
    check_conflict(project, replay, "outbox_receipt_payload_mismatch")
    assert not outbox.exists() and receipt.read_bytes() == older_bytes

    legacy = chat_event(0, first_time, event_id="evt_legacy_chat_recovery")
    legacy_path, legacy_bytes, legacy_id = v1_file(outbox.parent, target, legacy)
    v1_receipt(project, legacy_path, legacy_id, target)
    (recovered,) = dispatcher.dispatch_hooks(
        project, chat_event(1, retry_time, event_id=legacy["event_id"])
    )
    assert project / recovered["outbox"] == legacy_path
    assert legacy_path.read_bytes() == legacy_bytes
    verify(project, project / recovered["result"], target)


def replay_v1(workplace: Path, project: Path, event: dict[str, Any]) -> None:
    database = project / ".pf/runtime/events/events.sqlite3"
    journal = ProcessEventRecorder().event_journal_for_project(project, workplace)
    assert journal.append(database, event, queue_dispatch=True)
    pf(
        "runtime-host",
        "tick",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--json",
    )
    assert journal.pending_dispatch(database, event_id=event["event_id"]) == []


def v1_receipt(project: Path, path: Path, key: str, target: str) -> Path:
    receipt = project / ".pf/runtime/hooks/results" / f"{key}.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "delivery_id": key,
                "target_id": ids.safe_id(target, "hook"),
                "status": "written",
                "outbox": path.relative_to(project).as_posix(),
            }
        ),
        encoding="utf-8",
    )
    return receipt


def v1_platform_filename(
    workplace: Path, project: Path, original_event: dict[str, Any]
) -> None:
    target = "Build"
    event = {**original_event, "event_id": r"evt_batch\17"}
    configure(project, target)
    directory = project / ".pf/runtime/hooks/outbox"
    if os.name == "nt":
        replay_v1(workplace, project, event)
        key = hook_outbox.delivery_key(event["event_id"], target)
        receipt = project / ".pf/runtime/hooks/results" / f"{key}.json"
        assert verify(project, receipt, target)["event"] == event
        assert not (directory / "evt_batch").exists()
    else:
        path, original, key = v1_file(directory, target, event)
        receipt = v1_receipt(project, path, key, target)
        before = set(directory.glob("*.json"))
        replay_v1(workplace, project, event)
        assert verify(project, receipt, target)["event"] == event
        assert set(directory.glob("*.json")) == before and path.read_bytes() == original


def v1_independent_route(
    workplace: Path, project: Path, original_event: dict[str, Any]
) -> None:
    owner, other = "build-a", "Build A"
    event = {**original_event, "event_id": "evt_independent_legacy_routes"}
    routes = {owner: {"path": "owner-route"}, other: {"path": "other-route"}}
    owner_file, _, key = v1_file(project / ".pf/owner-route", owner, event)
    other_file, original, _ = v1_file(project / ".pf/other-route", other, event)
    configure(project, owner, overrides=routes)
    (first,) = RuntimeHookDispatcher().dispatch_hooks(project, event)
    assert first["delivery_id"] == key
    assert verify(project, project / first["result"], owner)["event"] == event
    configure(project, other, overrides=routes)

    database = project / ".pf/runtime/events/events.sqlite3"
    recorder = ProcessEventRecorder()
    journal = recorder.event_journal_for_project(project, workplace)
    assert journal.append(database, event, queue_dispatch=True)
    (pending,) = journal.pending_dispatch(database, event_id=event["event_id"])
    read_file = hook_outbox._read

    def read_without_owner(path: Path) -> bytes | None:
        if path == owner_file:
            raise PermissionError("sibling envelope is inaccessible")
        return read_file(path)

    with patch.object(hook_outbox, "_read", read_without_owner):
        recorder.deliver_pending_event(project, journal, database, pending)
    assert journal.pending_dispatch(database, event_id=event["event_id"]) == []
    receipt_key = hook_outbox.delivery_key(event["event_id"], other)
    receipt = project / ".pf/runtime/hooks/results" / f"{receipt_key}.json"
    assert verify(project, receipt, other)["event"] == event
    assert list(other_file.parent.glob("*.json")) == [other_file]
    assert other_file.read_bytes() == original


def interrupted_v1(
    workplace: Path, project: Path, original_event: dict[str, Any]
) -> None:
    target = "Legacy Gap"
    configure(project, target)
    hooks = project / ".pf/runtime/hooks"
    for number, torn in enumerate((None, b"", b'{"outbox":')):
        event = {**original_event, "event_id": f"evt_журнал gap{number}"}
        path, first, key = v1_file(hooks / "outbox", target, event)
        historical = hooks / "results" / f"{key}.json"
        before = set(path.parent.glob("*.json"))
        assert not historical.exists()
        if torn is not None:
            historical.write_bytes(torn)
        replay_v1(workplace, project, event)
        receipt = historical
        if torn is not None:
            current = hook_outbox.delivery_key(event["event_id"], target)
            receipt = historical.with_name(f"{current}.json")
        assert verify(project, receipt, target)["event"] == event
        proof = receipt.read_bytes()
        (action,) = RuntimeHookDispatcher().dispatch_hooks(project, event)
        assert project / action["result"] == receipt and receipt.read_bytes() == proof
        assert project / action["outbox"] == path
        assert set(path.parent.glob("*.json")) == before and path.read_bytes() == first
        if torn is None:
            assert receipt == historical
        else:
            assert receipt != historical and historical.read_bytes() == torn


def separate_v1_targets(
    workplace: Path, project: Path, original_event: dict[str, Any]
) -> None:
    targets = ("Build A", "build-a")
    routes = {
        target: {"path": f"legacy-{index}"} for index, target in enumerate(targets)
    }
    results = project / ".pf/runtime/hooks/results"
    for case in ("first", "second", "unclaimed"):
        event = {**original_event, "event_id": f"evt_legacy_routes_{case}"}
        files = {
            target: v1_file(project / ".pf" / routes[target]["path"], target, event)
            for target in targets
        }
        first_path, _, key = files[targets[0]]
        primary = results / f"{key}.json"
        if case != "unclaimed":
            v1_receipt(project, first_path, key, targets[0])
        order = targets if case == "first" else targets[::-1]
        configure(project, *order, overrides=routes)
        before = {
            t: set(path.parent.glob("*.json")) for t, (path, _, _) in files.items()
        }
        dispatcher = RuntimeHookDispatcher()
        if case == "unclaimed":
            # Independent publishers can race to claim the single historical receipt.
            selected = dispatcher.policy.selected_hooks(project, event)
            with ThreadPoolExecutor(max_workers=2) as executor:
                pending = [
                    executor.submit(
                        dispatcher.dispatch_hooks, project, event, targets=[target]
                    )
                    for target in selected
                ]
                for future in pending:
                    future.result()
        replay_v1(workplace, project, event)
        owner = json.loads(primary.read_bytes())["target_id"]
        assert owner in targets and (case == "unclaimed" or owner == targets[0])
        proofs = {}
        for target in targets:
            receipt = (
                primary
                if target == owner
                else results
                / (hook_outbox.delivery_key(event["event_id"], target) + ".json")
            )
            path, original, _ = files[target]
            assert verify(project, receipt, target)["delivery_id"] == key
            assert project / json.loads(receipt.read_bytes())["outbox"] == path
            assert path.read_bytes() == original
            assert set(path.parent.glob("*.json")) == before[target]
            proofs[receipt] = receipt.read_bytes()
        actions = dispatcher.dispatch_hooks(project, event)
        assert {project / a["result"] for a in actions} == set(proofs)
        assert all(path.read_bytes() == proof for path, proof in proofs.items())
        if case == "second":
            alias = next(a for a in actions if project / a["result"] != primary)
            configure(
                project,
                alias["target_id"],
                overrides={alias["target_id"]: {"path": "moved"}},
            )
            check_conflict(project, event, "outbox_delivery_route_conflict")
            configure(project, alias["target_id"], overrides=routes)
            check_conflict(
                project, {**event, "subject": "changed"}, "outbox_delivery_conflict"
            )
            assert not (project / ".pf/moved").exists()


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
    configure(project, "Blue A", overrides={"Blue A": {"path": "changed-outbox"}})
    prior = receipt.read_bytes()
    check_conflict(project, event, "outbox_delivery_route_conflict")
    assert receipt.read_bytes() == prior and path.read_bytes() == original
    assert not (project / ".pf/changed-outbox").exists()
    configure(project, "blue-a", "Blue A")
    other, legacy = RuntimeHookDispatcher().dispatch_hooks(project, event)
    assert (
        legacy["delivery_id"] == old_key and verify(project, receipt, "Blue A") == old
    )
    verify(project, project / other["result"], "blue-a")
    assert other["outbox"] != legacy["outbox"] and path.read_bytes() == original
    configure(project, "Blue A")
    proof = receipt.read_bytes()
    check_conflict(project, {**event, "subject": "changed"}, "outbox_delivery_conflict")
    assert receipt.read_bytes() == proof and path.read_bytes() == original

    configure(project, "typed")
    typed = {**event, "data": {"value": True}}
    (action,) = RuntimeHookDispatcher().dispatch_hooks(project, typed)
    typed_receipt = project / action["result"]
    proof = typed_receipt.read_bytes()
    check_conflict(project, {**typed, "data": {"value": 1}}, "outbox_delivery_conflict")
    configure(project, "typed", overrides={"typed": {"path": "changed-outbox"}})
    check_conflict(project, typed, "outbox_delivery_route_conflict")
    assert (
        typed_receipt.read_bytes() == proof
        and not (project / ".pf/changed-outbox").exists()
    )

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


def independent_pending_rows(
    workplace: Path, project: Path, original_event: dict[str, Any]
) -> None:
    target = "Retry"
    configure(project, target)
    database = project / ".pf/runtime/events/events.sqlite3"
    recorder = ProcessEventRecorder()
    journal = recorder.event_journal_for_project(project, workplace)
    blocked = [
        {
            **original_event,
            "event_id": f"evt_retired_{i}",
            "event_type": "retired.event",
        }
        for i in range(3)
    ]
    assert journal.append_many(database, blocked, queue_dispatch=True) == 3
    healthy = {**original_event, "event_id": "evt_healthy_retry"}
    routes = recorder.delivery_targets(project, healthy)
    inserted, pending = journal.append_for_dispatch(
        database,
        healthy,
        event_id_value=recorder.hooks.event_id_value,
        record=True,
        queue_dispatch=True,
        dispatch_targets=routes,
    )
    assert inserted and pending == [healthy]
    with patch.object(
        hook_outbox, "write_receipt", side_effect=PermissionError("receipt offline")
    ):
        try:
            recorder.deliver_pending_event(project, journal, database, healthy)
        except PermissionError:
            pass
        else:
            raise AssertionError("expected interrupted receipt")
    key = hook_outbox.delivery_key(healthy["event_id"], target)
    root = project / ".pf/runtime/hooks"
    payload = root / "outbox" / f"{key}.outbox.json"
    receipt = root / "results" / f"{key}.json"
    original = payload.read_bytes()
    assert not receipt.exists()
    reason = "journal_legacy_dispatch_targets_unknown"
    for expected in (blocked[:2], blocked[2:]):
        try:
            recorder.flush_pending_dispatches(project, journal, database, limit=2)
        except PendingDispatchError as error:
            assert error.failures == [
                {"event_id": e["event_id"], "reason": reason} for e in expected
            ]
        else:
            raise AssertionError("unresolved routes must remain visible")
    assert verify(project, receipt, target)["event"] == healthy
    assert payload.read_bytes() == original
    assert journal.pending_dispatch(database) == blocked

    later = {**healthy, "event_id": "evt_runtime_healthy_retry"}
    assert journal.append(database, later, queue_dispatch=True)
    # The completed scan revisits its oldest pending rows despite this new arrival.
    assert journal.next_dispatch_batch(database, limit=2) == [
        event["event_id"] for event in blocked[:2]
    ]
    tick = (
        "runtime-host",
        "tick",
        "--workplace",
        str(workplace),
        "--project-root",
        str(project),
        "--json",
    )
    outcome = json.loads(pf(*tick, expect=1))
    assert outcome["projects"][0]["dispatch_failures"] == [
        {"event_id": event["event_id"], "reason": reason} for event in blocked
    ]
    later_key = hook_outbox.delivery_key(later["event_id"], target)
    assert (
        verify(project, root / "results" / f"{later_key}.json", target)["event"]
        == later
    )
    assert journal.pending_dispatch(database) == blocked
    configure(project, target, overrides={target: {"event_types": ["retired.event"]}})
    pf(*tick)
    assert journal.pending_dispatch(database) == []


def read_during_windows_rename(root: Path) -> None:
    if os.name != "nt":
        return
    import _winapi

    path = root / "published.json"
    path.write_bytes(b"first delivery")
    # Hold DELETE access exactly as an overlapping Windows rename can do.
    handle = _winapi.CreateFile(str(path), 0x10000, 7, 0, _winapi.OPEN_EXISTING, 0, 0)
    try:
        assert hook_outbox._read(path) == b"first delivery"
    finally:
        _winapi.CloseHandle(handle)


def main() -> None:
    with tempfile.TemporaryDirectory(
        dir=os.environ.get("PF_TEST_SCRATCH_ROOT")
    ) as directory:
        root = Path(directory).resolve()
        read_during_windows_rename(root)
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
        replay_gap(workplace, project)
        unavailable_first_target(workplace, project)
        runtime_correlations(project)
        chat_recovery(project)
        interrupted_v1(workplace, project, event)
        separate_v1_targets(workplace, project, event)
        v1_platform_filename(workplace, project, event)
        v1_independent_route(workplace, project, event)
        legacy_and_concurrent(project, event)
        independent_pending_rows(workplace, project, event)
    print(
        f"PASS: outbox dispatch, interrupted replay, legacy and concurrent targets on {platform_name()}, Python {python_version()}"
    )


if __name__ == "__main__":
    main()
