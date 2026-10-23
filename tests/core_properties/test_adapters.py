"""Use real adapters with a canonical owner; no obsolete release-constant fakes."""

from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("change", ["update", "malformed", "missing"])
def test_cli_mcp_and_action_catalogue_consume_loaded_owner(
    adapters, capsys, write_distribution, change
):
    a = adapters
    original = a.properties.loaded
    assert a.runtime.properties is a.properties
    if change == "update":
        write_distribution(a.root, "8.3.2-dev.8+new")
    elif change == "malformed":
        (a.root / "VERSION").write_bytes(b"PRIVATE_CANARY")
    else:
        (a.root / "VERSION").unlink()
    assert a.properties.loaded is original
    assert a.cli.main(["version"]) == 0
    assert capsys.readouterr().out == (
        f"ProcessForge {original.version}\nSpec: 1.0\nSchema bundle: 1.0\n"
    )
    assert (
        a.cli.main(["actions", "list", "--surface", "mcp", "--limit", "1", "--json"])
        == 0
    )
    cli_catalogue = json.loads(capsys.readouterr().out)
    assert cli_catalogue["provenance"]["version"] == original.version
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    a.factory.reset_mock()
    response = a.mcp.respond_valid(request, a.workplace, "", a.runtime)
    a.factory.assert_called_once_with()
    assert response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "processforge", "version": original.version},
            "capabilities": {"tools": {}},
        },
    }
    a.factory.reset_mock()
    catalogue = a.mcp.tool_result(
        "pf.actions.list",
        {"project_root": str(a.project), "surface": "mcp", "limit": 1},
        a.workplace,
        "",
        a.runtime,
    )
    a.factory.assert_called_once_with()
    assert catalogue["provenance"]["version"] == original.version
    assert catalogue.keys() == cli_catalogue.keys()
    assert catalogue["actions"] == cli_catalogue["actions"]
    for payload in (catalogue, response):
        text = json.dumps(payload)
        assert str(a.root) not in text and "PRIVATE_CANARY" not in text


def test_runtime_host_and_console_preserve_loaded_identity(
    adapters, monkeypatch, write_distribution
):
    a = adapters
    write_distribution(a.root, "8.3.2-dev.8+new")
    a.factory.reset_mock()
    # The core argument deliberately has no release-version attribute.
    state = a.service.base_state(
        a.workplace, object(), status="ready", pid=123, instance_id="fixture"
    )
    a.factory.assert_called_once_with()
    assert state["processforge_core_version"] == a.properties.loaded.version
    assert state["runtime_version"] == a.service.RUNTIME_VERSION
    assert state["protocol_version"] == a.service.RUNTIME_PROTOCOL_VERSION
    assert state["runtime_version"] == "1.0.0-poc"
    assert state["protocol_version"] == "pf-runtime-poc-1"
    assert state["schema_version"] == 2
    assert state["core_identity"]["loaded"] == a.properties.loaded.record()
    assert state["runtime_version"] != state["processforge_core_version"]
    a.factory.reset_mock()
    host_state = a.host.load_state(a.workplace)
    original_keys = host_state.keys() | {
        "updated_at",
        "workplace_root",
        "processforge_core_version",
        "core_identity",
    }
    a.host.save_state(a.workplace, host_state, object())
    a.factory.assert_called_once_with()
    written = json.loads(a.host.state_path(a.workplace).read_bytes())
    assert written["processforge_core_version"] == a.properties.loaded.version
    assert written["schema_version"] == 2
    assert written["core_identity"]["loaded"] == a.properties.loaded.record()
    assert written["runtime_protocol_version"] == a.service.RUNTIME_PROTOCOL_VERSION
    assert written.keys() == original_keys
    from pf_runtime import console

    show = Mock()
    process = Mock()
    process.return_value.serve.return_value = 17
    monkeypatch.setattr(console, "show_server_console", show)
    monkeypatch.setattr(a.service, "RuntimeProcess", process)
    core = SimpleNamespace(resolve_workplace_root=lambda value: a.workplace)
    args = argparse.Namespace(workplace="fixture", port=123, interval=3, minimized=True)
    assert a.service.command_serve(args, core) == 17
    show.assert_called_once_with(a.properties.loaded.version, minimized=True)
    process.return_value.serve.assert_called_once_with(123)


@pytest.mark.parametrize(
    "change", ["update", "malformed", "missing", "same-label-build"]
)
def test_runtime_truth_observes_disk_without_rewriting_loaded_fields(
    adapters, write_distribution, change
):
    a = adapters
    state = a.service.base_state(a.workplace, object(), status="ready")
    loaded = a.properties.loaded
    if change == "update":
        write_distribution(a.root, "8.0.1+updated")
    elif change == "same-label-build":
        write_distribution(a.root, generated_at="2025-02-03T04:05:06Z")
        assert a.properties.installed().build_id != loaded.build_id
    elif change == "malformed":
        (a.root / "VERSION").write_bytes(b"malformed")
    else:
        (a.root / "VERSION").unlink()
    keys = state.keys() | {"installed_pf", "runtime", "last_runtime_instance"}
    a.factory.reset_mock()
    payload = a.service.add_runtime_truth(state, object(), running=True)
    a.factory.assert_called_once_with()
    assert payload.keys() == keys
    assert payload["processforge_core_version"] == loaded.version
    assert payload["core_identity"]["loaded"] == loaded.record()
    assert payload["core_identity"]["installed"] == a.properties.installed().record()
    if change in {"update", "same-label-build"}:
        assert payload["core_identity"]["status"] == "reload_required"
        assert payload["core_identity"]["required_action"] == "restart"
    else:
        assert payload["core_identity"]["status"] == "unknown"
    assert payload["installed_pf"] == {"version": a.properties.installed().version}
    assert payload["runtime"] == {"running": True, "status": "ready", "health": "ready"}
    assert payload["last_runtime_instance"] == {
        "version": a.service.RUNTIME_VERSION,
        "status": "current",
    }


