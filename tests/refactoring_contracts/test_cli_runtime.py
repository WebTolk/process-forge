"""Exercise the shipped launchers against the explicitly selected distribution."""

from __future__ import annotations

import errno
import http.client
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from stat import S_IMODE
from threading import Barrier
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import pytest
from conftest import HARNESS_ROOT, git_checkout_identity

if TYPE_CHECKING:
    from conftest import ContractDistribution


def _launch(
    distribution: ContractDistribution,
    entry: str,
    native: bool,
    *args: str | Path,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if not native:
        return distribution.run(*args, entry=f"bin/{entry}.py", input_text=input_text)
    if os.name == "nt":
        command = [str(distribution.root / "bin" / f"{entry}.bat")]
    else:
        command = ["sh", str(distribution.root / "bin" / entry)]
    return subprocess.run(
        [*command, *map(str, args)],
        cwd=distribution.root,
        env=distribution.environment,
        input=input_text,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _stdout(result: subprocess.CompletedProcess[str]) -> str:
    assert type(result.returncode) is int and result.returncode == 0, result
    assert result.stderr == "", result
    return result.stdout


def _object(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    body = json.loads(_stdout(result))
    assert isinstance(body, dict), body
    return body


def _refused(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert type(result.returncode) is int and result.returncode == 1, result
    assert result.stdout == "", result
    assert result.stderr == f"FAIL: {reason}\n", result


def _server_status(body: dict[str, Any], lifecycle: str) -> dict[str, Any]:
    assert type(body["schema_version"]) is int and body["schema_version"] == 1
    assert body["kind"] == "pf.runtime.monitor"
    runtime = body["runtime"]
    assert isinstance(runtime, dict), body
    assert runtime["lifecycle"] == lifecycle, runtime
    return runtime


def test_launcher_version(contract_distribution: ContractDistribution) -> None:
    version_file = contract_distribution.root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip()
    for native in (False, True):
        result = _launch(contract_distribution, "pf", native, "version")
        assert _stdout(result) == (
            f"ProcessForge {version}\nSpec: 1.0\nSchema bundle: 1.0\n"
        )
        invalid = _launch(contract_distribution, "pf", native, "version", "--json")
        assert type(invalid.returncode) is int and invalid.returncode == 2, invalid
        assert invalid.stdout == "", invalid
        assert invalid.stderr.startswith("usage: "), invalid
        assert invalid.stderr.endswith("error: unrecognized arguments: --json\n"), (
            invalid
        )


def test_absent_workplace(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    workplace = tmp_path / "absent workplace"
    for native in (False, True):
        options = ("--workplace", workplace, "--json")
        body = _object(
            _launch(contract_distribution, "pf", native, "runtime", "status", *options)
        )
        assert body["status"] == "not_running" and body["health"] == "stopped"
        assert body["runtime"]["running"] is False
        assert Path(body["workplace_root"]) == workplace
        assert not workplace.exists()
        for entry, prefix in (("pf", ("server",)), ("pf-server", ())):
            body = _object(
                _launch(
                    contract_distribution, entry, native, *prefix, "status", *options
                )
            )
            status = _server_status(body, "not_running")
            assert status["owner_pid"] is None and status["owner_alive"] is None
            assert not workplace.exists()


def test_native_refusals(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    workplace = tmp_path / "invalid configuration"
    workplace.mkdir()
    config = workplace / "configuration.yaml"
    invalid_yaml = "runtime: [PRIVATE_CANARY\n"
    config.write_text(invalid_yaml, encoding="utf-8")
    absent = tmp_path / "absent workplace"
    aliases = (
        ("pf", ("runtime",), "serve"),
        ("pf", ("server",), "run"),
        ("pf-server", (), "run"),
    )
    for native in (False, True):
        for entry, prefix, serve in aliases:
            _refused(
                _launch(
                    contract_distribution,
                    entry,
                    native,
                    *prefix,
                    serve,
                    "--workplace",
                    workplace,
                ),
                "configuration_yaml_invalid",
            )
            assert list(workplace.iterdir()) == [config]
            assert config.read_text(encoding="utf-8") == invalid_yaml
            _refused(
                _launch(
                    contract_distribution,
                    entry,
                    native,
                    *prefix,
                    "event",
                    "--workplace",
                    absent,
                    "--input",
                    "-",
                    "--json",
                    input_text="[]\n",
                ),
                "runtime event input must be a JSON object",
            )
            assert not absent.exists()


def test_nested_distribution_has_no_git_identity(
    contract_distribution: ContractDistribution,
) -> None:
    with pytest.raises(pytest.UsageError, match="not a checkout root"):
        git_checkout_identity(HARNESS_ROOT / "tests", contract_distribution.environment)


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Linux wrapper mode scenario"
)
def test_posix_direct_invocation(contract_distribution: ContractDistribution) -> None:
    for entry in ("pf", "pf-server"):
        launcher = contract_distribution.root / "bin" / entry
        assert S_IMODE(launcher.stat().st_mode) == 0o644, launcher
        try:
            subprocess.run(
                [str(launcher), "--help"],
                cwd=contract_distribution.root,
                env=contract_distribution.environment,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except PermissionError as exc:
            assert exc.errno == errno.EACCES, exc
            continue
        raise AssertionError(f"direct execution unexpectedly succeeded for {entry}")


def _http(
    endpoint: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    bearer: str | None = None,
) -> tuple[int, Any]:
    parsed = urlsplit(endpoint)
    assert parsed.hostname == "127.0.0.1", endpoint
    connection = http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=15)
    headers = {"Content-Type": "application/json"}
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    try:
        connection.request(
            method, path, None if payload is None else json.dumps(payload), headers
        )
        response = connection.getresponse()
        raw = response.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return response.status, body
    finally:
        connection.close()


def _check_native_actions(
    distribution: ContractDistribution,
    workplace: Path,
    project: Path,
    endpoint: str,
    bearer: str,
    instance: str,
    evidence: Path,
) -> None:
    # Same four calls as check_concurrent_native_actions in the shipped smoke.
    sessions = (("sess-a", "codex-a"), ("parallel-0", "parallel-agent-0"))
    for session, agent in sessions:
        body = _object(
            distribution.run(
                "runtime",
                "session-register",
                "--workplace",
                workplace,
                "--project-root",
                project,
                "--session",
                session,
                "--agent",
                agent,
                "--json",
            )
        )
        assert body["session_id"] == session

    def mcp(session: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "expected_instance_id": instance,
            "session_id": session,
            "request": {
                "jsonrpc": "2.0",
                "id": session,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        }

    requests = [
        ("/mcp", mcp(session, "pf.session.heartbeat", {"apply": True}))
        for session, _ in sessions
    ]
    requests.append(
        (
            "/mcp",
            mcp("sess-a", "pf.runtime_driver.describe", {"driver": "unregistered"}),
        )
    )
    requests.append(
        (
            "/tick",
            {"project_roots": [str(project)], "director": True, "inspector": True},
        )
    )
    barrier = Barrier(len(requests))

    def exchange(request: tuple[str, dict[str, Any]]) -> dict[str, Any]:
        path, payload = request
        barrier.wait(timeout=10)
        try:
            code, response = _http(endpoint, "POST", path, payload, bearer=bearer)
        except (OSError, http.client.HTTPException) as exc:
            return {
                "path": path,
                "request": payload,
                "transport_error": f"{type(exc).__name__}: {exc}",
            }
        return {
            "path": path,
            "request": payload,
            "http_status": code,
            "response": response,
        }

    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        exchanges = list(executor.map(exchange, requests))
    # Record each request and its response before evaluating the expected semantics.
    evidence.write_text(json.dumps(exchanges, indent=2) + "\n", encoding="utf-8")

    replies = []
    for item in exchanges[:3]:
        assert item.get("http_status") == 200, item
        (reply,) = item["response"]["messages"]
        assert reply["jsonrpc"] == "2.0"
        assert reply["id"] == item["request"]["request"]["id"]
        replies.append(reply["result"])
    refused = replies[2]
    assert refused.get("isError") is True, refused
    assert "driver_not_registered" in refused["content"][0]["text"], refused
    tick = exchanges[3]
    assert tick.get("http_status") == 200, tick
    (scheduled,) = tick["response"]["projects"]
    assert scheduled["director"] == scheduled["inspector"] == "tick", scheduled

    published = distribution.profile == "published-1.3.0"
    observed = []
    for reply in replies[:2]:
        result = json.loads(reply["content"][0]["text"])
        if published and reply.get("isError") is True:
            assert result == {"error": {"code": "read_failed"}}, reply
            observed.append("read_failed")
            continue
        assert not reply.get("isError"), reply
        assert result["status"] == "completed", result
        assert isinstance(result.get("native_summary", ""), str), result
        observed.append(result.get("native_summary", ""))
    expected = [f"HEARTBEAT: {agent} session={session}" for session, agent in sessions]
    if published:
        print(f"Published response ownership: {observed!r}")
    else:
        assert observed == expected


@contextmanager
def _running_server(
    distribution: ContractDistribution, workplace: Path
) -> Iterator[dict[str, Any]]:
    binding = ("--workplace", workplace)
    try:
        started = _object(
            _launch(
                distribution,
                "pf-server",
                True,
                "start",
                *binding,
                "--interval",
                "60",
                "--timeout",
                "30",
                "--json",
            )
        )
        assert started["status"] == "started", started
        pid = started["pid"]
        endpoint = started["endpoint"]
        assert type(pid) is int and pid > 0, started
        parsed = urlsplit(endpoint)
        assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
        assert parsed.port
        yield started
    finally:
        stopped = _launch(
            distribution, "pf-server", True, "stop", *binding, "--timeout", "10"
        )
        if stopped.returncode != 0:
            assert stopped.returncode == 1 and not stopped.stdout, stopped
            assert stopped.stderr.strip() == (
                "FAIL: runtime stop request failed: 409 "
                "{'error': 'runtime_busy_or_activity_unknown'}"
            ), stopped
            print("pf-server stop: guarded refusal 409; checking runtime stop")
            stopped = distribution.run("runtime", "stop", *binding, "--timeout", "10")
    assert _stdout(stopped) == "RUNTIME: stopped\n"


def test_server_lifecycle(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    distribution = contract_distribution
    workplace = tmp_path / "workplace"
    binding = ("--workplace", workplace)
    _stdout(distribution.run("workplace-init", *binding, "--apply"))
    with _running_server(distribution, workplace) as started:
        pid = started["pid"]
        endpoint = started["endpoint"]
        repeated = _object(distribution.run("runtime", "start", *binding, "--json"))
        assert repeated == {
            "status": "already_running",
            "pid": pid,
            "endpoint": endpoint,
        }
        runtime = _object(distribution.run("runtime", "status", *binding, "--json"))
        assert runtime["status"] == runtime["health"] == "ready"
        assert runtime["pid"] == pid and runtime["endpoint"] == endpoint
        assert Path(runtime["workplace_root"]) == workplace
        monitor = _object(
            _launch(distribution, "pf", True, "server", "status", *binding, "--json")
        )
        server = _server_status(monitor, "ready")
        assert server["owner_pid"] == pid and server["owner_alive"] is True

        assert _http(endpoint, "GET", "/readyz") == (
            200,
            {"status": "ready", "ready": True},
        )
        code, denied = _http(endpoint, "POST", "/event", {})
        assert code == 401 and isinstance(denied["error"], str) and denied["error"]

    runtime = _object(distribution.run("runtime", "status", *binding, "--json"))
    assert runtime["status"] == runtime["health"] == "stopped"


def test_native_response_ownership(
    contract_distribution: ContractDistribution, tmp_path: Path
) -> None:
    distribution = contract_distribution
    workplace = tmp_path / "workplace"
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Fixture project\n", encoding="utf-8")
    binding = ("--workplace", workplace)
    _stdout(distribution.run("workplace-init", *binding, "--apply"))
    _stdout(
        distribution.run(
            "workplace-mode",
            "set",
            *binding,
            "--director-enabled",
            "true",
            "--director-office-enabled",
            "true",
        )
    )
    _stdout(
        distribution.run(
            "project-onboard",
            *binding,
            "--project-root",
            project,
            "--type",
            "generic-software-project",
            "--apply",
        )
    )
    _stdout(
        distribution.run(
            "project-mode",
            "set",
            *binding,
            "--project-root",
            project,
            "--mode",
            "organized",
        )
    )
    with _running_server(distribution, workplace) as started:
        fixture_state = workplace / "runtime" / "pf-runtime"
        state_file = fixture_state / "service.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["pid"] == started["pid"]
        assert state["endpoint"] == started["endpoint"]
        instance = state["instance_id"]
        assert isinstance(instance, str) and instance
        token_file = fixture_state / "token.json"
        bearer = json.loads(token_file.read_text(encoding="utf-8"))["token"]
        assert isinstance(bearer, str) and bearer
        _check_native_actions(
            distribution,
            workplace,
            project,
            started["endpoint"],
            bearer,
            instance,
            tmp_path / "native-action-exchanges.json",
        )
