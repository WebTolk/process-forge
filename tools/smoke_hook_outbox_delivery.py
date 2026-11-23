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

import yaml
from processforge_subprocess import diagnostic_text, run_command

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pf_runtime.host import normalize_event  # noqa: E402

from processforge_core.agents import hook_outbox  # noqa: E402
from processforge_core.agents.hook_dispatch import RuntimeHookDispatcher  # noqa: E402
from processforge_core.agents.process_events import ProcessEventRecorder  # noqa: E402
from processforge_core.common import ids  # noqa: E402


def pf(*args: str) -> str:
    result = run_command(
        [sys.executable, str(ROOT / "bin/pf.py"), *args], cwd=ROOT, timeout=120
    )
    assert result.returncode == 0, diagnostic_text(result)
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
            primary.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "delivery_id": key,
                        "target_id": "build-a",
                        "status": "written",
                        "outbox": first_path.relative_to(project).as_posix(),
                    }
                ),
                encoding="utf-8",
            )
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
        replay_gap(workplace, project)
        runtime_correlations(project)
        interrupted_v1(workplace, project, event)
        separate_v1_targets(workplace, project, event)
        legacy_and_concurrent(project, event)
    print(
        f"PASS: outbox dispatch, interrupted replay, legacy and concurrent targets on {platform_name()}, Python {python_version()}"
    )


if __name__ == "__main__":
    main()
