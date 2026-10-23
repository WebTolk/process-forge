"""Regress build-aware diagnosis at the real Runtime and MCP boundaries."""

from __future__ import annotations

import argparse
import json
import threading
from types import SimpleNamespace

import pytest

from processforge_core.common.properties import CoreIdentity, CoreProperties


@pytest.mark.parametrize("change", ["same-label", "release", "missing", "malformed"])
def test_report_retains_boot_build_and_observes_live_disk(
    tmp_path, write_distribution, change
):
    root = tmp_path / "core"
    properties = write_distribution(root)
    loaded = properties.loaded
    assert properties.report()["status"] == "current"
    if change == "same-label":
        write_distribution(root, commit="b" * 40, generated_at="2025-02-03T04:05:06Z")
    elif change == "release":
        write_distribution(root, "8.1.0-dev.4")
    elif change == "missing":
        (root / "VERSION").unlink()
    else:
        (root / "VERSION").write_text("PRIVATE_CANARY", encoding="utf-8")
    report = properties.report()
    assert properties.loaded is loaded
    assert report["loaded"] == loaded.record()
    assert report["installed"] == properties.installed().record()
    assert report["schema_version"] == 1
    if change in {"same-label", "release"}:
        assert report["status"] == "reload_required"
        assert report["reload_required"] is True
        assert report["reason"] == (
            "build_changed" if change == "same-label" else "release_changed"
        )
        fresh = CoreProperties.from_distribution(root)
        assert fresh.report()["status"] == "current"
        assert fresh.loaded.build_id != loaded.build_id
    else:
        assert report["status"] == "unknown"
        assert report["reload_required"] is None
        assert report["reason"] == "installed_identity_unavailable"
    assert "PRIVATE_CANARY" not in json.dumps(report)
    assert str(root) not in json.dumps(report)


@pytest.mark.parametrize("record", [None, {}, "PRIVATE_CANARY", {"version": "1.2.0"}])
def test_missing_remote_identity_never_uses_observers_loaded_build(
    tmp_path, write_distribution, record
):
    properties = write_distribution(tmp_path)
    report = properties.report(loaded=record)
    assert report["loaded"]["build_id"] == "unknown"
    assert report["status"] == "unknown"
    assert report["reload_required"] is None
    assert report["installed"]["build_id"] == properties.loaded.build_id


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "PRIVATE_CANARY"),
        ("build_id", "PRIVATE_CANARY"),
        ("source_commit", "PRIVATE_CANARY"),
        ("source_kind", "PRIVATE_CANARY"),
        ("status", "PRIVATE_CANARY"),
        ("reason", "PRIVATE_CANARY/path"),
        ("reason", "x" * 129),
        ("version", None),
    ],
)
def test_remote_records_validate_each_portable_field(
    tmp_path, write_distribution, field, value
):
    properties = write_distribution(tmp_path)
    record = dict(properties.loaded.record())
    record[field] = value
    observed = CoreIdentity.from_record(record)
    assert observed.status == "unknown"
    assert observed.reason == "loaded_identity_invalid"
    assert "PRIVATE_CANARY" not in json.dumps(observed.record())


def test_partial_build_is_unknown_and_output_containers_are_fresh(
    tmp_path, write_distribution
):
    properties = write_distribution(tmp_path)
    record = CoreIdentity(
        version=properties.loaded.version,
        source_kind="unmanaged",
        status="partial",
        reason="build_metadata_unavailable",
    ).record()
    report = properties.report(loaded=record)
    assert report["status"] == "unknown"
    assert report["reason"] == "build_identity_unavailable"
    report["installed"]["build_id"] = "mutated"
    report["loaded"]["version"] = "mutated"
    assert properties.report()["status"] == "current"
    assert CoreIdentity.from_record(properties.loaded.record()) == properties.loaded


