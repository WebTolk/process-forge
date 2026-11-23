"""Durable file-outbox publication and qualified reuse of historical deliveries."""

from __future__ import annotations

import hashlib
import json
import os
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


def write_receipt(path: Path, result: dict[str, Any]) -> Path:
    _publish(path, _encode(result), replace=True)
    return path


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
    try:
        receipt = json.loads(raw_receipt)
        if not isinstance(receipt, dict) or not (
            receipt.get("schema_version") == 1
            and receipt.get("delivery_id") == legacy_id
            and receipt.get("target_id") in (slug, target_id)
            and receipt.get("status") == "written"
            and receipt.get("outbox") == rel(path, project)
        ):
            return None
        data = _read(path)
        if data is None:
            return None
        envelope = json.loads(data)
    except (ValueError, UnicodeError):
        # Preserve unreadable history and use the disjoint current key.
        return None
    if not isinstance(envelope, dict) or not (
        envelope.get("schema_version") == 1
        and envelope.get("delivery_id") == legacy_id
        and envelope.get("mode") == "outbox"
        and envelope.get("target_id") == target_id
        and envelope.get("event") == event
        and isinstance(envelope.get("delivery_time"), str)
    ):
        return None
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
        raw = _encode(payload)
        if previous and hashlib.sha256(raw).hexdigest() != previous["payload_sha256"]:
            raise ValueError("outbox_receipt_payload_mismatch")
        try:
            _publish(path, raw, replace=False)
        except FileExistsError:
            # Another replay published the first complete envelope. Its time is authoritative.
            data = path.read_bytes()
        else:
            return raw
    stored = json.loads(data)
    if not isinstance(stored, dict) or not isinstance(stored.get(timestamp), str):
        raise ValueError("outbox_payload_invalid")
    if stored != {**payload, timestamp: stored[timestamp]}:
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
        delivery_time = json.loads(data)["delivery_time"]
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
            ):
                raise ValueError("outbox_receipt_invalid")
        same_path = previous if previous.get("outbox") == rel(path, project) else {}
        data = _payload_bytes(path, payload, timestamp, same_path)
        if (
            same_path
            and hashlib.sha256(data).hexdigest() != same_path["payload_sha256"]
        ):
            raise ValueError("outbox_receipt_payload_mismatch")
        delivery_time = json.loads(data)[timestamp]
    outbox = rel(path, project)
    receipt = {
        **previous,
        "schema_version": 1,
        "delivery_id": delivery_id,
        "target_id": target_id,
        "event_id": event_id,
        "delivery_time": delivery_time,
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "status": "written",
        "exit_code": 0,
        "blocking": False,
        "message": "Outbox payload written",
        "outbox": outbox,
    }
    if receipt != previous:
        write_receipt(receipt_path, receipt)
    return delivery_id, outbox, rel(receipt_path, project)
