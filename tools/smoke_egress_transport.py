"""Independent TLS framing, environment and failure qualification for the broker."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
from processforge_core.egress.contracts import EgressError, binding_for, encoded
from processforge_core.egress.transport import JsonTransport, windows_tls_context
from processforge_core.egress.storage import Store
from processforge_core.egress.engine import TrustedTool
from smoke_egress_engine import denied, fixture, recipient


def openssl_binary():
    found = shutil.which("openssl")
    if found:
        return found
    git = shutil.which("git")
    if git:
        candidate = Path(git).resolve().parents[1] / "usr/bin/openssl.exe"
        if candidate.is_file():
            return str(candidate)
    raise AssertionError("Qualification requires OpenSSL executable (Git for Windows is supported)")


def run_checks():
    checks = []
    with tempfile.TemporaryDirectory(prefix="pf-egress-tls-") as temporary:
        root = Path(temporary)
        key, certificate = root / "fixture-key.pem", root / "fixture-cert.pem"
        result = subprocess.run([openssl_binary(), "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                                 "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost",
                                 "-keyout", str(key), "-out", str(certificate)], capture_output=True, timeout=30)
        assert result.returncode == 0, "synthetic TLS fixture creation failed"
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(certificate, key)
        # Test CA is scoped to this in-memory context. No OS certificate store edit.
        client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_context.load_verify_locations(cafile=certificate)
        with patch.dict(os.environ, {"SSLKEYLOGFILE": str(root / "must-not-exist.keys"),
                                     "SSL_CERT_FILE": str(root / "must-not-read.pem"),
                                     "SSL_CERT_DIR": str(root / "must-not-read-dir")}):
            actual_context = windows_tls_context()
            assert actual_context.keylog_filename is None and actual_context.verify_mode == ssl.CERT_REQUIRED
            assert actual_context.check_hostname and actual_context.get_ca_certs()
            assert not (root / "must-not-exist.keys").exists()
        checks.append("A08 no ambient TLS keylog home or trust-file configuration")
        with recipient(tls=server_context) as (endpoint, capture):
            with fixture(endpoint) as f:
                f.policy["recipient"]["transport"] = "https-json-v1"
                with patch("processforge_core.egress.transport.windows_tls_context", return_value=client_context):
                    s = f.session()
                view = s.prepare_view()
                s.dispatch(view, s.authorize(view))
                assert capture[-1]["body"] == view.body
                checks.append("A26 actual certificate-verified TLS exact body capture")
        with recipient(tls=server_context) as (endpoint, capture):
            with fixture(endpoint) as f:
                f.policy["recipient"]["transport"] = "https-json-v1"
                s = f.session()
                view = s.prepare_view()
                denied(lambda: s.dispatch(view, s.authorize(view)), "delivery_unknown")
                assert not capture
                checks.append("A26 untrusted TLS certificate sends no application bytes")

    with recipient() as (proxy, proxy_capture), recipient() as (endpoint, capture):
        with fixture(endpoint) as f, patch.dict(os.environ, {"HTTP_PROXY": proxy, "HTTPS_PROXY": proxy,
                                                           "ALL_PROXY": proxy, "NO_PROXY": ""}):
            s = f.session()
            s.run()
            assert len(capture) == 1 and not proxy_capture
            checks.append("A08 no ambient proxy or extra network recipient")

    for failure in ("redirect", "chunked", "oversize", "duplicate-length", "unknown-field", "range"):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(302 if failure == "redirect" else 200)
                self.send_header("Content-Type", "application/json")
                if failure == "redirect":
                    self.send_header("Location", "http://127.0.0.1:1/forbidden")
                if failure == "chunked":
                    self.send_header("Transfer-Encoding", "chunked")
                body = encoded({"op": "finish", "extra": "must-not-pass"} if failure == "unknown-field"
                               else {"op": "read", "handle": "0" * 32, "offset": 0, "length": 1} if failure == "range"
                               else {"op": "finish"})
                self.send_header("Content-Length", str(1048577 if failure == "oversize" else len(body)))
                if failure == "duplicate-length":
                    self.send_header("Content-Length", "1")
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with fixture(f"http://127.0.0.1:{server.server_port}/broker") as f:
                denied(lambda: f.session().run(), "delivery_unknown", "egress_contract_invalid")
                assert len(captured) == 1
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    checks.append("A15 A26 redirects streaming oversized duplicate and range responses refused")

    with recipient() as (endpoint, capture):
        with fixture(endpoint) as f:
            f.policy["limits"]["disclosures"] = 2
            s = f.session()
            seed = s.prepare_view()
            s.dispatch(seed, s.authorize(seed))
            first, second = s.prepare_view(), s.prepare_view()
            tokens = [s.authorize(first), s.authorize(second)]
            barrier = threading.Barrier(2)
            outcomes = []
            def dispatch(view, token):
                barrier.wait()
                try:
                    s.dispatch(view, token)
                    outcomes.append("sent")
                except EgressError as exc:
                    outcomes.append(exc.code)
            threads = [threading.Thread(target=dispatch, args=pair) for pair in zip((first, second), tokens)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
                assert not thread.is_alive()
            assert outcomes.count("sent") == 1 and len(capture) == 2, outcomes
            assert set(outcomes) <= {"sent", "egress_busy", "attempt_budget_exceeded"}
            assert f.store.inspect(s.key)["disclosures"] == 2
            checks.append("A15 concurrent reservations never exceed persistent attempt budget")

        with fixture(endpoint) as f:
            s = f.session()
            view = s.prepare_view()
            # Same transport cannot be changed after preparation to append SDK text.
            s.transport.recipient["endpoint"] += "/extra"
            denied(lambda: s.authorize(view), "invalid_binding")
            checks.append("A26 mutable transport config invalidates binding")

        with fixture(endpoint) as f:
            s = f.session()
            s.tools["text-stats"] = TrustedTool(("text",), "pure", "public", "none", True,
                                                lambda args, credential=None: {"changed": True})
            denied(lambda: s.invoke_tool("text-stats", {"text": "Public"}), "tool_qualification_required")
            checks.append("A26 trusted tool code drift invalidates session")

    return {"status": "passed", "checks": len(checks), "cases": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_checks()
    print(json.dumps(result) if args.json else "PASS " + str(result["checks"]) + " transport checks")