@pytest.mark.parametrize(
    "change", ["same-label", "release", "missing", "none", "old-state"]
)
def test_doctor_diagnoses_actual_recorded_build(
    adapters, monkeypatch, write_distribution, change
):
    a = adapters
    from processforge_core.agents.registry import AgentWorkplaceRegistry

    a.service.runtime_root(a.workplace).parent.mkdir(parents=True, exist_ok=True)
    AgentWorkplaceRegistry().workplace_agent_ledger_path(a.workplace).parent.mkdir(
        parents=True, exist_ok=True
    )
    state = a.service.base_state(a.workplace, object(), status="ready")
    if change == "same-label":
        write_distribution(a.root, commit="b" * 40)
    elif change == "release":
        write_distribution(a.root, "8.1.0-dev.4")
    elif change == "missing":
        (a.root / "VERSION").unlink()
    elif change == "old-state":
        state.pop("core_identity")
        state["schema_version"] = 1
    monkeypatch.setattr(a.service, "active_service", lambda *args: (True, state))
    monkeypatch.setattr(a.service, "status_payload", lambda *args: {"health": "ready"})
    checks = []
    core = SimpleNamespace(
        resolve_workplace_root=lambda value: a.workplace,
        check=lambda status, message: (status, message),
        print_checks=lambda values: (
            checks.extend(values) or int(any(status == "FAIL" for status, _ in values))
        ),
    )
    result = a.service.command_doctor(argparse.Namespace(workplace="fixture"), core)
    builds = [
        (status, message)
        for status, message in checks
        if message.startswith("runtime core build")
    ]
    assert len(builds) == 1
    if change in {"same-label", "release"}:
        assert builds == [
            ("FAIL", "runtime core build differs from installed; restart required")
        ]
        assert result == 1
        if change == "same-label":
            assert ("PASS", "runtime core version compatible") in checks
    elif change == "none":
        assert builds == [("PASS", "runtime core build current")]
        assert result == 0
    else:
        assert builds[0][0] == "WARN"
        assert "unknown" in builds[0][1]


@pytest.mark.parametrize("operation", ["list", "describe"])
def test_actual_mcp_discovery_requires_reconnect_after_same_label_build(
    adapters, write_distribution, operation
):
    a = adapters
    loaded = a.properties.loaded
    write_distribution(a.root, commit="b" * 40)
    arguments = (
        {"project_root": str(a.project), "limit": 1}
        if operation == "list"
        else {"project_root": str(a.project), "action_id": "mcp:pf.context"}
    )
    result = a.mcp.tool_result(
        "pf.actions." + operation, arguments, a.workplace, "", a.runtime
    )
    provenance = result["provenance"]
    identity = provenance["core_identity"]
    assert provenance["contract_version"] == 2
    assert provenance["version"] == loaded.version == a.properties.installed().version
    assert provenance["connected_host_build"] == loaded.build_id
    assert provenance["installed_build"] == a.properties.installed().build_id
    assert provenance["installed_build"] != provenance["connected_host_build"]
    assert identity["loaded"]["source_commit"] == loaded.source_commit
    assert identity["installed"]["source_commit"] == "b" * 40
    assert identity["required_action"] == "reconnect"
    assert identity["reload_required"] is True
    identity["loaded"]["build_id"] = "mutated"
    again = a.mcp.tool_result(
        "pf.actions." + operation, arguments, a.workplace, "", a.runtime
    )
    assert again["provenance"]["connected_host_build"] == loaded.build_id


def test_cli_observes_remote_runtime_without_replacing_its_loaded_identity(
    adapters, monkeypatch, write_distribution
):
    from processforge_core import composition

    a = adapters
    state = a.service.base_state(a.workplace, object(), status="ready")
    loaded = a.properties.loaded
    fresh = write_distribution(a.root, commit="b" * 40)
    monkeypatch.setattr(composition, "build_core_properties", lambda: fresh)
    payload = a.service.add_runtime_truth(state, object(), running=True)
    assert payload["core_identity"]["loaded"] == loaded.record()
    assert payload["core_identity"]["installed"] == fresh.loaded.record()
    assert payload["core_identity"]["required_action"] == "restart"
    old = a.service.add_runtime_truth(
        {"schema_version": 1, "processforge_core_version": loaded.version},
        object(),
        running=True,
    )
    assert old["schema_version"] == 2
    assert old["core_identity"]["loaded"]["build_id"] == "unknown"
    assert old["core_identity"]["status"] == "unknown"
    assert old["core_identity"]["required_action"] == "unknown"


def test_runtime_http_status_refreshes_disk_and_keeps_its_boot_build(
    adapters, write_distribution
):
    a = adapters
    process = object.__new__(a.service.RuntimeProcess)
    process.workplace_root = a.workplace
    process.core = object()
    process.state_lock = threading.RLock()
    process.state = a.service.base_state(a.workplace, object(), status="ready")
    process._project_errors = {}
    process.scheduler_thread = None
    process.known_project_roots = lambda: []
    process.active_worker_count = lambda roots: 0
    process.last_event = lambda roots: None
    loaded = a.properties.loaded
    write_distribution(a.root, commit="b" * 40)
    payload = process.status_payload()
    assert payload["core_identity"]["loaded"] == loaded.record()
    assert payload["core_identity"]["installed"] == a.properties.installed().record()
    assert payload["core_identity"]["required_action"] == "restart"
    assert process.state["core_identity"]["loaded"] == loaded.record()