@pytest.mark.parametrize(
    ("active", "running_version", "disk_change", "expected"),
    [
        (True, "loaded", "none", "PASS"),
        (True, "loaded", "update", "FAIL"),
        (True, "installed", "update", "PASS"),
        (True, "unknown", "missing", "FAIL"),
        (False, "unknown", "missing", "PASS"),
    ],
)
def test_doctor_compares_active_instance_to_live_disk(
    adapters,
    monkeypatch,
    write_distribution,
    active,
    running_version,
    disk_change,
    expected,
):
    a = adapters
    if disk_change == "update":
        write_distribution(a.root, "8.0.1+updated")
    elif disk_change == "missing":
        (a.root / "VERSION").unlink()
    selected = {
        "loaded": a.properties.loaded.version,
        "installed": a.properties.installed().version,
        "unknown": "unknown",
    }[running_version]
    state = {
        "processforge_core_version": selected,
        "protocol_version": a.service.RUNTIME_PROTOCOL_VERSION,
    }
    monkeypatch.setattr(a.service, "active_service", lambda *args: (active, state))
    monkeypatch.setattr(a.service, "status_payload", lambda *args: {"health": "ready"})
    checks = []
    core = SimpleNamespace(
        resolve_workplace_root=lambda value: a.workplace,
        check=lambda status, message: (status, message),
        print_checks=lambda values: checks.extend(values) or 0,
    )
    a.factory.reset_mock()
    assert a.service.command_doctor(argparse.Namespace(workplace="fixture"), core) == 0
    a.factory.assert_called_once_with()
    assert (expected, "runtime core version compatible") in checks
    assert ("PASS", "runtime protocol version compatible") in checks


def test_real_monitor_collects_loaded_cli_version(
    adapters, monkeypatch, write_distribution
):
    a = adapters
    write_distribution(a.root, "8.0.1+updated")
    snapshots = []

    def observe(collect, args, **streams):
        snapshots.append(collect())
        return 23

    monkeypatch.setattr(a.monitor, "run_view", observe)
    core = SimpleNamespace(resolve_workplace_root=lambda value: a.workplace)
    args = argparse.Namespace(workplace="fixture")
    a.factory.reset_mock()
    assert a.monitor.command_monitor(args, core) == 23
    a.factory.assert_called_once_with()
    assert len(snapshots) == 1
    assert snapshots[0]["cli_version"] == a.properties.loaded.version
    assert snapshots[0]["cli_version"] != a.properties.installed().version
    assert snapshots[0]["runtime"]["lifecycle"] != "ready"


@pytest.mark.parametrize("damage", ["missing", "invalid", "inconsistent"])
def test_unknown_loaded_identity_uses_existing_adapter_fields(
    adapters, monkeypatch, capsys, damage
):
    from processforge_core.common.properties import CoreProperties

    a = adapters
    if damage == "missing":
        (a.root / "VERSION").unlink()
    elif damage == "invalid":
        (a.root / "VERSION").write_bytes(b"PRIVATE_CANARY")
    else:
        (a.root / "VERSION").write_text("9.0.0+inconsistent", encoding="utf-8")
    unknown = CoreProperties.from_distribution(a.root)
    a.factory.return_value = unknown
    monkeypatch.setattr(a.cli, "CORE_PROPERTIES", unknown)
    assert unknown.loaded.version == "unknown"
    assert unknown.loaded.reason
    assert a.cli.main(["version"]) == 0
    output = capsys.readouterr()
    assert output.out == "ProcessForge unknown\nSpec: 1.0\nSchema bundle: 1.0\n"
    assert output.err == ""
    response = a.mcp.respond_valid(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        a.workplace,
        "",
        a.runtime,
    )
    assert response["result"]["serverInfo"] == {
        "name": "processforge",
        "version": "unknown",
    }
    assert response["result"].keys() == {
        "protocolVersion",
        "serverInfo",
        "capabilities",
    }
    state = a.service.base_state(a.workplace, object(), status="ready")
    a.service.add_runtime_truth(state, object(), running=True)
    assert state["processforge_core_version"] == "unknown"
    assert state["installed_pf"] == {"version": "unknown"}
    a.host.save_state(a.workplace, {}, object())
    saved = json.loads(a.host.state_path(a.workplace).read_bytes())
    assert saved["processforge_core_version"] == "unknown"
    catalogue = a.mcp.tool_result(
        "pf.actions.list",
        {"project_root": str(a.project), "limit": 1},
        a.workplace,
        "",
        a.runtime,
    )
    assert catalogue["provenance"]["version"] == "unknown"
    for payload in (response, catalogue):
        assert "PRIVATE_CANARY" not in json.dumps(payload)
        assert str(a.root) not in json.dumps(payload)
