"""Regress Runtime POST framing with inert readers and an isolated HTTP fixture."""
from __future__ import annotations

import http.client
import io
import json
import socket
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

from pf_runtime import service


class TrackedReader(io.BytesIO):
    def __init__(self, body: bytes):
        super().__init__(body)
        self.calls: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.calls.append(size)
        if not 0 <= size <= service.MAX_BODY_BYTES:
            raise AssertionError(f'unbounded body read: {size}')
        return super().read(size)


class RuntimeHttpBodyTests(unittest.TestCase):
    def setUp(self):
        # Construct only the real HTTP adapter; never initialize/start a Runtime.
        self.runtime = service.RuntimeProcess.__new__(service.RuntimeProcess)
        self.runtime.workplace_root = ROOT
        self.runtime.core = object()
        self.runtime.token = 'http-fixture-token'
        self.runtime.state = {'status': 'ready'}
        self.runtime.state_lock = threading.RLock()
        self.runtime.shutdown_check = False
        self.runtime.active_requests = 0
        self.handler = self.runtime.make_handler()
        self.logs = patch.object(service, 'append_operator_log').start()
        self.ingest = patch.object(service.host, 'ingest_event', side_effect=lambda payload, *_: {'payload': payload}).start()
        self.addCleanup(patch.stopall)

    def inert(self, length: str | None, body: bytes):
        handler = self.handler.__new__(self.handler)
        handler.headers = {} if length is None else {'Content-Length': length}
        handler.rfile = TrackedReader(body)
        return handler

    def test_valid_lengths_and_byte_boundaries(self):
        unicode_body = json.dumps({'text': 'Привет'}, ensure_ascii=False).encode('utf-8')
        cases = [
            (None, b'', {}), ('', b'', {}), ('0', b'ignored', {}),
            ('2', b'{}unread', {}), (' 2\t', b'{}', {}), ('0002', b'{}', {}),
            (str(len(unicode_body)), unicode_body, {'text': 'Привет'}),
            (str(service.MAX_BODY_BYTES), b'{}' + b' ' * (service.MAX_BODY_BYTES - 2), {}),
        ]
        for length, body, expected in cases:
            with self.subTest(length=length, size=len(body)):
                handler = self.inert(length, body)
                self.assertEqual(handler.read_body(), expected)
                size = int(length or '0')
                self.assertEqual(handler.rfile.calls, [size] if size else [])

    def test_rejected_lengths_never_read(self):
        invalid = ['-1', '-0', '+2', '2.0', 'text', '1_0', '0x2', '2, 2', '\u00b2', '\u0662', ' \t', '9' * 5000]
        for length in invalid + [str(service.MAX_BODY_BYTES + 1)]:
            with self.subTest(length=length[:30]):
                handler = self.inert(length, b'{}')
                message = 'request body too large' if length == str(service.MAX_BODY_BYTES + 1) else 'invalid Content-Length'
                with self.assertRaisesRegex(ValueError, '^' + message + '$'):
                    handler.read_body()
                self.assertEqual(handler.rfile.calls, [])

    def test_short_body_is_rejected_before_json(self):
        for length, body in [('3', b'{}'), ('20', b'{"ok":true}'), ('1', b'')]:
            with self.subTest(length=length):
                handler = self.inert(length, body)
                with self.assertRaisesRegex(ValueError, '^incomplete request body$'):
                    handler.read_body()
                self.assertEqual(handler.rfile.calls, [int(length)])

    def test_json_number_and_object_contract(self):
        valid = b'{"float":1.25,"large":1e308,"tiny":1e-4000,"int":123456789012345678901234567890,"bool":true,"null":null,"strings":["NaN","Infinity","1e9999"],"duplicate":1,"duplicate":2}'
        self.assertEqual(self.inert(str(len(valid)), valid).read_body(), json.loads(valid))
        invalid = [
            b'{"n":NaN}', b'{"n":Infinity}', b'{"n":-Infinity}',
            b'{"n":1e9999}', b'{"n":-1e9999}', b'{"nested":[{"n":NaN}]}',
            b'{"n":Infinity,"n":1}', b'{"n":1e9999,"n":1}',
        ]
        for body in invalid:
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, '^request JSON numbers must be finite$'):
                    self.inert(str(len(body)), body).read_body()
        for body in [b'[]', b'null', b'1', b'"text"']:
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, '^request JSON must be an object$'):
                    self.inert(str(len(body)), body).read_body()
        for body in [b'{', b'\xff']:
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    self.inert(str(len(body)), body).read_body()

    def test_authorization_and_stopping_precede_body_read(self):
        for authorization, stopping, shutdown_check, status, error in [
            (None, 'ready', False, 401, 'unauthorized'),
            ('Bearer wrong', 'ready', False, 401, 'unauthorized'),
            ('Bearer http-fixture-token', 'stopping', False, 503, 'runtime_stopping'),
            ('Bearer http-fixture-token', 'ready', True, 503, 'runtime_stopping'),
        ]:
            with self.subTest(status=status, authorization=authorization):
                handler = self.inert('-1', b'{}')
                if authorization:
                    handler.headers['Authorization'] = authorization
                handler.path = '/event'
                handler.send_json = Mock()
                self.runtime.state['status'] = stopping
                self.runtime.shutdown_check = shutdown_check
                handler.do_POST()
                handler.send_json.assert_called_once_with(status, {'error': error})
                self.assertEqual(handler.rfile.calls, [])
                self.assertEqual(self.runtime.active_requests, 0)
        self.ingest.assert_not_called()

    def test_actual_http_handler_dispatch_and_recovery(self):
        completed = threading.Event()

        class CompletedHandler(self.handler):
            def do_POST(self):
                try:
                    super().do_POST()
                finally:
                    completed.set()

        with ThreadingHTTPServer(('127.0.0.1', 0), CompletedHandler) as server:
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
            thread.start()
            try:
                def post(length, body=b'', authorization='Bearer http-fixture-token'):
                    completed.clear()
                    headers = ['POST /event HTTP/1.0', 'Host: localhost', 'Content-Type: application/json']
                    if length is not None:
                        headers.append('Content-Length: ' + length)
                    if authorization:
                        headers.append('Authorization: ' + authorization)
                    with socket.create_connection(server.server_address, timeout=5) as connection:
                        connection.sendall(('\r\n'.join(headers) + '\r\n\r\n').encode('latin-1') + body)
                        # EOF makes a truncated frame deterministic; no stalled socket claim.
                        connection.shutdown(socket.SHUT_WR)
                        response = http.client.HTTPResponse(connection)
                        response.begin()
                        result = response.status, json.loads(response.read())
                        self.assertTrue(completed.wait(timeout=5))
                        return result

                for length, body, status, error in [
                    ('-1', b'{}', 400, 'invalid Content-Length'),
                    ('text', b'', 400, 'invalid Content-Length'),
                    (str(service.MAX_BODY_BYTES + 1), b'', 400, 'request body too large'),
                    ('3', b'{}', 400, 'incomplete request body'),
                    ('9', b'{"n":NaN}', 400, 'request JSON numbers must be finite'),
                    ('12', b'{"n":1e9999}', 400, 'request JSON numbers must be finite'),
                    ('2', b'[]', 400, 'request JSON must be an object'),
                ]:
                    with self.subTest(length=length, body=body):
                        calls = self.ingest.call_count
                        self.assertEqual(post(length, body), (status, {'error': error}))
                        self.assertEqual(self.ingest.call_count, calls)
                        self.assertEqual(self.runtime.active_requests, 0)
                self.assertEqual(post('-1', b'{}', authorization=None), (401, {'error': 'unauthorized'}))
                body = '{"text":"Привет","number":1.25}'.encode('utf-8')
                for length, raw, expected in [(None, b'', {}), ('0', b'', {}), (str(len(body)), body, json.loads(body))]:
                    with self.subTest(length=length):
                        self.assertEqual(post(length, raw), (200, {'payload': expected}))
                self.assertEqual(self.ingest.call_count, 3)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())


if __name__ == '__main__':
    unittest.main(verbosity=2)
