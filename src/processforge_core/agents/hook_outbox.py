"""Durable file-outbox publication and qualified reuse of historical deliveries."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from ..common.ids import opaque_identity_digest, safe_id
from ..common.paths import rel
from ..maintenance.temporary_disposal import atomic_staging


def delivery_key(event_id: str, target_id: str) -> str:
    pair = json.dumps([event_id, target_id], ensure_ascii=False, separators=(",", ":"))
    return "del_" + opaque_identity_digest(pair)


def _encode(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _publish(path: Path, raw: bytes, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_staging(path) as staging:
        with staging.open("wb") as stream:
            if stream.write(raw) != len(raw):
                raise OSError("outbox_incomplete_write")
            stream.flush()
            os.fsync(stream.fileno())
            owned = os.fstat(stream.fileno())
        if replace:
            os.replace(staging, path)
        elif os.name == "nt":
            # Windows rename fails if another publisher won this delivery.
            os.rename(staging, path)
        else:
            os.link(staging, path)
            # The owned staging lease refuses multi-link cleanup. Remove our
            # verified sibling once the complete inode has its final name.
            if not os.path.samestat(owned, staging.lstat()):
                raise OSError("outbox_staging_changed")
            staging.unlink()


def _first_bytes(path: Path, raw: bytes) -> bytes:
    try:
        _publish(path, raw, replace=False)
    except (FileExistsError, PermissionError):
        # A Windows reader may deny a competing rename. Confirm the winner
        # from the actual file before accepting the operation as a replay.
        winner = _read(path)
        if winner is None:
            raise
        return winner
    return raw


def write_receipt(path: Path, result: dict[str, Any], *, first: bool = False) -> Path:
    raw = _encode(result)
    if first:
        if _first_bytes(path, raw) != raw:
            raise ValueError("outbox_receipt_conflict")
    else:
        _publish(path, raw, replace=True)
    return path


def _original_observation(
    event: dict[str, Any], first: dict[str, Any]
) -> dict[str, Any]:
    # Runtime can reconstruct an admitted event from raw ingress. Its host
    # observation time and the fallback correlation for a sessionless event
    # are generated anew. Keep the originally delivered values on replay.
    source = event.get("source")
    if (
        not isinstance(source, str)
        or not source.startswith("processforge.runtime.")
        or first.get("source") != source
    ):
        return event
    restored = dict(event)
    if isinstance(event.get("time"), str) and isinstance(first.get("time"), str):
        restored["time"] = first["time"]
    session = event.get("session") or {}
    data = event.get("data") or {}
    if (
        isinstance(session, dict)
        and isinstance(data, dict)
        and not session.get("id")
        and not data.get("run_id")
        and all(
            isinstance(value, str) and re.fullmatch(r"corr-[0-9a-f]{12}", value)
            for value in (event.get("correlation_id"), first.get("correlation_id"))
        )
    ):
        restored["correlation_id"] = first["correlation_id"]
    return restored


def _legacy_pair(
    project: Path,
    directory: Path,
    results: Path,
    event_id: str,
    target_id: str,
    event: dict[str, Any],
) -> tuple[str, Path, bytes, dict[str, Any]] | None:
    slug = safe_id(target_id, "hook")
    legacy_id = "del_" + opaque_identity_digest(f"{event_id}:{slug}")[:32]
    raw_receipt = _read(results / f"{legacy_id}.json")
    if raw_receipt is None:
        return None
    # A legacy WTAICC envelope cannot prove which exact configured target wrote it.
    if (
        slug.startswith("wtaicc")
        or not event_id.isascii()
        or not all(c.isalnum() or c in "-_." for c in event_id)
    ):
        return None
    path = directory / f"{event_id}.{slug}.json"
    bound = False
    try:
        receipt = json.loads(raw_receipt)
        if not isinstance(receipt, dict) or not (
            receipt.get("schema_version") == 1
            and receipt.get("delivery_id") == legacy_id
            and receipt.get("target_id") in (slug, target_id)
            and receipt.get("status") == "written"
        ):
            return None
        bound = (
            receipt.get("event_id") == event_id
            and receipt.get("target_id") == target_id
            and "payload_sha256" in receipt
        )
        if receipt.get("outbox") != rel(path, project):
            if bound:
                raise ValueError("outbox_delivery_route_conflict")
            return None
        data = _read(path)
        if data is None:
            if bound:
                raise ValueError("outbox_legacy_payload_missing")
            return None
        envelope = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        if bound:
            raise ValueError("outbox_legacy_payload_invalid") from error
        # Preserve unreadable history and use the disjoint current key.
        return None
    if not isinstance(envelope, dict) or not (
        envelope.get("schema_version") == 1
        and envelope.get("delivery_id") == legacy_id
        and envelope.get("mode") == "outbox"
        and envelope.get("target_id") == target_id
        and isinstance(envelope.get("event"), dict)
        and (envelope["event"].get("event_id") or envelope["event"].get("id"))
        == event_id
        and isinstance(envelope.get("delivery_time"), str)
    ):
        if bound:
            raise ValueError("outbox_legacy_payload_invalid")
        return None
    if _encode(envelope["event"]) != _encode(
        _original_observation(event, envelope["event"])
    ):
        raise ValueError("outbox_delivery_conflict")
    if (
        "payload_sha256" in receipt
        and receipt["payload_sha256"] != hashlib.sha256(data).hexdigest()
    ):
        raise ValueError("outbox_receipt_payload_mismatch")
    return legacy_id, path, data, receipt


def _payload_bytes(
    path: Path, payload: dict[str, Any], timestamp: str, previous: dict[str, Any]
) -> bytes:
    data = _read(path)
    if data is None:
        if previous:
            payload[timestamp] = previous["delivery_time"]
            payload["event"] = _original_observation(
                payload["event"], previous.get("runtime_observation", {})
            )
        raw = _encode(payload)
        if previous and hashlib.sha256(raw).hexdigest() != previous["payload_sha256"]:
            raise ValueError("outbox_receipt_payload_mismatch")
        data = _first_bytes(path, raw)
        if data == raw:
            return raw
    stored = json.loads(data)
    if (
        not isinstance(stored, dict)
        or not isinstance(stored.get(timestamp), str)
        or not isinstance(stored.get("event"), dict)
    ):
        raise ValueError("outbox_payload_invalid")
    expected = {
        **payload,
        timestamp: stored[timestamp],
        "event": _original_observation(payload["event"], stored["event"]),
    }
    if _encode(stored) != _encode(expected):
        raise ValueError("outbox_delivery_conflict")
    return data


def publish_outbox(
    project: Path,
    directory: Path,
    results: Path,
    event_id: str,
    target_id: str,
    delivery_id: str,
    payload: dict[str, Any],
) -> tuple[str, str, str]:
    path = directory / f"{delivery_id}.outbox.json"
    receipt_path = results / f"{delivery_id}.json"
    raw_receipt = _read(receipt_path)
    previous: dict[str, Any] = {}
    timestamp = "created_at" if "created_at" in payload else "delivery_time"
    legacy = None
    if raw_receipt is None:
        legacy = _legacy_pair(
            project, directory, results, event_id, target_id, payload["event"]
        )
    if legacy is not None:
        delivery_id, path, data, previous = legacy
        receipt_path = results / f"{delivery_id}.json"
    else:
        if raw_receipt is not None:
            previous = json.loads(raw_receipt)
            if not isinstance(previous, dict) or not (
                previous.get("delivery_id") == delivery_id
                and previous.get("event_id") == event_id
                and previous.get("target_id") == target_id
                and previous.get("status") == "written"
                and isinstance(previous.get("delivery_time"), str)
                and isinstance(previous.get("payload_sha256"), str)
                and isinstance(previous.get("runtime_observation", {}), dict)
            ):
                raise ValueError("outbox_receipt_invalid")
        if previous and previous.get("outbox") != rel(path, project):
            raise ValueError("outbox_delivery_route_conflict")
        data = _payload_bytes(path, payload, timestamp, previous)
        if previous and hashlib.sha256(data).hexdigest() != previous["payload_sha256"]:
            raise ValueError("outbox_receipt_payload_mismatch")
    envelope = json.loads(data)
    outbox = rel(path, project)
    receipt = {
        **previous,
        "schema_version": 1,
        "delivery_id": delivery_id,
        "target_id": target_id,
        "event_id": event_id,
        "delivery_time": envelope[timestamp],
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "status": "written",
        "exit_code": 0,
        "blocking": False,
        "message": "Outbox payload written",
        "outbox": outbox,
    }
    original = envelope["event"]
    if isinstance(original.get("source"), str) and original["source"].startswith(
        "processforge.runtime."
    ):
        receipt["runtime_observation"] = {
            key: original[key]
            for key in ("source", "time", "correlation_id")
            if key in original
        }
    if receipt != previous:
        write_receipt(receipt_path, receipt, first=not previous)
    return delivery_id, outbox, rel(receipt_path, project)
