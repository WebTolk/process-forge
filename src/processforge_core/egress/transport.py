"""Exact finite HTTP/JSON transport; no ambient proxies, SDKs or redirects."""
from __future__ import annotations

import hashlib
import http.client
import os
from pathlib import Path
import platform
import ssl
import socket
import threading

from .contracts import EgressError, bounded_json, fingerprint, route

PROTOCOL = "pf.egress/1"


def _disk_identity():
    root = Path(__file__).parent
    payload = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))}
    core_root = root.parents[2]
    for name in ("src/processforge_core/work/context.py", "src/processforge_core/process_execution.py",
                 "src/processforge_core/prepared/input.py", "src/processforge_core/work/resource_material.py",
                 "tools/processforge.py", "tools/prepared_executor.py", "schemas/execution-contract.schema.json",
                 "tools/smoke_egress_engine.py", "tools/smoke_egress_work.py", "tools/smoke_egress_transport.py"):
        payload[name] = hashlib.sha256((core_root / name).read_bytes()).hexdigest()
    payload["environment"] = [os.name, platform.system(), platform.release(), platform.version(),
                              platform.python_version(), ssl.OPENSSL_VERSION]
    return fingerprint(payload)


LOADED_ID = _disk_identity()


def implementation_id():
    if _disk_identity() != LOADED_ID:
        raise EgressError("enforcement_unavailable")
    return LOADED_ID


def windows_tls_context():
    """OS trust store only: no SSLKEYLOGFILE, SSL_CERT_FILE or home configuration."""
    if os.name != "nt":
        raise EgressError("enforcement_unavailable")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    purpose = ssl.Purpose.SERVER_AUTH.oid
    certificates = []
    for store in ("ROOT", "CA"):
        for certificate, encoding, trust in ssl.enum_certificates(store):
            if encoding == "x509_asn" and (trust is True or purpose in trust):
                certificates.append(ssl.DER_cert_to_PEM_cert(certificate))
    if not certificates or len(certificates) > 4096:
        raise EgressError("tls_trust_unavailable")
    context.load_verify_locations(cadata="".join(certificates))
    return context


class JsonTransport:
    def __init__(self, recipient, *, credential=None):
        self.recipient = dict(recipient)
        self.url = route(recipient)
        self.credential = credential
        if credential is not None and (not isinstance(credential, str) or not 1 <= len(credential) <= 4096
                                       or any(ord(c) < 33 or ord(c) > 126 for c in credential)):
            raise EgressError("credential_channel_invalid")
        self.binding = fingerprint(recipient)
        self.tls = windows_tls_context() if self.url.scheme == "https" else None

    def exchange(self, raw: bytes, maximum: int) -> bytes:
        if fingerprint(self.recipient) != self.binding or route(self.recipient) != self.url:
            raise EgressError("invalid_binding")
        headers = {"Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(raw)),
                   "Connection": "close"}
        if self.credential is not None:
            headers["Authorization"] = "Bearer " + self.credential
        connection = (http.client.HTTPSConnection(self.url.hostname, self.url.port, timeout=5,
                                                  context=self.tls)
                      if self.url.scheme == "https" else http.client.HTTPConnection(self.url.hostname, self.url.port, timeout=5))
        timer, wire = None, None
        try:
            connection.connect()
            wire = connection.sock
            def interrupt():
                try:
                    wire.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            # Bound the whole response, including slow headers and trickled body;
            # a per-recv timeout alone would restart after each arriving byte.
            timer = threading.Timer(10, interrupt)
            timer.daemon = True
            timer.start()
            # http.client has no proxy discovery, redirect loop, retry or telemetry.
            connection.request("POST", self.url.path or "/", body=raw, headers=headers)
            response = connection.getresponse()
            if (response.status != 200 or response.getheader("Content-Encoding")
                    or response.getheader("Transfer-Encoding")
                    or (response.getheader("Content-Type") or "").split(";")[0].strip().lower() != "application/json"):
                raise EgressError("recipient_response_invalid")
            length = response.getheader("Content-Length")
            if length is None or not length.isdecimal() or not 0 <= int(length) <= maximum:
                raise EgressError("recipient_response_invalid")
            result = response.read(int(length) + 1)
            if len(result) != int(length):
                raise EgressError("recipient_response_invalid")
            bounded_json(result, maximum)
            return result
        finally:
            if timer:
                timer.cancel()
            connection.close()
