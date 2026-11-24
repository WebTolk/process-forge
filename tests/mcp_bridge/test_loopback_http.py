"""Exercise the local HTTP contract shared by the Runtime and bridge adapters."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import cast
from unittest.mock import patch
from urllib.request import getproxies

INSTANCE_ID = "fixture-instance"
TOKEN = "fixture-token"
BRIDGE_LIMIT = 8 * 1024 * 1024
ENVELOPE_PREFIX = (
    b'{"instance_id":"' + INSTANCE_ID.encode("ascii") + b'","result":{"text":"'
)
ENVELOPE_SUFFIX = b'"}}'
ENVELOPE_OVERHEAD = len(ENVELOPE_PREFIX) + len(ENVELOPE_SUFFIX)


def setUpModule() -> None:
    # The public stdio suite runs under unittest with no source PYTHONPATH.
    root = Path(__file__).resolve().parents[2]
    source_path = [str(root / name) for name in ("tools", "src")]
    path_patch = patch.object(sys, "path", source_path + sys.path)
    path_patch.start()
    unittest.addModuleCleanup(path_patch.stop)


@dataclass
class Reply:
    status: int
    body: bytes
    content_length: bool = True


@dataclass
class Request:
    method: str
    target: str
    authorization: str | None
    content_type: str | None
    accept: str | None
    body: bytes


class FixtureHandler(BaseHTTPRequestHandler):
    timeout = 5.0

    def reply(self) -> None:
        server = cast(FixtureServer, self.server)
        server.requests.append(
            Request(
                self.command,
                self.path,
                self.headers.get("Authorization"),
                self.headers.get("Content-Type"),
                self.headers.get("Accept"),
                self.rfile.read(int(self.headers.get("Content-Length", "0"))),
            )
        )
        reply = server.replies.get(self.path, Reply(404, b""))
        self.send_response(reply.status)
        if reply.content_length:
            self.send_header("Content-Length", str(len(reply.body)))
        else:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(reply.body)

    do_GET = do_POST = reply

    def log_message(self, format: str, *args: object) -> None:
        pass


class FixtureServer(HTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), FixtureHandler)
        self.requests: list[Request] = []
        self.replies: dict[str, Reply] = {}


def padded_envelope(size: int) -> bytes:
    return ENVELOPE_PREFIX + b"x" * (size - ENVELOPE_OVERHEAD) + ENVELOPE_SUFFIX


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = import_module("pf_runtime.service")
        self.bridge = import_module("pf_runtime.mcp_bridge")
        self.enterContext(patch.dict(os.environ, {"NO_PROXY": "127.0.0.1"}))

        self.server = FixtureServer()
        self.addCleanup(self.server.server_close)
        thread = Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

        self.workplace = Path(self.enterContext(TemporaryDirectory()))
        self.descriptor = {
            "status": "ready",
            "endpoint": self.endpoint,
            "instance_id": INSTANCE_ID,
        }
        runtime = self.workplace / "runtime" / "pf-runtime"
        runtime.mkdir(parents=True)
        (runtime / "service.json").write_text(
            json.dumps(self.descriptor), encoding="utf-8"
        )
        (runtime / "token.json").write_text(
            json.dumps({"token": TOKEN}), encoding="utf-8"
        )
        (self.workplace / "workplace.yaml").write_text(
            "coordination:\n  director_enabled: true\n", encoding="utf-8"
        )

    def test_runtime_preserves_json_headers_and_query(self) -> None:
        route = "/register?source=fixture"
        payload = {"label": "café"}
        self.server.replies[route] = Reply(201, b'{"registered":true}')
        status, body = self.service.http_json(
            "POST", self.endpoint + route, token=TOKEN, payload=payload
        )
        self.assertEqual((status, body), (201, {"registered": True}))
        self.assertEqual(
            self.server.requests,
            [
                Request(
                    "POST",
                    route,
                    f"Bearer {TOKEN}",
                    "application/json",
                    "application/json",
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                )
            ],
        )

    def test_runtime_preserves_empty_and_ordinary_error_responses(self) -> None:
        route = "/status"
        for status, raw, expected in (
            (204, b"", {}),
            (401, b'{"error":"not_authorized"}', {"error": "not_authorized"}),
            (409, b'{"error":"conflict"}', {"error": "conflict"}),
            (409, b"operation pending", {"error": "operation pending"}),
        ):
            with self.subTest(status=status, raw=raw):
                self.server.replies[route] = Reply(status, raw)
                self.assertEqual(
                    self.service.http_json("GET", self.endpoint + route),
                    (status, expected),
                )
        self.assertEqual(
            self.server.requests,
            [Request("GET", route, None, None, "application/json", b"")] * 4,
        )

    def test_runtime_reads_beyond_the_bridge_limit(self) -> None:
        raw = padded_envelope(BRIDGE_LIMIT + 1)
        self.server.replies["/status"] = Reply(200, raw)
        status, body = self.service.http_json("GET", self.endpoint + "/status")
        self.assertEqual(status, 200)
        self.assertEqual(
            len(body["result"]["text"]), BRIDGE_LIMIT + 1 - ENVELOPE_OVERHEAD
        )

    def test_both_adapters_use_origin_form_with_proxy_configured(self) -> None:
        self.server.replies["/status"] = Reply(200, b"{}")
        self.server.replies["/work/start"] = Reply(
            200, json.dumps({"instance_id": INSTANCE_ID, "result": {}}).encode("ascii")
        )
        # The configured proxy is the fixture itself. Every possible request stays
        # within the test server, where the request target exposes proxy use.
        with patch.dict(
            os.environ,
            {
                "HTTP_PROXY": self.endpoint,
                "http_proxy": self.endpoint,
                "NO_PROXY": "",
                "no_proxy": "",
            },
        ):
            self.assertEqual(getproxies().get("http"), self.endpoint)
            self.assertEqual(
                self.service.http_json("GET", self.endpoint + "/status"), (200, {})
            )
            self.assertEqual(self.bridge.runtime_work_start(self.workplace, {}), {})
        self.assertEqual(
            [request.target for request in self.server.requests],
            ["/status", "/work/start"],
        )

    def test_bridge_preserves_mcp_and_work_start_envelopes(self) -> None:
        message = {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
        reply = {"jsonrpc": "2.0", "id": 7, "result": {"tools": []}}
        result = {"action": "work_started"}
        for route, envelope in (
            ("/mcp", {"messages": [reply]}),
            ("/work/start", {"result": result}),
        ):
            self.server.replies[route] = Reply(
                200,
                json.dumps({"instance_id": INSTANCE_ID, **envelope}).encode("ascii"),
            )
        self.assertEqual(
            self.bridge.exchange(
                json.dumps(message), str(self.workplace), "fixture-session", 5.0
            ),
            [reply],
        )
        arguments = {"objective": "fixture"}
        self.assertEqual(
            self.bridge.runtime_work_start(self.workplace, arguments), result
        )
        self.assertEqual(
            [
                (
                    request.method,
                    request.target,
                    request.authorization,
                    request.content_type,
                )
                for request in self.server.requests
            ],
            [
                ("POST", "/mcp", f"Bearer {TOKEN}", "application/json"),
                ("POST", "/work/start", f"Bearer {TOKEN}", "application/json"),
            ],
        )
        self.assertEqual(
            [json.loads(request.body) for request in self.server.requests],
            [
                {
                    "request": message,
                    "session_id": "fixture-session",
                    "expected_instance_id": INSTANCE_ID,
                },
                {**arguments, "expected_instance_id": INSTANCE_ID},
            ],
        )

    def test_bridge_rejects_uncorrelated_work_start_result(self) -> None:
        self.server.replies["/work/start"] = Reply(
            200, b'{"instance_id":"other-instance","result":{"action":"work_started"}}'
        )
        with self.assertRaises(self.bridge.BackendUnavailable):
            self.bridge.runtime_work_start(self.workplace, {})
        self.assertEqual(len(self.server.requests), 1)

    def test_bridge_rejects_non_success_status_with_matching_envelope(self) -> None:
        self.server.replies["/work/start"] = Reply(
            401, json.dumps({"instance_id": INSTANCE_ID, "result": {}}).encode("ascii")
        )
        with self.assertRaises((self.bridge.BackendUnavailable, OSError)):
            self.bridge.runtime_work_start(self.workplace, {})
        self.assertEqual(len(self.server.requests), 1)

    def test_bridge_preserves_unavailable_envelope_without_retry(self) -> None:
        self.server.replies["/mcp"] = Reply(
            200, b'{"instance_id":"other-instance","messages":[]}'
        )
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "pf.work.start", "arguments": {"objective": "fixture"}},
        }
        argv = ["mcp_bridge", "--workplace", str(self.workplace)]
        stdin = io.StringIO(json.dumps(request) + "\n")
        stdout = io.StringIO()
        with (
            patch.object(sys, "argv", argv),
            patch.object(sys, "stdin", stdin),
            patch.object(sys, "stdout", stdout),
            patch.object(self.bridge, "configure_utf8"),
            patch.object(self.bridge, "_garage_exchange") as garage,
        ):
            self.assertEqual(self.bridge.main(), 0)
        garage.assert_not_called()
        self.assertEqual([request.target for request in self.server.requests], ["/mcp"])
        response = json.loads(stdout.getvalue())
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 7)
        self.assertIs(response["result"]["isError"], True)
        self.assertEqual(
            json.loads(response["result"]["content"][0]["text"]),
            {
                "error": {
                    "code": "mcp_backend_unavailable",
                    "outcome": "unknown",
                    "automatic_retry": False,
                }
            },
        )

    def test_bridge_response_limit_with_both_http_framings(self) -> None:
        for content_length in (True, False):
            for size in (BRIDGE_LIMIT, BRIDGE_LIMIT + 1):
                with self.subTest(content_length=content_length, size=size):
                    raw = padded_envelope(size)
                    self.assertEqual(len(raw), size)
                    self.server.replies["/work/start"] = Reply(200, raw, content_length)
                    with (
                        patch.object(
                            self.bridge,
                            "_read_mapping",
                            side_effect=(self.descriptor, {"token": TOKEN}),
                        ),
                        patch.object(self.bridge, "json", wraps=json) as bridge_json,
                    ):
                        if size == BRIDGE_LIMIT:
                            result = self.bridge.runtime_work_start(self.workplace, {})
                            expected = {"text": "x" * (size - ENVELOPE_OVERHEAD)}
                            self.assertTrue(result == expected)
                            bridge_json.loads.assert_called_once()
                        else:
                            with self.assertRaises(self.bridge.BackendUnavailable):
                                self.bridge.runtime_work_start(self.workplace, {})
                            bridge_json.loads.assert_not_called()


class SharedTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = import_module("pf_runtime.loopback_http")
        self.client = self.transport.LoopbackHttpClient()

    def test_adapters_refuse_nonliteral_endpoint_before_connecting(self) -> None:
        service = import_module("pf_runtime.service")
        bridge = import_module("pf_runtime.mcp_bridge")
        endpoint = "http://localhost:1234"
        descriptor = {
            "status": "ready",
            "endpoint": endpoint,
            "instance_id": INSTANCE_ID,
        }
        with (
            patch.object(self.transport, "HTTPConnection") as connection,
            patch(
                "socket.create_connection", side_effect=AssertionError("unexpected I/O")
            ) as connect,
            patch.object(
                bridge, "_read_mapping", side_effect=(descriptor, {"token": TOKEN})
            ),
        ):
            self.assertEqual(
                service.http_json("GET", endpoint + "/status"),
                (0, {"error": "Invalid loopback HTTP URL"}),
            )
            with self.assertRaises(
                (bridge.BackendUnavailable, self.transport.LoopbackTransportError)
            ):
                bridge.runtime_work_start(Path("."), {})
            connect.assert_not_called()
            connection.assert_not_called()

    def test_url_validation_refuses_before_opening_a_connection(self) -> None:
        with patch.object(self.transport, "HTTPConnection") as connection:
            for url in (
                "http://localhost:1234/",
                "https://127.0.0.1:1234/",
                "http://127.0.0.1/",
                "http://127.0.0.1:0/",
                "http://127.0.0.1:65536/",
                "http://fixture-user@127.0.0.1:1234/",
                "http://127.0.0.1:1234/#fixture",
                "http://127.0.0.1:1234/\t",
            ):
                with (
                    self.subTest(url=url),
                    self.assertRaisesRegex(
                        self.transport.LoopbackTransportError,
                        "^Invalid loopback HTTP URL$",
                    ),
                ):
                    self.client.request("GET", url, headers={}, body=None, timeout=1.0)
            connection.assert_not_called()

    def test_endpoint_builder_requires_an_origin_and_local_route(self) -> None:
        endpoint = "http://127.0.0.1:1234"
        self.assertEqual(
            self.transport.loopback_endpoint_url(endpoint + "/", "/work/start"),
            endpoint + "/work/start",
        )
        for suffix in ("/status", "?source=fixture"):
            with (
                self.subTest(suffix=suffix),
                self.assertRaisesRegex(
                    self.transport.LoopbackTransportError,
                    "^Invalid loopback HTTP endpoint$",
                ),
            ):
                self.transport.loopback_endpoint_url(endpoint + suffix, "/mcp")
        with self.assertRaisesRegex(
            self.transport.LoopbackTransportError, "^Invalid loopback HTTP route$"
        ):
            self.transport.loopback_endpoint_url(endpoint, "relative")

    def test_redirect_status_is_refused_before_read_and_closes(self) -> None:
        with patch.object(self.transport, "HTTPConnection") as connection:
            opened = connection.return_value
            response = opened.getresponse.return_value
            response.status = 303
            with self.assertRaisesRegex(
                self.transport.LoopbackTransportError,
                "^Loopback HTTP redirect refused$",
            ):
                self.client.request(
                    "GET", "http://127.0.0.1:1234/", headers={}, body=None, timeout=1.0
                )
            response.read.assert_not_called()
            response.close.assert_called_once_with()
            opened.close.assert_called_once_with()
            connection.assert_called_once_with("127.0.0.1", 1234, timeout=1.0)

    def test_oversized_response_reads_only_limit_plus_one_and_closes(self) -> None:
        with patch.object(self.transport, "HTTPConnection") as connection:
            opened = connection.return_value
            response = opened.getresponse.return_value
            response.status = 200
            response.read.return_value = b"x" * (BRIDGE_LIMIT + 1)
            with self.assertRaisesRegex(
                self.transport.LoopbackTransportError,
                "^Loopback HTTP response exceeds byte limit$",
            ):
                self.client.request(
                    "GET",
                    "http://127.0.0.1:1234/",
                    headers={},
                    body=None,
                    timeout=1.0,
                    max_response_bytes=BRIDGE_LIMIT,
                )
            response.read.assert_called_once_with(BRIDGE_LIMIT + 1)
            response.close.assert_called_once_with()
            opened.close.assert_called_once_with()

    def test_connection_failure_has_a_fixed_diagnostic(self) -> None:
        with patch.object(self.transport, "HTTPConnection") as connection:
            opened = connection.return_value
            opened.request.side_effect = OSError("fixture-private-diagnostic")
            with self.assertRaisesRegex(
                self.transport.LoopbackTransportError, "^Loopback HTTP request failed$"
            ) as raised:
                self.client.request(
                    "GET", "http://127.0.0.1:1234/", headers={}, body=None, timeout=1.0
                )
            self.assertTrue(raised.exception.__suppress_context__)
            opened.close.assert_called_once_with()
