"""Optional bounded diagnostics. Never use this module for required evidence."""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import math
import os
import re
import stat
import sys
import threading
import time
import uuid
from itertools import islice
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator

LEVELS = dict(debug=10, info=20, notice=25, warning=30, error=40,
              critical=50, alert=60, emergency=70)
PROFILES = dict(quiet="warning", normal="info", diagnostic="debug", trace="debug", off="emergency")
LIMITS = dict(record_bytes=16384, string_chars=2048, depth=6, items=32,
              stack_frames=8, spans=32, file_bytes=1048576, quota_bytes=8388608,
              files=8, retention_seconds=604800, detail_records=10000)
DEFAULTS = dict(schema_version=1, profile="normal", threshold="info", components=[],
                sink="jsonl", expires_at=None, sample_every=1, **LIMITS)
SECRET_KEY = re.compile(r"password|passwd|secret|token|credential|authorization|cookie|api.?key|private.?key|access.?key|headers", re.I)
OMIT_KEY = re.compile(r"prompt|payload|environment|(?:^|[_-])env(?:$|[_-])|(?:^|[_-])content(?:$|[_-])|file.?contents?|source.?code", re.I)
SECRET_TEXT = [
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9_./+=-]+"),
    re.compile(r"(?i)(?:password|passwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*(?:\"[^\"\n]*\"|'[^'\n]*'|[^\s,;}]+)"),
    re.compile(r"https?://[^\s/@:]+:[^\s/@]+@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", re.S),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{12,})\b"),
]
ABS_PATH = re.compile(r"(?<![\w:/])(?:file://|[A-Za-z]:[\\/]|/(?!/))[^\r\n]*", re.I)
_CURRENT: contextvars.ContextVar[Any] = contextvars.ContextVar("pf_diagnostic", default=None)
_IDENTITY: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("pf_diagnostic_identity", default={})
_CACHE: OrderedDict[Any, Any] = OrderedDict()
_CACHE_LOCK = threading.RLock()
_IO_LOCK = threading.RLock()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def severity(level: str) -> int:
    if not isinstance(level, str) or level not in LEVELS:
        raise ValueError("unknown diagnostic severity")
    return LEVELS[level]


