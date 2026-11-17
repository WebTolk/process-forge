"""Exercise the real MCP entry across compatible Core replacement and failure."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from io import TextIOWrapper
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
IDENTITY_URI = "pf://core/identity"
INVENTORY_SPEC = importlib.util.spec_from_file_location(
    "bridge_inventory", ROOT / "tools/validate-process-forge-checksums.py"
)
assert INVENTORY_SPEC is not None and INVENTORY_SPEC.loader is not None
INVENTORY = importlib.util.module_from_spec(INVENTORY_SPEC)
INVENTORY_SPEC.loader.exec_module(INVENTORY)


class WireClient:
    """Keep one host connection and retain the actual wire transcript."""

    def __init__(
        self,
        source: Path,
        workplace: Path,
        *,
        backend_timeout_seconds: float | None = None,
    ) -> None:
        command = [
            sys.executable,
            "-B",
            str(source / "tools/pf_runtime/mcp_server.py"),
            "--workplace",
            str(workplace),
            "--session",
            "bridge-fixture-session",
        ]
        if backend_timeout_seconds is not None:
            command.extend(["--backend-timeout-seconds", str(backend_timeout_seconds)])
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=source,
        )
        self.messages: queue.Queue[str | None] = queue.Queue()
        self.stderr: list[str] = []
        self.reader_errors: list[str] = []
        self.transcript: list[dict[str, Any]] = []
        self.counter = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.error_reader = threading.Thread(target=self._read_errors, daemon=True)
        self.reader.start()
        self.error_reader.start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                self.messages.put(line)
        except (OSError, UnicodeError) as error:
            self.reader_errors.append(repr(error))
        finally:
            self.messages.put(None)

    def _read_errors(self) -> None:
        assert self.process.stderr is not None
        try:
            raw = cast(TextIOWrapper, self.process.stderr).buffer.read()
            if raw:
                self.stderr.append(
                    bytes(raw).decode("utf-8", errors="backslashreplace")
                )
        except OSError as error:
            self.reader_errors.append(repr(error))

    def notify(self, method: str) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": method}) + "\n"
        )
        self.process.stdin.flush()

    def exchange(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        self.counter += 1
        identifier = self.counter if request_id is None else request_id
        request = {
            "jsonrpc": "2.0",
            "id": identifier,
            "method": method,
            "params": params or {},
        }
        assert self.process.stdin is not None
        started = time.monotonic()
        self.process.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
        self.process.stdin.flush()
        notices = []
        while True:
            raw = self.messages.get(timeout=20)
            if raw is None:
                raise AssertionError("MCP entry exited: " + "".join(self.stderr))
            response = json.loads(raw)
            self.transcript.append({"request_id": identifier, "stdout": raw})
            if "id" not in response:
                notices.append(response)
                continue
            if response["id"] != identifier:
                raise AssertionError("uncorrelated or duplicate response")
            self.transcript.append(
                {"method": method, "elapsed_seconds": time.monotonic() - started}
            )
            return response, notices

    def close(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.close()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
            raise
        finally:
            self.reader.join(timeout=5)
            self.error_reader.join(timeout=5)
            if self.reader.is_alive() or self.error_reader.is_alive():
                self.reader_errors.append("wire reader did not finish")
            print(
                json.dumps(
                    {
                        "kind": "native-mcp-wire",
                        "os": platform.platform(),
                        "python": platform.python_version(),
                        "pid": self.process.pid,
                        "exit_code": self.process.returncode,
                        "transcript": self.transcript,
                        "stderr": self.stderr,
                        "reader_errors": self.reader_errors,
                    },
                    ensure_ascii=True,
                )
            )
            for stream in (self.process.stdout, self.process.stderr):
                if stream is not None:
                    stream.close()
        if self.process.returncode:
            raise AssertionError("MCP entry failed: " + "".join(self.stderr))
        if self.reader_errors:
            raise AssertionError("wire capture failed: " + repr(self.reader_errors))
        if self.stderr:
            raise AssertionError("unexpected transport stderr: " + "".join(self.stderr))


class StdioBridgeTest(unittest.TestCase):
    """Use native subprocesses and isolated source-mode consumer distributions."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pf-mcp-bridge-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "distribution"
        self.source.mkdir()
        for name, path in INVENTORY.public_file_entries(ROOT):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(INVENTORY.released_content(path))
        self.refresh_inventory()
        self.workplace = self.root / "workplace"
        self.workplace.mkdir()
        (self.workplace / "workplace.yaml").write_text(
            "schema_version: 1\nid: bridge-fixture\n", encoding="utf-8"
        )
        self.client = WireClient(self.source, self.workplace, backend_timeout_seconds=5)
        self.addCleanup(self.client.close)

    def refresh_inventory(self) -> None:
        """Publish coherent source bytes for the next genuine backend entry."""
        inventory = self.source / INVENTORY.PUBLIC_INVENTORY
        inventory.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text(INVENTORY.build_inventory(self.source), encoding="utf-8")

    def identity(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        response, notices = self.client.exchange(
            "resources/read", {"uri": IDENTITY_URI}
        )
        self.assertNotIn("error", response)
        return json.loads(response["result"]["contents"][0]["text"]), notices

    def test_compatible_replacement_keeps_connection_and_refreshes_discovery(
        self,
    ) -> None:
        ping, _ = self.client.exchange("ping")
        self.assertEqual(ping["result"], {})
        response, notices = self.client.exchange(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bridge-qualification", "version": "1"},
            },
        )
        self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")
        self.assertTrue(response["result"]["capabilities"]["tools"]["listChanged"])
        self.assertTrue(response["result"]["capabilities"]["resources"]["subscribe"])
        self.assertEqual(notices, [])
        self.client.notify("notifications/initialized")
        before, _ = self.client.exchange("tools/list")
        self.client.exchange("resources/list")
        initial, _ = self.identity()
        subscribed, _ = self.client.exchange(
            "resources/subscribe", {"uri": IDENTITY_URI}
        )
        self.assertNotIn("error", subscribed)
        pid = self.client.process.pid

        # Change executing Core logic, not merely its installed VERSION label.
        properties = self.source / "src/processforge_core/common/properties.py"
        original = properties.read_text(encoding="utf-8")
        changed = original.replace(
            "source_revision_unavailable", "bridge_fixture_core_v2"
        )
        self.assertNotEqual(original, changed)
        properties.write_text(changed, encoding="utf-8")
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        original_entry = entry.read_text(encoding="utf-8")
        changed_entry = original_entry.replace(
            '"pf.context": "Read Garage context',
            '"pf.context": "Обновлённый каталог: \u0085 \u2028 \u2029 Read Garage context',
        )
        self.assertNotEqual(original_entry, changed_entry)
        entry.write_text(changed_entry, encoding="utf-8")
        self.refresh_inventory()
        print(
            json.dumps(
                {
                    "candidate_core_sha256": hashlib.sha256(
                        properties.read_bytes()
                    ).hexdigest()
                }
            )
        )

        current, notices = self.identity()
        self.assertNotEqual(initial["reason"], current["reason"])
        self.assertEqual(current["reason"], "bridge_fixture_core_v2")
        self.assertEqual(self.client.process.pid, pid)
        self.assertIsNone(self.client.process.poll())
        self.assertEqual(
            {notice["method"] for notice in notices},
            {"notifications/tools/list_changed", "notifications/resources/updated"},
        )
        after, repeated = self.client.exchange("tools/list")
        self.assertEqual(repeated, [])
        self.assertEqual(
            [tool["name"] for tool in before["result"]["tools"]],
            [tool["name"] for tool in after["result"]["tools"]],
        )
        self.assertIn("Обновлённый каталог", after["result"]["tools"][0]["description"])
        for separator in ("\u0085", "\u2028", "\u2029"):
            self.assertIn(separator, after["result"]["tools"][0]["description"])
        ping, _ = self.client.exchange("ping")
        self.assertEqual(ping["result"], {})
        self.client.exchange("resources/unsubscribe", {"uri": IDENTITY_URI})
        properties.write_text(original, encoding="utf-8")
        self.refresh_inventory()
        _, notices = self.identity()
        self.assertEqual(notices, [])
        denied, _ = self.client.exchange("resources/read", {"uri": properties.as_uri()})
        self.assertEqual(denied["error"]["code"], -32002)
        mismatch, _ = self.client.exchange(
            "tools/call",
            {"name": "pf.work.state", "arguments": {"session_id": "different-session"}},
        )
        self.assertTrue(mismatch["result"]["isError"])
        self.assertIn("session_mismatch", mismatch["result"]["content"][0]["text"])

    def test_forge_clients_share_runtime_and_reconnect_without_local_fallback(
        self,
    ) -> None:
        workplace = self.root / "forge-workplace"

        def cli(*args: object) -> dict[str, Any]:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(self.source / "bin/pf.py"),
                    *(str(value) for value in args),
                ],
                cwd=self.source,
                capture_output=True,
                encoding="utf-8",
                timeout=60,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            return (
                json.loads(completed.stdout)
                if completed.stdout.lstrip().startswith("{")
                else {}
            )

        cli(
            "workplace-init",
            "--workplace",
            workplace,
            "--profile",
            "software-development",
            "--apply",
        )
        cli(
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

        def runtime(*args: object) -> dict[str, Any]:
            return cli("runtime", *args, "--workplace", workplace)

        project = self.root / "forge-project"
        project.mkdir()
        cli(
            "project-init",
            "--project-root",
            project,
            "--workplace",
            workplace,
            "--type",
            "processforge-development",
            "--process",
            "software-feature-development",
            "--apply",
        )
        first = runtime("start", "--interval", "3600", "--timeout", "30", "--json")
        self.addCleanup(runtime, "stop", "--timeout", "30")
        runtime(
            "session-register",
            "--session",
            "bridge-fixture-session",
            "--agent",
            "bridge-fixture",
            "--project-root",
            project,
            "--json",
        )
        state_path = workplace / "runtime/pf-runtime/service.json"
        state = json.loads(state_path.read_bytes())
        clients = [
            WireClient(self.source, workplace, backend_timeout_seconds=5)
            for _ in range(2)
        ]
        for client in clients:
            self.addCleanup(client.close)
            response, _ = client.exchange("initialize")
            self.assertNotIn("error", response)
            self.assertEqual(
                response["result"]["_meta"]["processforge/backend"]["runtime"],
                {"instance_id": state["instance_id"], "pid": first["pid"]},
            )
            self.assertNotEqual(client.process.pid, first["pid"])
            scoped, _ = client.exchange(
                "tools/call", {"name": "pf.session_context", "arguments": {}}
            )
            self.assertFalse(scoped["result"].get("isError"), scoped)
            outside, _ = client.exchange(
                "tools/call",
                {
                    "name": "pf.session_context",
                    "arguments": {"project_root": str(self.root)},
                },
            )
            self.assertTrue(outside["result"]["isError"])
            self.assertIn("project", outside["result"]["content"][0]["text"])
            mismatch, _ = client.exchange(
                "tools/call",
                {
                    "name": "pf.work.state",
                    "arguments": {"session_id": "another-session"},
                },
            )
            self.assertTrue(mismatch["result"]["isError"])
            self.assertIn("session_mismatch", mismatch["result"]["content"][0]["text"])

        # The instance selector is checked by the server, not trusted from disk.
        stale = dict(state, instance_id="different-runtime-instance")
        state_path.write_text(json.dumps(stale), encoding="utf-8")
        try:
            rejected, _ = clients[0].exchange("tools/list")
            self.assertEqual(rejected["error"]["code"], -32603)
        finally:
            state_path.write_text(json.dumps(state), encoding="utf-8")

        runtime("stop", "--timeout", "30")
        stopped = runtime("status", "--json")
        self.assertEqual(stopped["status"], "stopped")
        unavailable, _ = clients[0].exchange(
            "tools/call", {"name": "pf.work.start", "arguments": {"apply": True}}
        )
        self.assertTrue(unavailable["result"]["isError"])
        failure = json.loads(unavailable["result"]["content"][0]["text"])["error"]
        self.assertEqual(failure["code"], "mcp_backend_unavailable")
        self.assertFalse(failure["automatic_retry"])
        for client in clients:
            unavailable, _ = client.exchange("resources/read", {"uri": IDENTITY_URI})
            self.assertEqual(unavailable["error"]["code"], -32603)
            ping, _ = client.exchange("ping")
            self.assertEqual(ping["result"], {})

        # Existing host pipes reconnect to the restarted sole executor.
        restarted = runtime("start", "--interval", "3600", "--timeout", "30", "--json")
        current = json.loads(state_path.read_bytes())
        self.assertNotEqual(current["instance_id"], state["instance_id"])
        for client in clients:
            identity, _ = client.exchange("resources/read", {"uri": IDENTITY_URI})
            self.assertNotIn("error", identity)
            self.assertEqual(
                identity["result"]["_meta"]["processforge/backend"]["runtime"],
                {"instance_id": current["instance_id"], "pid": restarted["pid"]},
            )

    def test_uncertain_backend_does_not_replay_and_recovers_on_next_request(
        self,
    ) -> None:
        self.client.exchange("initialize")
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        original = entry.read_bytes()
        marker = self.root / "attempt-count.txt"
        entry.write_text(
            "from pathlib import Path\nimport sys\n"
            f"with Path({str(marker)!r}).open('a', encoding='utf-8') as stream:\n"
            "    stream.write('attempt\\n')\n"
            "print('private backend diagnostic', file=sys.stderr)\n"
            "raise SystemExit(31)\n",
            encoding="utf-8",
        )
        failed, _ = self.client.exchange(
            "tools/call",
            {"name": "pf.work.start", "arguments": {"objective": "fixture"}},
        )
        self.assertTrue(failed["result"]["isError"])
        error = json.loads(failed["result"]["content"][0]["text"])["error"]
        self.assertEqual(error["outcome"], "unknown")
        self.assertFalse(error["automatic_retry"])
        self.assertEqual(marker.read_text(encoding="utf-8"), "attempt\n")
        self.assertNotIn("private backend diagnostic", json.dumps(failed))
        self.assertEqual(self.client.stderr, [])
        entry.write_bytes(original)
        self.refresh_inventory()
        ping, _ = self.client.exchange("ping")
        self.assertEqual(ping["result"], {})
        restored, _ = self.client.exchange("resources/read", {"uri": IDENTITY_URI})
        self.assertIn("contents", restored["result"])
        self.assertEqual(marker.read_text(encoding="utf-8"), "attempt\n")

    def test_invalid_protocol_does_not_load_business_core(self) -> None:
        # Capture the genuine transport before introducing a business-Core trap.
        ping, _ = self.client.exchange("ping")
        self.assertEqual(ping["result"], {})
        core = self.source / "tools/processforge.py"
        original = core.read_bytes()
        core.write_text(
            "raise RuntimeError('business Core must not load')\n", encoding="utf-8"
        )
        self.refresh_inventory()
        rejected, notices = self.client.exchange("initialize", {"capabilities": []})
        self.assertEqual(rejected["error"]["code"], -32602)
        self.assertEqual(notices, [])
        invalid_names: tuple[object, ...] = ([], {}, None, 42)
        for name in invalid_names:
            rejected, _ = self.client.exchange("tools/call", {"name": name})
            self.assertEqual(rejected["error"]["code"], -32602)
        core.write_bytes(original)
        self.refresh_inventory()
        accepted, _ = self.client.exchange("initialize")
        self.assertEqual(accepted["result"]["protocolVersion"], "2024-11-05")

    def test_malformed_frames_do_not_start_backend(self) -> None:
        self.client.exchange("ping")
        cases: list[tuple[Any, Any, int]] = [
            ([], None, -32600),
            (None, None, -32600),
            (1, None, -32600),
            ({"jsonrpc": "1.0", "id": "old", "method": "initialize"}, "old", -32600),
            ({"jsonrpc": "2.0", "id": "method", "method": 3}, "method", -32600),
            ({"jsonrpc": "2.0", "method": False}, None, -32600),
        ]
        for identifier in (True, [], {}):
            cases.append(
                (
                    {"jsonrpc": "2.0", "id": identifier, "method": "initialize"},
                    None,
                    -32600,
                )
            )
        for identifier in (None, "Текст \u2028 \ud800", 4, 1.5):
            cases.append(
                (
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "method": "tools/call",
                        "params": [],
                    },
                    identifier,
                    -32602,
                )
            )
        for params in (None, False, 2, "bad"):
            cases.append(
                (
                    {
                        "jsonrpc": "2.0",
                        "id": "params",
                        "method": "unknown",
                        "params": params,
                    },
                    "params",
                    -32602,
                )
            )
        for params in ({}, {"name": []}, {"name": "pf.work.start", "arguments": None}):
            cases.append(
                (
                    {
                        "jsonrpc": "2.0",
                        "id": "call",
                        "method": "tools/call",
                        "params": params,
                    },
                    "call",
                    -32602,
                )
            )
        lines = [json.dumps(value, ensure_ascii=True) for value, _, _ in cases]
        expected = [(identifier, code) for _, identifier, code in cases]
        for raw, code in (
            ("{bad-json", -32700),
            ("NaN", -32700),
            ("""{"jsonrpc":"2.0","id":1e400,"method":"initialize"}""", -32600),
        ):
            lines.append(raw)
            expected.append((None, code))
        lines.extend(
            json.dumps(value)
            for value in (
                {"jsonrpc": "2.0", "method": "initialize", "params": []},
                {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": []}},
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "pf.work.start", "arguments": []},
                },
            )
        )
        # Compare the public transport to the genuine current backend, including
        # exact errors, null IDs and silence, before replacing the backend.
        backend = subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.source / "tools/pf_runtime/mcp_server.py"),
                "--workplace",
                str(self.workplace),
                "--backend-request",
            ],
            input="\n".join(lines) + "\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=30,
            cwd=self.source,
        )
        self.assertEqual(backend.returncode, 0, backend.stderr)
        baseline = [json.loads(line) for line in backend.stdout.split("\n") if line]
        self.assertEqual(len(baseline), len(expected))
        self.assertEqual(
            [(value["id"], value["error"]["code"]) for value in baseline], expected
        )
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        original = entry.read_bytes()
        marker = self.root / "malformed-backend-attempts.txt"
        entry.write_text(
            "from pathlib import Path\nimport sys\n"
            f"""with Path({str(marker)!r}).open("a", encoding="utf-8") as stream:\n"""
            "    stream.write(sys.stdin.readline())\n"
            "raise SystemExit(31)\n",
            encoding="utf-8",
        )
        sentinel = {"jsonrpc": "2.0", "id": "transport-sentinel", "method": "ping"}
        assert self.client.process.stdin is not None
        started = time.monotonic()
        self.client.process.stdin.write(
            "\n".join([*lines, json.dumps(sentinel)]) + "\n"
        )
        self.client.process.stdin.flush()
        responses = []
        for _ in range(len(expected) + 1):
            raw = self.client.messages.get(timeout=20)
            self.assertIsNotNone(raw)
            responses.append(json.loads(cast(str, raw)))
        self.client.transcript.append(
            {
                "kind": "malformed-frame-batch",
                "responses": responses,
                "elapsed_seconds": time.monotonic() - started,
            }
        )
        self.assertEqual(responses[:-1], baseline)
        self.assertEqual(
            responses[-1],
            {"jsonrpc": "2.0", "id": "transport-sentinel", "result": {}},
        )
        self.assertFalse(marker.exists(), "Malformed frames launched a backend")

        # Fixed transport shapes cannot accept business arguments or silence a
        # valid notification. Each must still launch exactly one fresh backend.
        failed, _ = self.client.exchange(
            "tools/call", {"name": "pf.session_chat", "arguments": {"limit": True}}
        )
        self.assertTrue(failed["result"]["isError"])
        self.client.notify("notifications/initialized")
        self.client.exchange("ping")
        attempts = marker.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(
            json.loads(attempts[0])["params"]["arguments"], {"limit": True}
        )
        self.assertEqual(json.loads(attempts[1])["method"], "notifications/initialized")
        entry.write_bytes(original)
        self.refresh_inventory()
        rejected, _ = self.client.exchange(
            "tools/call", {"name": "pf.session_chat", "arguments": {"limit": True}}
        )
        self.assertEqual(rejected["error"]["code"], -32602)

    def test_bad_backend_frames_and_timeout_preserve_connection(self) -> None:
        self.client.exchange("initialize")
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        original = entry.read_bytes()
        cases = {
            "truncated": "print('{', flush=True)\n",
            "wrong-id": "print(json.dumps({'jsonrpc':'2.0','id':999,'result':{}}))\n",
            "duplicate": "for _ in range(2): print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':{}}))\n",
            "timeout": "import time; time.sleep(60)\n",
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                entry.write_text(
                    "import json,sys\nrequest=json.loads(sys.stdin.readline())\n"
                    + body,
                    encoding="utf-8",
                )
                failed, _ = self.client.exchange(
                    "tools/call",
                    {"name": "pf.work.start", "arguments": {"objective": "fixture"}},
                )
                self.assertTrue(failed["result"]["isError"])
                error = json.loads(failed["result"]["content"][0]["text"])["error"]
                self.assertEqual(error["outcome"], "unknown")
                self.assertFalse(error["automatic_retry"])
                ping, _ = self.client.exchange("ping")
                self.assertEqual(ping["result"], {})
                entry.write_bytes(original)
                self.refresh_inventory()
                restored, _ = self.client.exchange(
                    "resources/read", {"uri": IDENTITY_URI}
                )
                self.assertIn("contents", restored["result"])

    def test_surrogate_ids_keep_transport_and_backend_usable(self) -> None:
        self.client.exchange("initialize")
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        original = entry.read_bytes()
        pid = self.client.process.pid
        for identifier in ("\ud800", "\udfff"):
            with self.subTest(identifier=ascii(identifier)):
                ping, _ = self.client.exchange("ping", request_id=identifier)
                self.assertEqual(ping["id"], identifier)
                self.assertEqual(ping["result"], {})
                identity, _ = self.client.exchange(
                    "resources/read", {"uri": IDENTITY_URI}, request_id=identifier
                )
                self.assertEqual(identity["id"], identifier)
                self.assertIn("contents", identity["result"])
                entry.write_text("raise SystemExit(31)\n", encoding="utf-8")
                failed, _ = self.client.exchange(
                    "tools/call",
                    {"name": "pf.work.start", "arguments": {"objective": "fixture"}},
                    request_id=identifier,
                )
                self.assertEqual(failed["id"], identifier)
                self.assertTrue(failed["result"]["isError"])
                ping, _ = self.client.exchange("ping")
                self.assertEqual(ping["result"], {})
                entry.write_bytes(original)
                self.refresh_inventory()
                restored, _ = self.client.exchange(
                    "resources/read", {"uri": IDENTITY_URI}
                )
                self.assertIn("contents", restored["result"])
                self.assertEqual(self.client.process.pid, pid)
                self.assertIsNone(self.client.process.poll())

    def test_unicode_response_and_opaque_stderr(self) -> None:
        # Wait for the real transport parent before replacing only its backend.
        self.client.exchange("initialize")
        entry = self.source / "tools/pf_runtime/mcp_server.py"
        text = "Текст \u0085 \u2028 \u2029 не является разделителем MCP"
        entry.write_text(
            "import json,sys\nrequest=json.loads(sys.stdin.readline())\n"
            f"text={text!r}\n"
            "response={'jsonrpc':'2.0','id':request['id'],'result':{'content':[{'type':'text','text':text}]}}\n"
            "sys.stderr.buffer.write(b'\\xff\\xfe diagnostic')\n"
            "sys.stdout.buffer.write((json.dumps(response,ensure_ascii=False)+'\\n').encode('utf-8'))\n",
            encoding="utf-8",
        )
        response, notices = self.client.exchange(
            "tools/call",
            {"name": "pf.work.start", "arguments": {"objective": "fixture"}},
        )
        self.assertEqual(response["result"]["content"][0]["text"], text)
        self.assertNotIn("isError", response["result"])
        self.assertEqual(notices, [])
        self.assertEqual(self.client.stderr, [])


if __name__ == "__main__":
    unittest.main()
