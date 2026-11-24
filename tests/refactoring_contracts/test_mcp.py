"""Exercise both Work read contracts over the selected distribution's stdio bridge."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from conftest import verify_published_archive

if TYPE_CHECKING:
    from conftest import ContractDistribution


ENTRY = "tools/pf_runtime/mcp_server.py"
SESSION = "bridge-fixture-session"
IDENTITY_URI = "pf://core/identity"
PROCESS = "software-feature-development"
BRIDGE_TEST = Path(__file__).resolve().parents[1] / "mcp_bridge/test_stdio_bridge.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    assert name not in sys.modules
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[name]
    return module


@pytest.fixture(scope="module")
def bridge_support() -> ModuleType:
    return load_module("_pf_contract_bridge_support", BRIDGE_TEST)


@contextmanager
def open_bridge(
    support: ModuleType,
    distribution: ContractDistribution,
    workplace: Path,
    *,
    consumer: Path | None = None,
) -> Iterator[Any]:
    # Inject the environment at spawn through the private helper module.
    # The shared subprocess module and this process's environment stay intact.
    launcher = SimpleNamespace(
        PIPE=subprocess.PIPE,
        Popen=partial(subprocess.Popen, env=distribution.environment),
    )
    with patch.object(support, "subprocess", launcher):
        client = support.WireClient(consumer or distribution.root, workplace)
    try:
        yield client
    finally:
        client.close()


def exchange(
    client: Any,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    identifier: str,
) -> dict[str, Any]:
    reply, notices = client.exchange(method, params, request_id=identifier)
    assert (reply["jsonrpc"], reply["id"]) == ("2.0", identifier)
    assert not notices, notices
    return reply


def call(
    client: Any, name: str, arguments: dict[str, Any], identifier: str
) -> dict[str, Any]:
    return exchange(
        client,
        "tools/call",
        {"name": name, "arguments": arguments},
        identifier=identifier,
    )


def tool_body(reply: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    assert "error" not in reply, reply
    result = reply["result"]
    assert result.get("isError", False) is is_error, reply
    (content,) = result["content"]
    assert content["type"] == "text"
    body = json.loads(content["text"])
    assert isinstance(body, dict)
    return body


def cli(distribution: ContractDistribution, *args: str | Path) -> str:
    result = distribution.run(*args)
    assert result.returncode == 0, (args, result.stdout, result.stderr)
    return result.stdout


def start_runtime(
    distribution: ContractDistribution, workplace: Path
) -> dict[str, Any]:
    started = cli(
        distribution,
        "runtime",
        "start",
        "--workplace",
        workplace,
        "--interval",
        "3600",
        "--timeout",
        "30",
        "--json",
    )
    state = json.loads((workplace / "runtime/pf-runtime/service.json").read_bytes())
    return {"pid": json.loads(started)["pid"], "instance_id": state["instance_id"]}


def stop_runtime(distribution: ContractDistribution, workplace: Path) -> None:
    cli(distribution, "runtime", "stop", "--workplace", workplace, "--timeout", "30")


def assert_work_schemas(tools: list[dict[str, Any]]) -> None:
    by_name = {tool["name"]: tool for tool in tools}
    assert len(by_name) == len(tools), "Duplicate tool names in tools/list"
    projection = by_name["pf.work_state"]
    exact = by_name["pf.work.state"]
    project_fields = {
        "project_root": {"type": "string"},
        "session_id": {"type": "string"},
    }
    selectors = {
        key: {"type": "string", "minLength": 1}
        for key in ("run_id", "assignment_id", "context_id")
    }
    schema = {"type": "object", "additionalProperties": False}
    assert projection["inputSchema"] == {**schema, "properties": project_fields}
    assert exact["inputSchema"] == {
        **schema,
        "properties": {**project_fields, **selectors},
    }
    for tool in (projection, exact):
        assert tool["annotations"]["readOnlyHint"] is True


def assert_work_calls(client: Any, project: Path, sibling: Path) -> dict[str, Any]:
    started = tool_body(
        call(
            client,
            "pf.work.start",
            {
                "project_root": str(project),
                "session_id": SESSION,
                "objective": "Verify the explicit stdio Work read contract",
                "process_id": PROCESS,
                "scope_intent": {
                    "schema_version": 1,
                    "assignment": {
                        "allowed_actions": ["read", "write_artifact", "write_product"],
                        "allowed_read_files": ["AGENTS.md"],
                        "allowed_files": [
                            "fixture.txt",
                            ".pf/artifacts/mcp-contract/**",
                        ],
                    },
                },
            },
            "seed-work",
        )
    )
    assert started["action"] == "created_new", started
    selectors = {
        "run_id": started["run_id"],
        "assignment_id": started["assignment_id"],
        "context_id": started["context"]["id"],
    }
    scope = {"session_id": SESSION, "project_root": str(project)}
    projection = tool_body(call(client, "pf.work_state", scope, "projection"))
    assert set(projection) == {"project", "work", "context", "session"}
    assert Path(projection["project"]["root"]) == project
    assert projection["session"]["status"] == "bound"
    assert projection["context"]["snapshot_id"]
    assert any(
        item["run_id"] == selectors["run_id"]
        and item["assignment_id"] == selectors["assignment_id"]
        for item in projection["work"]["active_work"]
    )

    arguments = {**scope, **selectors}
    selected = tool_body(call(client, "pf.work.state", arguments, "selected"))
    assert selected["kind"] == "pf.work.state"
    assert selected["schema_version"] == 1
    assert selected["project"]["id"] == projection["project"]["id"]
    assert selected["run"]["id"] == selectors["run_id"]
    assert selected["assignment"]["id"] == selectors["assignment_id"]
    assert selected["context"]["id"] == selectors["context_id"]
    assert selected["context"]["checksum"] == started["context"]["checksum"]
    assert selected["context"]["identity_source"] == "assignment_process_pin"
    assert selected["process"]["id"] == PROCESS
    assert selected["stage"]["id"] == "orchestration"
    assert selected["execution_readiness"]["allowed_read_files"] == ["AGENTS.md"]

    for name, invalid, identifier in (
        ("pf.work_state", arguments, "projection-rejects-selectors"),
        ("pf.work.state", {**arguments, "run_id": 17}, "selector-type"),
        ("pf.work.state", {**arguments, "context_id": ""}, "selector-empty"),
    ):
        reply = call(client, name, invalid, identifier)
        assert reply["error"] == {"code": -32602, "message": "invalid params"}
        assert "result" not in reply

    for field, other, reason in (
        ("run_id", "different-work-run", "work_identity_mismatch"),
        ("assignment_id", "different-work-assignment", "work_not_found"),
        ("context_id", "different-work-capsule", "work_context_mismatch"),
    ):
        blocked = tool_body(
            call(
                client, "pf.work.state", {**arguments, field: other}, f"denied-{field}"
            )
        )
        assert blocked == {
            "schema_version": 1,
            "kind": "pf.work.execution",
            "action": "blocked",
            "reason": reason,
        }

    for name, fields in (("pf.work_state", scope), ("pf.work.state", arguments)):
        mismatch = call(
            client, name, {**fields, "session_id": "different-session"}, name
        )
        assert tool_body(mismatch, is_error=True) == {
            "error": {"code": "session_mismatch"}
        }
        outside = call(
            client, name, {**fields, "project_root": str(sibling)}, name + "-scope"
        )
        error = tool_body(outside, is_error=True)["error"]
        assert error["code"] == "session_project_mismatch"
        assert error["remediation"]["kind"] == "ledger_session_binding_invalid"

    assert (
        tool_body(call(client, "pf.work.state", arguments, "selected-again"))
        == selected
    )
    return arguments


def assert_forge_recovery(
    client: Any,
    distribution: ContractDistribution,
    workplace: Path,
    runtime: dict[str, Any],
    selectors: dict[str, Any],
) -> None:
    pid = client.process.pid
    stop_runtime(distribution, workplace)
    unavailable = exchange(
        client, "resources/read", {"uri": IDENTITY_URI}, identifier="forge-offline"
    )
    assert unavailable["error"] == {"code": -32603, "message": "backend unavailable"}
    assert tool_body(
        call(client, "pf.work.state", selectors, "forge-offline-work"), is_error=True
    ) == {
        "error": {
            "code": "mcp_backend_unavailable",
            "outcome": "unknown",
            "automatic_retry": False,
        }
    }
    assert exchange(client, "ping", identifier="forge-offline-ping")["result"] == {}
    restarted = start_runtime(distribution, workplace)
    assert restarted["instance_id"] != runtime["instance_id"]
    recovered = exchange(
        client, "resources/read", {"uri": IDENTITY_URI}, identifier="forge-recovered"
    )
    assert recovered["result"]["_meta"]["processforge/backend"]["runtime"] == restarted
    assert client.process.pid == pid and client.process.poll() is None


def assert_forge_stage_receipt(
    client: Any, bridge_support: ModuleType, project: Path, selectors: dict[str, Any]
) -> None:
    flow = project / ".pf"
    outbox_path = "runtime/hooks/contract-stage"
    hook = {
        "id": "contract-stage",
        "type": "outbox",
        "enabled": True,
        "path": outbox_path,
        "event_types": ["process.stage.completed"],
    }
    (flow / "hooks.yaml").write_text(
        json.dumps({"schema_version": 1, "hooks": {"targets": [hook]}}),
        encoding="utf-8",
    )
    state = tool_body(call(client, "pf.work.state", selectors, "stage-before"))
    evidence = state["evidence_guidance"]["transition_template"]["evidence"]
    path = ".pf/artifacts/mcp-contract/observation.md"
    artifact = project / path
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Observed the exact Forge Work binding.\n", encoding="utf-8")
    transitioned = tool_body(
        call(
            client,
            "pf.work.transition",
            {
                **selectors,
                "outcome": "completed",
                "notes": "Observed the exact Forge Work binding.",
                "evidence": [{**item, "path": path} for item in evidence],
            },
            "stage-completed",
        )
    )
    assert transitioned["action"] == "stage_transitioned", transitioned
    journal = flow / "runtime/events/events.sqlite3"
    events = bridge_support.StdioBridgeTest().work_events(journal, selectors["run_id"])
    (event_id,) = [key for kind, key in events if kind == "process.stage.completed"]
    (receipt,) = (flow / outbox_path).glob("*.json")
    assert json.loads(receipt.read_bytes())["event"]["event_id"] == event_id
    print(f"forge stage completed receipt: {event_id}")


@pytest.mark.parametrize("mode", ["garage", "forge"])
def test_work_stdio_contract(
    contract_distribution: ContractDistribution,
    bridge_support: ModuleType,
    tmp_path: Path,
    mode: str,
) -> None:
    """Check discovery, Work shape, scope and errors on one initialized connection."""
    distribution = contract_distribution
    workplace = tmp_path / "wp"
    cli(
        distribution,
        "workplace-init",
        "--workplace",
        workplace,
        "--profile",
        "software-development",
        "--apply",
    )
    if mode == "forge":
        cli(
            distribution,
            "workplace-mode",
            "set",
            "--workplace",
            workplace,
            "--director-enabled",
            "true",
            "--director-office-enabled",
            "true",
            "--json",
        )
    project = tmp_path / "project"
    sibling = tmp_path / "sibling"
    for root in (project, sibling):
        root.mkdir()
        cli(
            distribution,
            "project-init",
            "--project-root",
            root,
            "--workplace",
            workplace,
            "--type",
            "processforge-development",
            "--process",
            PROCESS,
            "--apply",
        )

    runtime = None
    try:
        if mode == "forge":
            runtime = start_runtime(distribution, workplace)
            cli(
                distribution,
                "runtime",
                "session-register",
                "--workplace",
                workplace,
                "--session",
                SESSION,
                "--agent",
                "bridge-fixture",
                "--project-root",
                project,
                "--json",
            )
        else:
            cli(
                distribution,
                "agent-checkin",
                "--workplace",
                workplace,
                "--session",
                SESSION,
                "--agent",
                "bridge-fixture",
                "--project-root",
                project,
            )

        with open_bridge(bridge_support, distribution, workplace) as client:
            reply, notices = client.exchange(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "work-contract", "version": "1"},
                },
            )
            assert type(reply["id"]) is int and reply["id"] == 1
            assert reply["jsonrpc"] == "2.0" and not notices
            initialized = reply["result"]
            assert initialized["protocolVersion"] == "2024-11-05"
            assert initialized["capabilities"] == {
                "tools": {"listChanged": True},
                "resources": {"listChanged": True, "subscribe": True},
            }
            backend = initialized["_meta"]["processforge/backend"]
            if runtime is None:
                assert "runtime" not in backend
            else:
                assert backend["runtime"] == runtime
                assert client.process.pid != runtime["pid"]
            client.notify("notifications/initialized")

            tools = exchange(client, "tools/list", identifier="tools")["result"][
                "tools"
            ]
            assert_work_schemas(tools)
            resources = exchange(client, "resources/list", identifier="resources")
            (identity,) = resources["result"]["resources"]
            assert identity["uri"] == IDENTITY_URI
            assert identity["name"] == "core-identity"
            assert identity["mimeType"] == "application/json"
            selectors = assert_work_calls(client, project, sibling)
            if runtime is not None:
                assert_forge_recovery(
                    client, distribution, workplace, runtime, selectors
                )
                assert_forge_stage_receipt(client, bridge_support, project, selectors)
    finally:
        if mode == "forge":
            stop_runtime(distribution, workplace)


def source_consumer(support: ModuleType, root: Path, consumer: Path) -> None:
    for name, source in support.INVENTORY.public_file_entries(root):
        target = consumer / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def sealed_replacement(consumer: Path) -> str:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys, "dont_write_bytecode", True)
        native = load_module(
            "_pf_contract_native_publication", consumer / "tools/pf_native_control.py"
        )
    manifest_path = consumer / native.MANIFEST
    manifest = native.parse_manifest(manifest_path.read_bytes())
    publication = native.accept_publication(
        consumer, trusted_leaf=(consumer / native.LEAF).read_bytes()
    )
    assert publication is not None
    payload = dict(publication.payload)
    old = payload[ENTRY]
    payload[ENTRY] = old.replace(
        b'"pf.context": "Read Garage context',
        b'"pf.context": "Replacement catalog: Read Garage context',
    )
    assert payload[ENTRY] != old
    build = native.build_publication(
        payload,
        version=manifest["version"],
        source=manifest["source"],
        generated_at=manifest["generated_at"],
    )
    assert build.projection_sha256 != publication.projection_sha256
    for relative_path, content in build.payload.items():
        if content != publication.payload[relative_path]:
            (consumer / relative_path).write_bytes(content)
    manifest_path.write_bytes(build.manifest)
    replaced = native.accept_publication(
        consumer, trusted_leaf=(consumer / native.LEAF).read_bytes()
    )
    assert (
        replaced is not None and replaced.projection_sha256 == build.projection_sha256
    )
    return "manifest:sha256:" + hashlib.sha256(build.manifest).hexdigest()


def assert_sealed_replacement(client: Any, consumer: Path) -> None:
    exchange(client, "initialize", identifier="sealed-init")
    client.notify("notifications/initialized")
    before = exchange(client, "tools/list", identifier="sealed-tools")["result"][
        "tools"
    ]
    before_build = read_identity(client, "sealed-identity")["build_id"]
    exchange(
        client, "resources/subscribe", {"uri": IDENTITY_URI}, identifier="subscribe"
    )
    pid = client.process.pid

    replacement_build = sealed_replacement(consumer)
    assert replacement_build != before_build
    reply, notices = client.exchange(
        "resources/read", {"uri": IDENTITY_URI}, request_id="replacement-identity"
    )
    assert (reply["jsonrpc"], reply["id"]) == ("2.0", "replacement-identity")
    assert (
        json.loads(reply["result"]["contents"][0]["text"])["build_id"]
        == replacement_build
    )
    assert len(notices) == 2
    assert {notice["method"] for notice in notices} == {
        "notifications/tools/list_changed",
        "notifications/resources/updated",
    }
    update = next(
        item for item in notices if item["method"] == "notifications/resources/updated"
    )
    assert update["params"] == {"uri": IDENTITY_URI}
    after = exchange(client, "tools/list", identifier="replacement-tools")["result"][
        "tools"
    ]
    assert [item["name"] for item in after] == [item["name"] for item in before]
    assert "Replacement catalog" in next(
        item["description"] for item in after if item["name"] == "pf.context"
    )
    assert client.process.pid == pid and client.process.poll() is None


def read_identity(client: Any, identifier: str) -> dict[str, Any]:
    reply = exchange(
        client, "resources/read", {"uri": IDENTITY_URI}, identifier=identifier
    )
    (content,) = reply["result"]["contents"]
    return json.loads(content["text"])


def assert_sealed_failure(client: Any, consumer: Path, root: Path) -> None:
    exchange(client, "initialize", identifier="failure-init")
    original = read_identity(client, "failure-identity")
    entry = consumer / ENTRY
    original_entry = entry.read_bytes()
    marker = root / "attempts.txt"
    entry.write_text(
        "from pathlib import Path\nimport sys\n"
        f"with Path({str(marker)!r}).open('a', encoding='utf-8') as stream:\n"
        "    stream.write('attempt\\n')\n"
        "print('private backend diagnostic', file=sys.stderr)\n"
        "raise SystemExit(31)\n",
        encoding="utf-8",
    )
    try:
        failed = call(
            client, "pf.work.start", {"objective": "fixture"}, "failed-mutation"
        )
        assert tool_body(failed, is_error=True) == {
            "error": {
                "code": "mcp_backend_unavailable",
                "outcome": "unknown",
                "automatic_retry": False,
            }
        }
        assert "private backend diagnostic" not in json.dumps(failed)
        assert marker.read_text(encoding="utf-8") == "attempt\n"
    finally:
        entry.write_bytes(original_entry)
    assert exchange(client, "ping", identifier="failure-ping")["result"] == {}
    assert read_identity(client, "restored-identity") == original
    assert marker.read_text(encoding="utf-8") == "attempt\n"


@pytest.mark.parametrize("scenario", ["replacement", "unavailable"])
def test_garage_stdio_backend_lifecycle(
    contract_distribution: ContractDistribution,
    bridge_support: ModuleType,
    tmp_path: Path,
    scenario: str,
) -> None:
    """Use a separate disposable consumer for each deliberate backend change."""
    distribution = contract_distribution
    consumer = tmp_path / "core"
    workplace = tmp_path / "wp"
    workplace.mkdir()
    (workplace / "workplace.yaml").write_text(
        "schema_version: 1\nid: bridge-fixture\n", encoding="utf-8"
    )
    if distribution.profile == "published-1.3.0":
        shutil.copytree(distribution.root, consumer)
        with open_bridge(
            bridge_support, distribution, workplace, consumer=consumer
        ) as client:
            if scenario == "replacement":
                assert_sealed_replacement(client, consumer)
            else:
                assert_sealed_failure(client, consumer, tmp_path)
        verify_published_archive(
            distribution.root, Path(os.environ["PF_CONTRACT_ARCHIVE"])
        )
        return

    source_consumer(bridge_support, distribution.root, consumer)
    case = bridge_support.StdioBridgeTest()
    case.root = tmp_path
    case.source = consumer
    case.workplace = workplace
    case.refresh_inventory()
    with open_bridge(
        bridge_support, distribution, workplace, consumer=consumer
    ) as client:
        case.client = client
        if scenario == "replacement":
            case.test_compatible_replacement_keeps_connection_and_refreshes_discovery()
        else:
            case.test_uncertain_backend_does_not_replay_and_recovers_on_next_request()