def _epoch(value: Any) -> float:
    if not isinstance(value, str):
        raise ValueError("expires_at must be a UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("expires_at must include timezone")
    return parsed.timestamp()


def resolve_config(*layers: tuple[str, dict[str, Any]], now: float | None = None) -> dict[str, Any]:
    """Resolve policy without IO. Invalid input is explicit; factories fail safely."""
    now = time.time() if now is None else now
    values, sources, locked = dict(DEFAULTS), dict.fromkeys(DEFAULTS, "defaults"), set()
    values["components"] = []
    for source, layer in layers:
        if not isinstance(layer, dict) or set(layer) - set(DEFAULTS) - {"locked"}:
            raise ValueError("unknown diagnostic configuration field")
        if layer.get("schema_version", 1) != 1 or type(layer.get("schema_version", 1)) is not int:
            raise ValueError("unsupported diagnostic configuration version")
        if "locked" in layer and (not isinstance(layer["locked"], list) or any(k not in DEFAULTS for k in layer["locked"])):
            raise ValueError("invalid locked diagnostic fields")
        updates = dict(layer)
        if "profile" in updates:
            if updates["profile"] not in PROFILES:
                raise ValueError("unknown diagnostic profile")
            updates.setdefault("threshold", PROFILES[updates["profile"]])
        for key, value in updates.items():
            if key == "locked":
                continue
            if key in locked and value != values[key]:
                raise ValueError("locked diagnostic field: " + key)
            if key in LIMITS:
                if type(value) is not int or not 1 <= value <= values[key]:
                    raise ValueError("diagnostic limit cannot be relaxed: " + key)
            if key == "threshold":
                severity(value)
            if key == "sink" and value not in {"jsonl", "stderr", "both", "none"}:
                raise ValueError("unknown diagnostic sink")
            if key == "components" and (not isinstance(value, list) or len(value) > 32 or any(not isinstance(s, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", s) for s in value)):
                raise ValueError("invalid diagnostic components")
            if key == "sample_every" and (type(value) is not int or not 1 <= value <= 10000):
                raise ValueError("invalid diagnostic sampling")
            if key == "expires_at" and value is not None:
                _epoch(value)
            values[key], sources[key] = value, source
        locked.update(layer.get("locked", []))
    if values["record_bytes"] < 512 or values["file_bytes"] < values["record_bytes"] or values["quota_bytes"] < values["file_bytes"]:
        raise ValueError("diagnostic record/file/quota limits do not fit")
    detailed = values["profile"] in {"diagnostic", "trace"} or LEVELS[values["threshold"]] < LEVELS["info"]
    if detailed and (values["expires_at"] is None or _epoch(values["expires_at"]) > now + 900):
        raise ValueError("diagnostic detail needs expires_at within 15 minutes")
    return {"values": values, "sources": sources, "locked": sorted(locked), "errors": []}


class Sanitizer:
    def __init__(self, limits: dict[str, Any], secrets: tuple[str, ...] = (), *, export: bool = False):
        self.limits = limits
        self.secrets = [s for s in secrets if isinstance(s, str) and s][:256]
        self.export = export
        self.redacted = 0
        self.truncated = 0
        self._nodes = 0
        self._collect_nodes = 0

    def text(self, value: str) -> str:
        # Bound scanning before regex/conversion. No sliced-away data is emitted.
        maximum = self.limits["string_chars"]
        if len(value) > maximum:
            value = value[:maximum]
            self.truncated += 1
        for secret in self.secrets:
            if secret in value:
                value = value.replace(secret, "<redacted>")
                self.redacted += 1
        for pattern in SECRET_TEXT:
            value, count = pattern.subn("<redacted>", value)
            self.redacted += count
        if self.export:
            value, count = ABS_PATH.subn("<private-path>", value)
            self.redacted += count
        return value[:maximum]

    def collect(self, value: Any, depth: int = 0) -> None:
        self._collect_nodes += 1
        if depth > self.limits["depth"] or len(self.secrets) >= 256 or self._collect_nodes > 512:
            return
        if type(value) is dict:
            for key, item in islice(value.items(), self.limits["items"]):
                if isinstance(key, str) and SECRET_KEY.search(key) and type(item) is str and item:
                    self.secrets.append(item[:self.limits["string_chars"]])
                else:
                    self.collect(item, depth + 1)
        elif type(value) in (list, tuple):
            for item in value[:self.limits["items"]]:
                self.collect(item, depth + 1)

    def clean(self, value: Any, depth: int = 0) -> Any:
        self._nodes += 1
        if depth > self.limits["depth"] or self._nodes > 512:
            self.truncated += 1
            return "<truncated>"
        if value is None or type(value) is bool:
            return value
        if type(value) is int:
            return value if value.bit_length() < 128 else "<large-integer>"
        if type(value) is float:
            return value if math.isfinite(value) else "<non-finite>"
        if type(value) is str:
            return self.text(value)
        if type(value) is dict:
            out = {}
            for i, (key, item) in enumerate(value.items()):
                if i >= self.limits["items"]:
                    self.truncated += 1
                    break
                name = self.text(key) if type(key) is str else "<non-string-key>"
                normalized_name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
                if SECRET_KEY.search(name) or OMIT_KEY.search(normalized_name):
                    out[name] = "<redacted>"
                    self.redacted += 1
                else:
                    out[name] = self.clean(item, depth + 1)
            return out
        if type(value) in (list, tuple):
            if len(value) > self.limits["items"]:
                self.truncated += 1
            return [self.clean(item, depth + 1) for item in value[:self.limits["items"]]]
        if isinstance(value, BaseException):
            # Exception strings can execute user code. Failure stays contained.
            try:
                message = self.text(str(value))
            except BaseException:
                message = "<unprintable>"
            frames, tb = [], value.__traceback__
            while tb and len(frames) < self.limits["stack_frames"]:
                frames.append({"file": self.text(tb.tb_frame.f_code.co_filename),
                               "function": self.text(tb.tb_frame.f_code.co_name), "line": tb.tb_lineno})
                tb = tb.tb_next
            return {"type": type(value).__name__, "message": message, "frames": frames}
        return "<" + type(value).__name__[:80] + ">"


def encode(record: Any) -> bytes:
    return (json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


@contextlib.contextmanager
def _file_lock(root: Path) -> Iterator[None]:
    path = root / ".diagnostics.lock"
    if path.is_symlink():
        raise OSError("diagnostic lock symlink")
    with _IO_LOCK, path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + 0.05
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.005)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def log_files(root: Path) -> list[Path]:
    return [root / "diagnostics.jsonl", *[root / f"diagnostics.{i}.jsonl" for i in range(1, 8)]]


class JsonlSink:
    def __init__(self, root: Path, limits: dict[str, Any]):
        self.root, self.limits = root, limits
        self._initialized = False
        self._birthmarks: dict[str, tuple[int, float]] = {}

    def __call__(self, record: dict[str, Any]) -> None:
        data = encode(record)
        if len(data) > self.limits["record_bytes"]:
            raise ValueError("diagnostic record exceeds byte limit")
        if not self._initialized:
            if any(p.is_symlink() for p in (self.root, self.root.parent, self.root.parent.parent)):
                raise OSError("diagnostic directory symlink")
            self.root.mkdir(parents=True, exist_ok=True)
            self._initialized = True
        with _file_lock(self.root):
            files = log_files(self.root)
            names = {path.name: i for i, path in enumerate(files)}
            sizes = {}
            now = time.time()
            with os.scandir(self.root) as entries:
                for entry in entries:
                    if entry.name not in names:
                        continue
                    if entry.is_symlink():
                        raise OSError("diagnostic file symlink")
                    stat = entry.stat()
                    index = names[entry.name]
                    cached = self._birthmarks.get(entry.name)
                    if cached is None or cached[0] != stat.st_ino:
                        first_time = stat.st_mtime
                        try:
                            with files[index].open("rb") as handle:
                                first_time = _epoch(json.loads(handle.readline(16385))["timestamp"])
                        except (OSError, ValueError, KeyError, TypeError):
                            pass
                        cached = (stat.st_ino, first_time)
                        self._birthmarks[entry.name] = cached
                    if index >= self.limits["files"] or now - min(stat.st_mtime, cached[1]) > self.limits["retention_seconds"]:
                        files[index].unlink()
                        self._birthmarks.pop(entry.name, None)
                    else:
                        sizes[index] = stat.st_size
            active = files[0]
            if sizes.get(0, 0) + len(data) > self.limits["file_bytes"]:
                for index in sorted(sizes, reverse=True):
                    size = sizes.pop(index)
                    if index + 1 >= self.limits["files"]:
                        files[index].unlink()
                    else:
                        files[index].replace(files[index + 1])
                        sizes[index + 1] = size
            total = sum(sizes.values())
            for index in sorted(sizes, reverse=True):
                if index and total + len(data) > self.limits["quota_bytes"]:
                    files[index].unlink()
                    total -= sizes.pop(index)
            if total + len(data) > self.limits["quota_bytes"]:
                raise OSError("diagnostic quota exceeded")
            with active.open("ab") as handle:
                handle.write(data)


def stderr_sink(record: dict[str, Any]) -> None:
    sys.stderr.write(encode(record).decode("utf-8"))


class Logger:
    def __init__(self, config: dict[str, Any] | None = None, *, root: Path | None = None,
                 sinks: list[Callable] | None = None, secrets: tuple[str, ...] = ()):
        self.config = config or resolve_config()
        self.values = self.config["values"]
        self.secrets = secrets
        self.health = dict(emitted=0, filtered=0, dropped=0, sink_failures=0,
                           serialization_failures=0, truncated=0, detail_expired=0)
        self.detail_count = 0
        self._seen_debug = 0
        self._last_warning = float("-inf")
        self._lock = threading.RLock()
        self.sinks = list(sinks) if sinks is not None else []
        if sinks is None:
            if root is not None and self.values["sink"] in {"jsonl", "both"}:
                self.sinks.append(JsonlSink(root, self.values))
            if self.values["sink"] in {"stderr", "both"}:
                self.sinks.append(stderr_sink)

    def effective(self) -> dict[str, Any]:
        values = dict(self.values)
        detailed = values["profile"] in {"diagnostic", "trace"} or LEVELS[values["threshold"]] < 20
        if detailed and (time.time() >= _epoch(values["expires_at"]) or self.detail_count >= values["detail_records"]):
            values.update(profile="normal", threshold="info")
        return {**self.config, "values": values, "detail_expired": detailed and values["profile"] == "normal", "health": dict(self.health)}

    def enabled(self, level: str, component: str = "core") -> bool:
        number = severity(level)
        if self.values["profile"] == "off" or not self.sinks:
            return False
        effective = self.effective()["values"]
        return number >= LEVELS[effective["threshold"]] and (not effective["components"] or component in effective["components"])

    def _failure(self, kind: str, level: str) -> None:
        self.health[kind] += 1
        self.health["dropped"] += 1
        if LEVELS[level] >= 40 and time.monotonic() - self._last_warning >= 60:
            self._last_warning = time.monotonic()
            try:
                sys.stderr.write("PF diagnostic_delivery_failed: optional serious record lost; inspect diagnostics health.\n")
            except Exception:
                pass

    def log(self, level: str, message: str, context: Any = None, *, component: str = "core", code: str = "diagnostic") -> dict[str, Any] | None:
        severity(level)  # programmer error stays explicit, including no-op
        if not self.enabled(level, component):
            self.health["filtered"] += 1
            return None
        with self._lock:
            if level == "debug":
                self._seen_debug += 1
                if self._seen_debug % self.values["sample_every"]:
                    self.health["dropped"] += 1
                    return None
            try:
                if callable(context):
                    context = context()
                clean = Sanitizer(self.values, self.secrets)
                clean.collect(context)
                sanitized = clean.clean(context if context is not None else {})
                identity = clean.clean(dict(_IDENTITY.get()))
                template = clean.text(message) if type(message) is str else "<message>"
                rendered = template
                if isinstance(sanitized, dict):
                    for key, value in sanitized.items():
                        if value is None or type(value) in (str, int, float, bool):
                            rendered = rendered.replace("{" + key + "}", str(value))
                record = {"schema_version": 1, "timestamp": utc(), "severity": level,
                          "python_level": LEVELS[level], "component": clean.text(component),
                          "code": clean.text(code), "message": clean.text(rendered),
                          "template": template, "context": sanitized, "identity": identity,
                          "redacted": clean.redacted, "truncated": clean.truncated, "health": dict(self.health)}
                if len(encode(record)) > self.values["record_bytes"]:
                    record.update(context={"detail": "<record-truncated>"}, message=record["message"][:128],
                                  template=record["template"][:128], truncated=record["truncated"] + 1)
                    if len(encode(record)) > self.values["record_bytes"]:
                        record["identity"] = {k: v[:80] if isinstance(v, str) else v for k, v in identity.items() if k in {"request_id", "run_id", "session_id"}}
                    if len(encode(record)) > self.values["record_bytes"]:
                        raise ValueError("minimum diagnostic envelope exceeds limit")
            except BaseException:
                self._failure("serialization_failures", level)
                return None
            for sink in self.sinks:
                try:
                    sink(record)
                except BaseException:
                    self._failure("sink_failures", level)
            self.health["emitted"] += 1
            self.health["truncated"] += record["truncated"]
            if LEVELS[level] < 20 or self.values["profile"] in {"diagnostic", "trace"}:
                self.detail_count += 1
            if self.effective()["detail_expired"]:
                self.health["detail_expired"] = 1
            return record


def _level_method(level: str) -> Callable:
    def method(self: Logger, message: str, context: Any = None, **kwargs: Any) -> Any:
        return self.log(level, message, context, **kwargs)
    return method


for _level in LEVELS:
    setattr(Logger, _level, _level_method(_level))


class NullLogger(Logger):
    def __init__(self) -> None:
        super().__init__(resolve_config(("invocation", {"profile": "off", "sink": "none"})))


NULL = NullLogger()


def current() -> Logger:
    return _CURRENT.get() or NULL


def emit(level: str, code: str, context: Any = None, *, component: str = "core") -> Any:
    return current().log(level, code, context, component=component, code=code)


def annotate(**identity: Any) -> None:
    if _CURRENT.get() is not None:
        _IDENTITY.set({**_IDENTITY.get(), **identity})


def select_work(project: Path, run_id: str, assignment_id: str | None = None) -> None:
    """Bind only a Work already selected by the application, never infer one."""
    logger = current()
    annotate(run_id=run_id, assignment_id=assignment_id)
    if getattr(logger, "project", None) == project:
        _CURRENT.set(for_project(project, run_id=run_id, session_id=_IDENTITY.get().get("session_id"),
                                 invocation=logger.invocation))


def invocation_options(profile: str | None = None, threshold: str | None = None,
                       components: str | None = None, sink: str | None = None) -> dict[str, Any]:
    result = {k: v for k, v in dict(profile=profile, threshold=threshold, sink=sink).items() if v is not None}
    if components is not None:
        result["components"] = [c.strip() for c in components.split(",") if c.strip()]
    if profile in {"diagnostic", "trace"} or threshold == "debug":
        result["expires_at"] = datetime.fromtimestamp(time.time() + 600, timezone.utc).isoformat()
    return result


def _read_config(path: Path) -> dict[str, Any]:
    for item in (path, path.parent):
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("diagnostic config path is linked")
    if not path.exists():
        return {}
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > 65536:
        raise ValueError("diagnostic config is not a bounded regular file")
    with path.open("rb") as handle:
        raw = handle.read(65537)
    if len(raw) > 65536:
        raise ValueError("diagnostic config is too large")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("diagnostic config must be an object")
    return result


def configuration(project: Path, *, run_id: str | None = None, session_id: str | None = None,
                  invocation: dict[str, Any] | None = None) -> dict[str, Any]:
    document = _read_config(project / ".pf" / "diagnostics.json")
    return configuration_document(document, run_id=run_id, session_id=session_id, invocation=invocation)


def configuration_document(document, *, run_id=None, session_id=None, invocation=None, now=None):
    document = dict(document)
    work = document.pop("work", {})
    sessions = document.pop("sessions", {})
    if not isinstance(work, dict) or not isinstance(sessions, dict):
        raise ValueError("diagnostic scope overrides must be objects")
    env = os.environ.get("PF_DIAGNOSTICS", "")
    if len(env) > 65536:
        raise ValueError("diagnostic invocation config too large")
    override = json.loads(env) if env else {}
    # CLI overrides are a distinct layer: they cannot hide environment locks.
    return resolve_config(("project", document), ("work", work.get(run_id, {}) if run_id else {}),
                          ("session", sessions.get(session_id, {}) if session_id else {}),
                          ("environment", override), ("invocation", invocation or {}), now=now)


def configure_proposal(document, profile, *, duration=600, run_id=None, session_id=None, invocation=None, now=None):
    """Pure bounded v1 edit. Existing locks apply even within the edited layer."""
    now = time.time() if now is None else now
    if profile not in PROFILES or type(duration) is not int or not 1 <= duration <= 900:
        raise ValueError("profile/duration invalid; duration must be 1..900 seconds")
    if run_id and session_id:
        raise ValueError("choose one target scope")
    for identifier in (run_id, session_id):
        if identifier is not None and (not isinstance(identifier, str) or not 1 <= len(identifier) <= 256 or any(ord(c) < 32 for c in identifier)):
            raise ValueError("invalid target identifier")
    if not isinstance(document, dict) or len(encode(document)) > 65536:
        raise ValueError("invalid bounded diagnostic document")
    proposed = json.loads(json.dumps(document))
    project = {k: v for k, v in document.items() if k not in {"work", "sessions"}}
    resolve_config(("project", project), now=now)
    for name in ("work", "sessions"):
        scopes = document.get(name, {})
        if not isinstance(scopes, dict):
            raise ValueError("invalid diagnostic scopes")
        for key, value in scopes.items():
            if not isinstance(key, str) or not key:
                raise ValueError("invalid diagnostic scope key")
            resolve_config(("project", project), (name, value), now=now)
    scope, identifier = ("work", run_id) if run_id else ("sessions", session_id) if session_id else ("project", None)
    target = project if identifier is None else document.get(scope, {}).get(identifier, {})
    layers = [("project", project)] + ([(scope, target)] if identifier else [])
    change = {"profile": profile, "threshold": PROFILES[profile],
              "expires_at": datetime.fromtimestamp(now + duration, timezone.utc).isoformat() if profile in {"diagnostic", "trace"} else None}
    resolve_config(*layers, ("requested_change", change), now=now)
    if identifier:
        proposed.setdefault(scope, {}).setdefault(identifier, {}).update(change)
    else:
        proposed.update(change)
    new_project = {k: v for k, v in proposed.items() if k not in {"work", "sessions"}}
    for name in ("work", "sessions"):
        for value in proposed.get(name, {}).values():
            resolve_config(("project", new_project), (name, value), now=now)
    effective = configuration_document(proposed, run_id=run_id, session_id=session_id, invocation=invocation, now=now)
    if len(encode(proposed)) > 65536:
        raise ValueError("diagnostic config output exceeds limit")
    return proposed, {"schema_version": 1, "scope": scope, "target": identifier,
                      "change": change, "effective": effective}


@lru_cache(maxsize=16)
def _build_identity(entry: str | Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    result = {"core_version": "unknown"}
    try:
        result["diagnostics_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        result["core_version"] = (root / "VERSION").read_text(encoding="utf-8").strip()[:80]
        result["entry_sha256"] = hashlib.sha256(Path(entry or __file__).read_bytes()).hexdigest()
    except OSError:
        result["source_status"] = "unavailable"
    return result


def build_identity(entry: str | Path | None = None) -> dict[str, Any]:
    return dict(_build_identity(entry))


def identity_for(logger: Logger, entry: str | Path) -> dict[str, Any] | None:
    # Off/none must not read source files to construct unused diagnostic context.
    return build_identity(entry) if logger.values["profile"] != "off" and logger.sinks else None


def for_project(project: Path | None, *, run_id: str | None = None, session_id: str | None = None,
                invocation: dict[str, Any] | None = None) -> Logger:
    try:
        return _for_project(project, run_id=run_id, session_id=session_id, invocation=invocation)
    except Exception:
        try:
            sys.stderr.write("PF diagnostic_setup_failed: optional diagnostics disabled.\n")
        except Exception:
            pass
        return NULL


def _for_project(project: Path | None, *, run_id: str | None = None, session_id: str | None = None,
                 invocation: dict[str, Any] | None = None) -> Logger:
    if project is None or not (project / ".pf").is_dir() or (project / ".pf").is_symlink():
        return NULL
    try:
        config = configuration(project, run_id=run_id, session_id=session_id, invocation=invocation)
    except Exception as exc:
        config = resolve_config(("fallback", {"profile": "off", "sink": "none"}))
        config["errors"] = ["diagnostics_config_invalid:" + type(exc).__name__]
    key = (str(project.resolve()), run_id, session_id, json.dumps(config, sort_keys=True))
    with _CACHE_LOCK:
        if key not in _CACHE:
            secrets = tuple(value for name, value in os.environ.items() if SECRET_KEY.search(name) and value)[:256]
            logger = Logger(config, root=project / ".pf" / "runtime" / "diagnostics", secrets=secrets)
            logger.project, logger.invocation = project, invocation or {}
            _CACHE[key] = logger
            if config["errors"]:
                try:
                    sys.stderr.write("PF diagnostics_config_invalid: optional diagnostics disabled; inspect configuration.\n")
                except Exception:
                    pass
            while len(_CACHE) > 32:
                _CACHE.popitem(last=False)
        else:
            _CACHE.move_to_end(key)
        return _CACHE[key]


def for_stderr(invocation: dict[str, Any]) -> Logger:
    """Unscoped adapter failure diagnostics; no project files are created."""
    try:
        env = os.environ.get("PF_DIAGNOSTICS", "")
        if len(env) > 65536:
            raise ValueError("diagnostic invocation config too large")
        config = resolve_config(("adapter", {"sink": "stderr"}), ("environment", json.loads(env) if env else {}), ("invocation", invocation))
        secrets = tuple(value for name, value in os.environ.items() if SECRET_KEY.search(name) and value)[:256]
        return Logger(config, secrets=secrets)
    except Exception:
        return NULL


@contextlib.contextmanager
def operation(logger: Logger, component: str, code: str, **identity: Any) -> Iterator[Logger]:
    base = dict(_IDENTITY.get())
    base.update(identity)
    base.setdefault("request_id", str(uuid.uuid4()))
    base.setdefault("session_id", None)
    token, identity_token = _CURRENT.set(logger), _IDENTITY.set(base)
    started = time.perf_counter()
    logger.debug("operation.started", component=component, code=code + ".started")
    try:
        yield logger
    except BaseException as exc:
        current().error("operation.failed", {"exception": exc, "duration_ms": round((time.perf_counter() - started) * 1000, 3)}, component=component, code=code + ".failed")
        raise
    else:
        current().info("operation.completed", {"duration_ms": round((time.perf_counter() - started) * 1000, 3)}, component=component, code=code + ".completed")
    finally:
        _IDENTITY.reset(identity_token)
        _CURRENT.reset(token)


@contextlib.contextmanager
def span(code: str, context: Any = None, *, component: str = "core") -> Iterator[None]:
    logger = current()
    identity = _IDENTITY.get()
    count = identity.get("span_count", 0)
    if logger.effective()["values"]["profile"] != "trace" or count >= logger.values["spans"]:
        yield
        return
    identity["span_count"] = count + 1
    start = time.perf_counter()
    emit("debug", code + ".span_start", context, component=component)
    try:
        yield
    finally:
        emit("debug", code + ".span_end", {"duration_ms": round((time.perf_counter() - start) * 1000, 3)}, component=component)


def export_bundle(project: Path, output: Path, *, request_id: str | None = None, run_id: str | None = None,
                  since: str | None = None, until: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read known logs only, filter, sanitize, and exclusively create a local bundle."""
    lower, upper = _epoch(since) if since else float("-inf"), _epoch(until) if until else float("inf")
    if lower > upper:
        raise ValueError("invalid diagnostic time interval")
    root = project / ".pf" / "runtime" / "diagnostics"
    if output.resolve() in {p.resolve() for p in log_files(root)} or output.name == ".diagnostics.lock":
        raise ValueError("diagnostic export destination overlaps log storage")
    cleaner = Sanitizer(DEFAULTS, export=True)
    try:
        config = configuration(project, run_id=run_id)
    except Exception as exc:
        raise ValueError("diagnostics_config_invalid:" + type(exc).__name__) from None
    retention_cutoff = time.time() - config["values"]["retention_seconds"]
    records, manifest = [], []
    consumed, truncated, rejected, expired = 0, False, 0, 0
    for path in reversed(log_files(root)):
        if not path.exists():
            continue
        if any(p.is_symlink() for p in (path, root, root.parent, root.parent.parent)) or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("diagnostic export refuses linked inputs")
        if path.stat().st_mtime < retention_cutoff:
            manifest.append({"name": path.name, "excluded": "retention_expired"})
            continue
        digest, read_bytes = hashlib.sha256(), 0
        with path.open("rb") as handle:
            while consumed < 4 * 1024 * 1024 and len(records) < 2000:
                line = handle.readline(min(16385, 4 * 1024 * 1024 - consumed))
                if not line:
                    break
                consumed += len(line)
                read_bytes += len(line)
                digest.update(line)
                if len(line) > 16384 or not line.endswith(b"\n"):
                    rejected += 1
                    truncated = True
                    break
                try:
                    record = json.loads(line)
                    identity = record.get("identity", {})
                    if request_id and str(identity.get("request_id")) != str(request_id):
                        continue
                    if run_id and identity.get("run_id") != run_id:
                        continue
                    record_time = _epoch(record["timestamp"])
                    if record_time < retention_cutoff:
                        expired += 1
                        continue
                    if not lower <= record_time <= upper:
                        continue
                    cleaner._nodes = 0
                    cleaner.collect(record)
                    records.append(cleaner.clean(record))
                except (ValueError, TypeError, KeyError, AttributeError):
                    rejected += 1
            if handle.read(1):
                truncated = True
        manifest.append({"name": path.name, "read_bytes": read_bytes, "read_sha256": digest.hexdigest()})
        if consumed >= 4 * 1024 * 1024 or len(records) >= 2000:
            truncated = True
            break
    cleaner._nodes = 0
    safe_metadata = cleaner.clean(metadata or {})
    cleaner._nodes = 0
    bundle = {"schema_version": 1, "kind": "processforge.diagnostics.bundle", "created_at": utc(),
              "recipient": "local-operator-sanitized", "read_only": True, "build": build_identity(),
              "filters": cleaner.clean({"request_id": request_id, "run_id": run_id, "since": since, "until": until}),
              "effective_configuration": cleaner.clean(config), "metadata": safe_metadata,
              "manifest": manifest, "records": records, "redaction": "secrets-and-private-paths",
              "redacted_values": cleaner.redacted, "truncated_values": cleaner.truncated,
              "truncated": truncated or bool(cleaner.truncated) or any(r.get("truncated") for r in records),
              "rejected_records": rejected, "expired_records": expired}
    while len(encode(bundle)) > 4 * 1024 * 1024 and bundle["records"]:
        bundle["records"].pop()
        bundle["truncated"] = True
    with output.open("xb") as handle:
        handle.write(encode(bundle))
    return {"path": str(output), "records": len(bundle["records"]), "truncated": bundle["truncated"],
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
