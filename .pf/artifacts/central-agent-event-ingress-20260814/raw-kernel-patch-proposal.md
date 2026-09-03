## Raw Kernel Patch Proposal

```diff
diff --git a/tools/pf_runtime/raw_ingress_kernel.py b/tools/pf_runtime/raw_ingress_kernel.py
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/tools/pf_runtime/raw_ingress_kernel.py
@@ -0,0 +1,646 @@
+from __future__ import annotations
+
+import hashlib
+import json
+import math
+import os
+import tempfile
+import time
+import unicodedata
+from dataclasses import asdict, dataclass, field
+from datetime import datetime, timezone
+from pathlib import Path
+from typing import Any, Dict, Mapping, Optional, Tuple, Union
+
+_NATIVE_ID_SCOPES = {"provider", "adapter", "session", "project"}
+_IDENTITY_CONTRACT = "processforge.raw-identity.v1"
+_NATIVE_IDENTITY_CONTRACT = "processforge.native-identity.v1"
+_DERIVED_ID_CONTRACT = "processforge.derived-id.v1"
+
+JsonObject = Mapping[str, Any]
+PathLikeStr = Union[os.PathLike, str]
+
+
+@dataclass(frozen=True)
+class NativeAgentEvent:
+    """Provider-native event envelope accepted by the raw ingress kernel."""
+
+    provider: str
+    adapter: str
+    native_event_type: str
+    raw_payload: JsonObject
+    payload_version: str = "1"
+    native_event_id: Optional[str] = None
+    native_id_scope: str = "provider"
+    native_event_id_stable: bool = True
+    source_session_id: Optional[str] = None
+    source_project_ref: Optional[str] = None
+    correlation: Optional[JsonObject] = None
+
+
+@dataclass(frozen=True)
+class RawReceipt:
+    """Durable raw-ingress decision returned to transports and routers."""
+
+    raw_event_id: Optional[str]
+    accepted: bool
+    deduplicated: bool
+    raw_location: Optional[str]
+    normalized_event_ids: Tuple[str, ...] = field(default_factory=tuple)
+    chat_message_ids: Tuple[str, ...] = field(default_factory=tuple)
+    routing_status: str = "raw_accepted"
+    diagnostics: Dict[str, Any] = field(default_factory=dict)
+
+    def to_dict(self) -> Dict[str, Any]:
+        data = asdict(self)
+        data["normalized_event_ids"] = list(self.normalized_event_ids)
+        data["chat_message_ids"] = list(self.chat_message_ids)
+        return data
+
+
+class RawIngressError(ValueError):
+    """Raised when the event envelope cannot be accepted before raw receipt."""
+
+
+class PathContainmentError(RawIngressError):
+    """Raised when a computed storage path escapes the configured root."""
+
+
+class FileLock:
+    """Small cross-process lock based on atomic lock-file creation."""
+
+    def __init__(
+        self,
+        path: Path,
+        *,
+        timeout_seconds: float = 10.0,
+        poll_seconds: float = 0.05,
+        stale_seconds: float = 300.0,
+    ) -> None:
+        self.path = path
+        self.timeout_seconds = timeout_seconds
+        self.poll_seconds = poll_seconds
+        self.stale_seconds = stale_seconds
+        self._fd: Optional[int] = None
+
+    def __enter__(self) -> "FileLock":
+        self.path.parent.mkdir(parents=True, exist_ok=True)
+        deadline = time.monotonic() + self.timeout_seconds
+        payload = f"pid={os.getpid()} acquired_at={time.time()}\n".encode("ascii")
+        while True:
+            try:
+                self._fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
+                os.write(self._fd, payload)
+                os.fsync(self._fd)
+                return self
+            except FileExistsError:
+                self._remove_stale_lock()
+                if time.monotonic() >= deadline:
+                    raise TimeoutError(f"timed out waiting for lock: {self.path}")
+                time.sleep(self.poll_seconds)
+
+    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
+        if self._fd is not None:
+            os.close(self._fd)
+            self._fd = None
+        try:
+            self.path.unlink()
+        except FileNotFoundError:
+            pass
+
+    def _remove_stale_lock(self) -> None:
+        try:
+            age = time.time() - self.path.stat().st_mtime
+        except FileNotFoundError:
+            return
+        if age <= self.stale_seconds:
+            return
+        try:
+            self.path.unlink()
+        except FileNotFoundError:
+            pass
+
+
+def contained_path(root: PathLikeStr, *parts: PathLikeStr) -> Path:
+    """Return a normalized path and reject traversal outside root."""
+
+    root_path = Path(root).resolve(strict=False)
+    candidate = root_path
+    for part in parts:
+        part_path = Path(part)
+        candidate = part_path if part_path.is_absolute() else candidate / part_path
+    candidate = candidate.resolve(strict=False)
+    root_key = os.path.normcase(str(root_path))
+    candidate_key = os.path.normcase(str(candidate))
+    try:
+        common = os.path.commonpath([root_key, candidate_key])
+    except ValueError as exc:
+        raise PathContainmentError(f"path escapes root: {candidate}") from exc
+    if common != root_key:
+        raise PathContainmentError(f"path escapes root: {candidate}")
+    return candidate
+
+
+def canonical_json(value: Any) -> bytes:
+    """Serialize JSON data with recursive NFC strings and sorted object keys."""
+
+    normalized = _normalize_json_value(value)
+    return json.dumps(
+        normalized,
+        ensure_ascii=False,
+        sort_keys=True,
+        separators=(",", ":"),
+        allow_nan=False,
+    ).encode("utf-8")
+
+
+def raw_payload_hash(raw_payload: JsonObject) -> str:
+    return "sha256:" + _sha256_hex(canonical_json(raw_payload))
+
+
+def raw_identity_document(event: NativeAgentEvent) -> Dict[str, Any]:
+    event = validate_native_event(event)
+    payload_hash = raw_payload_hash(event.raw_payload)
+    mode = _identity_mode(event)
+    return {
+        "contract": _IDENTITY_CONTRACT,
+        "provider": _nfc(event.provider),
+        "adapter": _nfc(event.adapter),
+        "native_event_type": _nfc(event.native_event_type),
+        "identity_mode": mode,
+        "native_id_scope": _nfc(event.native_id_scope),
+        "native_event_id": _nfc_or_none(event.native_event_id) if mode == "native_id" else None,
+        "source_session_id": _identity_session_scope(event, mode),
+        "source_project_ref": _identity_project_scope(event, mode),
+        "payload_version": _nfc(event.payload_version),
+        "raw_payload_hash": payload_hash,
+    }
+
+
+def raw_event_id(event: NativeAgentEvent) -> str:
+    return "raw_" + _sha256_hex(canonical_json(raw_identity_document(event)))
+
+
+def stable_native_identity_document(event: NativeAgentEvent) -> Optional[Dict[str, Any]]:
+    """Return the native-id conflict document, deliberately excluding payload hash."""
+
+    event = validate_native_event(event)
+    if _identity_mode(event) != "native_id":
+        return None
+    return {
+        "contract": _NATIVE_IDENTITY_CONTRACT,
+        "provider": _nfc(event.provider),
+        "adapter": _nfc(event.adapter),
+        "native_event_type": _nfc(event.native_event_type),
+        "native_id_scope": _nfc(event.native_id_scope),
+        "native_event_id": _nfc_or_none(event.native_event_id),
+        "source_session_id": _identity_session_scope(event, "native_id"),
+        "source_project_ref": _identity_project_scope(event, "native_id"),
+        "payload_version": _nfc(event.payload_version),
+    }
+
+
+def stable_native_identity_key(event: NativeAgentEvent) -> Optional[str]:
+    document = stable_native_identity_document(event)
+    if document is None:
+        return None
+    return "native_" + _sha256_hex(canonical_json(document))
+
+
+def derived_key_document(
+    *,
+    raw_event_id: str,
+    derived_kind: str,
+    processor_id: str,
+    processor_version: str,
+    semantic_target: Any,
+) -> Dict[str, Any]:
+    return {
+        "contract": _DERIVED_ID_CONTRACT,
+        "raw_event_id": _require_prefixed_id(raw_event_id, "raw_"),
+        "derived_kind": _require_text(derived_kind, "derived_kind"),
+        "processor_id": _require_text(processor_id, "processor_id"),
+        "processor_version": _require_text(processor_version, "processor_version"),
+        "semantic_target": semantic_target,
+    }
+
+
+def deterministic_derived_key(
+    *,
+    raw_event_id: str,
+    derived_kind: str,
+    processor_id: str,
+    processor_version: str,
+    semantic_target: Any,
+) -> str:
+    return _sha256_hex(
+        canonical_json(
+            derived_key_document(
+                raw_event_id=raw_event_id,
+                derived_kind=derived_kind,
+                processor_id=processor_id,
+                processor_version=processor_version,
+                semantic_target=semantic_target,
+            )
+        )
+    )
+
+
+def deterministic_derived_id(prefix: str, **kwargs: Any) -> str:
+    return _require_text(prefix, "prefix") + deterministic_derived_key(**kwargs)
+
+
+def atomic_write_json(
+    path: PathLikeStr,
+    data: JsonObject,
+    *,
+    root: Optional[PathLikeStr] = None,
+) -> None:
+    target = contained_path(root, path) if root is not None else Path(path).resolve(strict=False)
+    target.parent.mkdir(parents=True, exist_ok=True)
+    tmp_name: Optional[str] = None
+    try:
+        with tempfile.NamedTemporaryFile(
+            mode="wb",
+            dir=str(target.parent),
+            prefix=f".{target.name}.",
+            suffix=".tmp",
+            delete=False,
+        ) as tmp:
+            tmp_name = tmp.name
+            tmp.write(canonical_json(data) + b"\n")
+            tmp.flush()
+            os.fsync(tmp.fileno())
+        os.replace(tmp_name, target)
+        _fsync_directory(target.parent)
+    except Exception:
+        if tmp_name:
+            try:
+                Path(tmp_name).unlink()
+            except FileNotFoundError:
+                pass
+        raise
+
+
+class RawIngressKernel:
+    """File-first raw ingress kernel with deterministic identity and indexes."""
+
+    def __init__(self, workplace_root: PathLikeStr) -> None:
+        self.workplace_root = Path(workplace_root).resolve(strict=False)
+        self.event_root = contained_path(self.workplace_root, "runtime", "agent-events")
+
+    def ingest(
+        self,
+        event: NativeAgentEvent,
+        *,
+        received_at: Optional[Union[datetime, str]] = None,
+    ) -> RawReceipt:
+        event = validate_native_event(event)
+        received_dt, received_text = _coerce_received_at(received_at)
+        payload_hash = raw_payload_hash(event.raw_payload)
+        identity_doc = raw_identity_document(event)
+        identity_hash = "sha256:" + _sha256_hex(canonical_json(identity_doc))
+        rid = "raw_" + identity_hash[len("sha256:") :]
+        native_key = stable_native_identity_key(event)
+        shard_path, shard_rel = self._raw_shard(received_dt)
+        raw_index_path = self._index_path("raw_event_id", rid)
+        native_index_path = self._index_path("native_identity", native_key) if native_key else None
+        transaction_lock = contained_path(self.event_root, "indexes", ".raw-ingress.lock")
+
+        with FileLock(transaction_lock):
+            native_existing = self._read_json_if_exists(native_index_path) if native_index_path else None
+            if native_existing and native_existing.get("raw_payload_hash") != payload_hash:
+                return self._quarantine(
+                    "poisoned",
+                    "native_id_payload_conflict",
+                    event,
+                    rid,
+                    identity_hash,
+                    payload_hash,
+                    received_text,
+                    existing=native_existing,
+                    native_identity_key=native_key,
+                )
+
+            raw_existing = self._read_json_if_exists(raw_index_path)
+            if raw_existing:
+                if (
+                    raw_existing.get("identity_hash") == identity_hash
+                    and raw_existing.get("raw_payload_hash") == payload_hash
+                ):
+                    return RawReceipt(
+                        raw_event_id=rid,
+                        accepted=True,
+                        deduplicated=True,
+                        raw_location=raw_existing.get("raw_location"),
+                        routing_status="duplicate_raw",
+                    )
+                return self._quarantine(
+                    "collisions",
+                    "raw_event_id_hash_collision",
+                    event,
+                    rid,
+                    identity_hash,
+                    payload_hash,
+                    received_text,
+                    existing=raw_existing,
+                    native_identity_key=native_key,
+                )
+
+            if native_existing:
+                if native_existing.get("raw_event_id") == rid:
+                    return RawReceipt(
+                        raw_event_id=rid,
+                        accepted=True,
+                        deduplicated=True,
+                        raw_location=native_existing.get("raw_location"),
+                        routing_status="duplicate_raw",
+                    )
+                return self._quarantine(
+                    "collisions",
+                    "raw_event_id_hash_collision",
+                    event,
+                    rid,
+                    identity_hash,
+                    payload_hash,
+                    received_text,
+                    existing=native_existing,
+                    native_identity_key=native_key,
+                )
+
+            raw_line = self._raw_record(
+                event,
+                rid,
+                identity_hash,
+                payload_hash,
+                native_key,
+                received_text,
+            )
+            offset, byte_length = self._append_raw_line(shard_path, raw_line)
+            raw_location = f"{shard_rel}:{offset}"
+            index_record = {
+                "schema_version": 1,
+                "raw_event_id": rid,
+                "identity_hash": identity_hash,
+                "raw_payload_hash": payload_hash,
+                "native_identity_key": native_key,
+                "shard": shard_rel,
+                "offset": offset,
+                "byte_length": byte_length,
+                "raw_location": raw_location,
+                "received_at": received_text,
+                "routing_status": "raw_accepted",
+            }
+            atomic_write_json(raw_index_path, index_record, root=self.event_root)
+            if native_index_path is not None:
+                atomic_write_json(native_index_path, index_record, root=self.event_root)
+            return RawReceipt(
+                raw_event_id=rid,
+                accepted=True,
+                deduplicated=False,
+                raw_location=raw_location,
+                routing_status="raw_accepted",
+            )
+
+    def _raw_shard(self, received_at: datetime) -> Tuple[Path, str]:
+        parts = (
+            "raw",
+            "v1",
+            f"{received_at.year:04d}",
+            f"{received_at.month:02d}",
+            f"{received_at.day:02d}",
+            f"{received_at.hour:02d}.ndjson",
+        )
+        path = contained_path(self.event_root, *parts)
+        return path, path.relative_to(self.event_root).as_posix()
+
+    def _index_path(self, kind: str, key: Optional[str]) -> Path:
+        if key is None:
+            raise RawIngressError("index key is required")
+        _require_storage_key(kind, "index kind")
+        _require_storage_key(key, "index key")
+        return contained_path(self.event_root, "indexes", kind, f"{key}.json")
+
+    def _append_raw_line(self, shard_path: Path, record: JsonObject) -> Tuple[int, int]:
+        shard_path.parent.mkdir(parents=True, exist_ok=True)
+        lock_path = shard_path.with_suffix(shard_path.suffix + ".lock")
+        line = canonical_json(record) + b"\n"
+        with FileLock(lock_path):
+            fd = os.open(str(shard_path), os.O_CREAT | os.O_APPEND | os.O_WRONLY)
+            try:
+                offset = os.lseek(fd, 0, os.SEEK_END)
+                written = os.write(fd, line)
+                if written != len(line):
+                    raise OSError(f"short raw journal write: {written} != {len(line)}")
+                os.fsync(fd)
+            finally:
+                os.close(fd)
+        _fsync_directory(shard_path.parent)
+        return offset, len(line)
+
+    def _raw_record(
+        self,
+        event: NativeAgentEvent,
+        rid: str,
+        identity_hash: str,
+        payload_hash: str,
+        native_key: Optional[str],
+        received_at: str,
+    ) -> Dict[str, Any]:
+        return {
+            "schema_version": 1,
+            "raw_event_id": rid,
+            "provider": _nfc(event.provider),
+            "adapter": _nfc(event.adapter),
+            "native_event_type": _nfc(event.native_event_type),
+            "native_event_id": _nfc_or_none(event.native_event_id),
+            "received_at": received_at,
+            "source_session_id": _nfc_or_none(event.source_session_id),
+            "source_project_ref": _nfc_or_none(event.source_project_ref),
+            "correlation": event.correlation or {},
+            "payload_version": _nfc(event.payload_version),
+            "raw_payload": event.raw_payload,
+            "payload_ref": None,
+            "privacy": "private",
+            "identity_hash": identity_hash,
+            "raw_payload_hash": payload_hash,
+            "native_identity_key": native_key,
+        }
+
+    def _read_json_if_exists(self, path: Optional[Path]) -> Optional[Dict[str, Any]]:
+        if path is None or not path.exists():
+            return None
+        with path.open("r", encoding="utf-8") as handle:
+            data = json.load(handle)
+        if not isinstance(data, dict):
+            raise RawIngressError(f"index record is not an object: {path}")
+        return data
+
+    def _quarantine(
+        self,
+        bucket: str,
+        diagnostic: str,
+        event: NativeAgentEvent,
+        rid: str,
+        identity_hash: str,
+        payload_hash: str,
+        received_at: str,
+        *,
+        existing: Dict[str, Any],
+        native_identity_key: Optional[str],
+    ) -> RawReceipt:
+        _require_storage_key(bucket, "error bucket")
+        error_path = contained_path(self.event_root, "errors", bucket, f"{rid}.json")
+        error_record = {
+            "schema_version": 1,
+            "diagnostic": diagnostic,
+            "raw_event_id": rid,
+            "existing_raw_event_id": existing.get("raw_event_id"),
+            "identity_hash": identity_hash,
+            "raw_payload_hash": payload_hash,
+            "native_identity_key": native_identity_key,
+            "received_at": received_at,
+            "provider": _nfc(event.provider),
+            "adapter": _nfc(event.adapter),
+            "native_event_type": _nfc(event.native_event_type),
+            "native_event_id": _nfc_or_none(event.native_event_id),
+            "raw_payload": event.raw_payload,
+            "privacy": "private",
+        }
+        atomic_write_json(error_path, error_record, root=self.event_root)
+        return RawReceipt(
+            raw_event_id=rid,
+            accepted=False,
+            deduplicated=False,
+            raw_location=None,
+            routing_status="quarantined",
+            diagnostics={
+                "code": diagnostic,
+                "error_location": error_path.relative_to(self.event_root).as_posix(),
+                "existing_raw_event_id": existing.get("raw_event_id"),
+            },
+        )
+
+
+def validate_native_event(event: NativeAgentEvent) -> NativeAgentEvent:
+    if not isinstance(event, NativeAgentEvent):
+        raise RawIngressError("event must be a NativeAgentEvent")
+    _require_text(event.provider, "provider")
+    _require_text(event.adapter, "adapter")
+    _require_text(event.native_event_type, "native_event_type")
+    _require_text(event.payload_version, "payload_version")
+    if event.native_id_scope not in _NATIVE_ID_SCOPES:
+        raise RawIngressError(f"unsupported native_id_scope: {event.native_id_scope}")
+    if not isinstance(event.raw_payload, Mapping):
+        raise RawIngressError("raw_payload must be a JSON object")
+    if event.correlation is not None and not isinstance(event.correlation, Mapping):
+        raise RawIngressError("correlation must be a JSON object when provided")
+    canonical_json(event.raw_payload)
+    if event.correlation is not None:
+        canonical_json(event.correlation)
+    return event
+
+
+def _normalize_json_value(value: Any) -> Any:
+    if value is None or isinstance(value, bool) or isinstance(value, int):
+        return value
+    if isinstance(value, float):
+        if not math.isfinite(value):
+            raise ValueError("non-finite JSON number is not canonical")
+        return value
+    if isinstance(value, str):
+        return _nfc(value)
+    if isinstance(value, Mapping):
+        output: Dict[str, Any] = {}
+        for key, item in value.items():
+            if not isinstance(key, str):
+                raise TypeError("JSON object keys must be strings")
+            normalized_key = _nfc(key)
+            if normalized_key in output:
+                raise ValueError(f"duplicate JSON object key after NFC normalization: {normalized_key}")
+            output[normalized_key] = _normalize_json_value(item)
+        return output
+    if isinstance(value, (list, tuple)):
+        return [_normalize_json_value(item) for item in value]
+    raise TypeError(f"value is not JSON serializable: {type(value).__name__}")
+
+
+def _identity_mode(event: NativeAgentEvent) -> str:
+    native_id = _nfc_or_none(event.native_event_id)
+    if native_id and event.native_event_id_stable:
+        return "native_id"
+    return "payload_fallback"
+
+
+def _identity_session_scope(event: NativeAgentEvent, mode: str) -> Optional[str]:
+    if mode == "payload_fallback" or event.native_id_scope == "session":
+        return _nfc_or_none(event.source_session_id)
+    return None
+
+
+def _identity_project_scope(event: NativeAgentEvent, mode: str) -> Optional[str]:
+    if mode == "payload_fallback" or event.native_id_scope == "project":
+        return _nfc_or_none(event.source_project_ref)
+    return None
+
+
+def _coerce_received_at(value: Optional[Union[datetime, str]]) -> Tuple[datetime, str]:
+    if value is None:
+        dt = datetime.now(timezone.utc)
+    elif isinstance(value, str):
+        text = value[:-1] + "+00:00" if value.endswith("Z") else value
+        dt = datetime.fromisoformat(text)
+    elif isinstance(value, datetime):
+        dt = value
+    else:
+        raise RawIngressError("received_at must be datetime, ISO string, or None")
+    if dt.tzinfo is None:
+        dt = dt.replace(tzinfo=timezone.utc)
+    dt = dt.astimezone(timezone.utc)
+    text = dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
+    return dt, text
+
+
+def _require_text(value: str, field_name: str) -> str:
+    if not isinstance(value, str) or not value.strip():
+        raise RawIngressError(f"{field_name} must be a non-empty string")
+    return _nfc(value)
+
+
+def _require_prefixed_id(value: str, prefix: str) -> str:
+    value = _require_text(value, "id")
+    if not value.startswith(prefix):
+        raise RawIngressError(f"id must start with {prefix}")
+    return value
+
+
+def _require_storage_key(value: str, field_name: str) -> str:
+    value = _require_text(value, field_name)
+    if any(ch in value for ch in ("/", "\\", "\0")) or value in {".", ".."}:
+        raise RawIngressError(f"unsafe {field_name}: {value}")
+    return value
+
+
+def _nfc(value: str) -> str:
+    return unicodedata.normalize("NFC", value)
+
+
+def _nfc_or_none(value: Optional[str]) -> Optional[str]:
+    if value is None:
+        return None
+    normalized = _nfc(value).strip()
+    return normalized or None
+
+
+def _sha256_hex(data: bytes) -> str:
+    return hashlib.sha256(data).hexdigest()
+
+
+def _fsync_directory(path: Path) -> None:
+    if os.name == "nt":
+        return
+    fd = os.open(str(path), os.O_RDONLY)
+    try:
+        os.fsync(fd)
+    finally:
+        os.close(fd)
```

## Пояснение

Патч добавляет только `tools/pf_runtime/raw_ingress_kernel.py`. Модуль остается на stdlib и вводит компактное ядро raw ingress: `NativeAgentEvent`, `RawReceipt`, canonical JSON/NFC, `raw_event_id`, отдельный stable native-identity key без payload hash, проверку containment путей, hourly shard `runtime/agent-events/raw/v1/yyyy/mm/dd/hh.ndjson`, межпроцессный lock для append, атомарную запись JSON index/error файлов, duplicate/poison/collision решения и deterministic derived key/id helpers.

Poisoned duplicate определяется через `indexes/native_identity/<native_key>.json`: тот же stable provider-native id при другом `raw_payload_hash` уходит в `errors/poisoned/` и не дописывается в raw journal. Повтор того же `raw_event_id` с теми же `identity_hash` и `raw_payload_hash` возвращает исходный `raw_location` и `deduplicated=true`.

## Syntax Check

```powershell
python -m py_compile tools/pf_runtime/raw_ingress_kernel.py
```
