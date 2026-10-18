"""Private mandatory receipts, revocations and persistent budget reservations."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import secrets
import time

from .contracts import EgressError, PRIVATE_COMPONENT, bounded_json, encoded, fingerprint
from .windows import private_directory, verify_private

MAX_STATE = 1048576
RETENTION_SECONDS = 30 * 24 * 3600


class Store:
    def __init__(self, root: Path, project: Path):
        self.root = root.absolute()
        if (self.root.name != PRIVATE_COMPONENT or self.root.resolve().is_relative_to(project.resolve())
                or len(str(self.root)) > 200):
            raise EgressError("private_store_location_invalid")
        private_directory(self.root)

    def path(self, name):
        if not re.fullmatch(r"(?:[a-f0-9]{64}\.(?:json|ndjson)|revocations\.json|qualification\.json|store\.lock)", name):
            raise EgressError("private_store_invalid")
        return self.root / name

    @contextmanager
    def locked(self):
        import msvcrt
        verify_private(self.root, directory=True)
        path = self.path("store.lock")
        if path.exists():
            verify_private(path)
        with path.open("a+b") as stream:
            verify_private(path)
            if path.stat().st_size == 0:
                stream.write(b"\x00")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise EgressError("egress_busy") from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)

    def load(self, name, default=None):
        path = self.path(name)
        if not path.exists():
            return default
        verify_private(path)
        with path.open("rb") as stream:
            raw = stream.read(MAX_STATE + 1)
        return bounded_json(raw, MAX_STATE)

    def write(self, name, value):
        path = self.path(name)
        if path.exists():
            verify_private(path)
        raw = encoded(value)
        if len(raw) > MAX_STATE:
            raise EgressError("audit_unavailable")
        temporary = self.root / (".write-" + secrets.token_hex(16))
        try:
            with temporary.open("xb") as stream:
                verify_private(temporary)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            verify_private(path)
        except OSError:
            raise EgressError("audit_unavailable") from None
        finally:
            temporary.unlink(missing_ok=True)

    def audit(self, attempt, event):
        path = self.path(attempt + ".ndjson")
        if path.exists():
            verify_private(path)
            if path.stat().st_size > 8 * 1048576:
                raise EgressError("audit_unavailable")
        raw = encoded({"time": int(time.time()), **event}) + b"\n"
        if len(raw) > 65536:
            raise EgressError("audit_unavailable")
        try:
            with path.open("ab") as stream:
                verify_private(path)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            raise EgressError("audit_unavailable") from None

    def denied(self, binding, sources=(), tools=()):
        revocations = self.load("revocations.json", {"bindings": [], "sources": [], "tools": []})
        return (fingerprint(binding) in revocations["bindings"]
                or any(fingerprint([binding, x]) in revocations["sources"] for x in sources)
                or any(fingerprint([binding, x]) in revocations["tools"] for x in tools))

    def revoke(self, binding, *, source=None, tool=None):
        with self.locked():
            value = self.load("revocations.json", {"bindings": [], "sources": [], "tools": []})
            key = "sources" if source is not None else "tools" if tool is not None else "bindings"
            item = fingerprint([binding, source if source is not None else tool]) if key != "bindings" else fingerprint(binding)
            if item not in value[key]:
                value[key].append(item)
            self.write("revocations.json", value)

    def inspect(self, attempt):
        with self.locked():
            value = self.load(attempt + ".json")
            if value is None:
                raise EgressError("attempt_unknown")
            # Never infer non-delivery from a crash or an absent final receipt.
            for receipt in value["receipts"]:
                if receipt["status"] == "dispatching":
                    receipt["status"] = "delivery_unknown"
            return value

    def prune(self):
        """Remove only expired receipt bodies; permanent opaque budget tombstones remain."""
        count = 0
        with self.locked():
            entries = list(self.root.iterdir())
            if len(entries) > 4096:
                raise EgressError("retention_budget_exceeded")
            now = time.time()
            for path in entries:
                if re.fullmatch(r"[a-f0-9]{64}\.ndjson", path.name):
                    verify_private(path)
                    if now - path.stat().st_mtime > RETENTION_SECONDS:
                        path.unlink()
                        count += 1
        return count
