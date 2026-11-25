"""Durable file-outbox publication and qualified reuse of historical deliveries."""

from __future__ import annotations

import errno
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
        if os.name == "nt":
            from processforge_platforms.windows_shared_read import read_published_file

            return read_published_file(path)
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
    elif _read(path) != raw:
        _publish(path, raw, replace=True)
    return path


def _is_chat_observation(event: dict[str, Any]) -> bool:
    return (
        event.get("source") == "processforge.cli"
        and event.get("event_type") == "chat.message.recorded"
    )


def _chat_reference(event: dict[str, Any]) -> dict[str, Any] | None:
    reference: Any = event
    for key in ("data", "message", "content_ref"):
        if not isinstance(reference, dict):
            return None
        reference = reference.get(key)
    return reference if isinstance(reference, dict) else None


def _original_observation(
    event: dict[str, Any], first: dict[str, Any]
) -> dict[str, Any]:
    # The clock and an unknown chat line can change when rebuilding an event.
    # The serialized comparison still binds every other field of the delivery.
    source = event.get("source")
    chat = _is_chat_observation(event) and _is_chat_observation(first)
    if (
        not isinstance(source, str)
        or first.get("source") != source
        or not (source.startswith("processforge.runtime.") or chat)
    ):
        return event
    restored = dict(event)
    if isinstance(event.get("time"), str) and isinstance(first.get("time"), str):
        restored["time"] = first["time"]
    if not chat:
        return restored
    published, replayed = _chat_reference(first), _chat_reference(event)
    if published is None or replayed is None:
        return restored
    published_line, replayed_line = published.get("line"), replayed.get("line")
    if (
        type(published_line) is int
        and type(replayed_line) is int
        and min(published_line, replayed_line) == 0
        and max(published_line, replayed_line) > 0
        and all(
            isinstance(published.get(key), str)
            and published[key]
            and published[key] == replayed.get(key)
            for key in ("path", "message_id")
        )
    ):
        data = event["data"]
        restored["data"] = {
            **data,
            "message": {
                **data["message"],
                "content_ref": {**replayed, "line": published_line},
            },
        }
    return restored


def _legacy_object(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _legacy_payload(
    path: Path,
    legacy_id: str,
    target_id: str,
    event_id: str,
    event: dict[str, Any],
    *,
    bound: bool = False,
) -> bytes | None:
    try:
        data = _read(path)
    except OSError as error:
        if not bound and (
            error.errno == errno.ENAMETOOLONG or getattr(error, "winerror", None) == 206
        ):
            return None
        raise
    if data is None:
        if bound:
            raise ValueError("outbox_legacy_payload_missing")
        return None
    envelope = _legacy_object(data)
    if not (
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
    return data


def _legacy_pair(
    project: Path,
    directory: Path,
    results: Path,
    event_id: str,
    target_id: str,
    event: dict[str, Any],
    delivery_id: str,
    previous: dict[str, Any],
) -> tuple[str, Path, bytes, dict[str, Any]] | None:
    slug = safe_id(target_id, "hook")
    legacy_id = "del_" + opaque_identity_digest(f"{event_id}:{slug}")[:32]
    # A legacy WTAICC envelope cannot prove which exact configured target wrote it.
    if slug.startswith("wtaicc") or not event_id or "\0" in event_id:
        return None
    filename = f"{event_id}.{slug}.json"
    if Path(filename).name != filename:
        return None
    if os.name == "nt" and (
        Path(filename).is_reserved()
        or any(char in '<>:"|?*' or ord(char) < 32 for char in filename)
    ):
        return None
    configured = directory / filename
    if previous:
        if previous.get("payload_delivery_id") != legacy_id:
            raise ValueError("outbox_receipt_invalid")
        if previous.get("outbox") != rel(configured, project):
            raise ValueError("outbox_delivery_route_conflict")
        data = _legacy_payload(
            configured, legacy_id, target_id, event_id, event, bound=True
        )
        if data is not None:
            return delivery_id, configured, data, previous
        return None

    receipt_path = results / f"{legacy_id}.json"
    raw = _read(receipt_path)
    if raw is None:
        data = _legacy_payload(configured, legacy_id, target_id, event_id, event)
        if data is None:
            return None
        # More than one exact target may qualify for the same historical receipt.
        # Elect its owner once, using the immutable payload as evidence.
        claim = _written_receipt(
            project, configured, data, {}, legacy_id, event_id, target_id
        )
        raw = _first_bytes(receipt_path, _encode(claim))

    receipt = _legacy_object(raw)
    # Original receipts used a slug. An upgraded receipt names its exact owner.
    bound = receipt.get("event_id") == event_id and "payload_sha256" in receipt
    possible_owners = (target_id,) if bound else (slug, target_id)
    if (
        receipt.get("schema_version") == 1
        and receipt.get("delivery_id") == legacy_id
        and receipt.get("target_id") in possible_owners
        and receipt.get("status") == "written"
    ):
        recorded = receipt.get("outbox")
        if (
            isinstance(recorded, str)
            and "\0" not in recorded
            and Path(recorded).name == filename
        ):
            path = project / recorded
            data = _legacy_payload(
                path, legacy_id, target_id, event_id, event, bound=bound
            )
            if data is not None:
                if path != configured:
                    raise ValueError("outbox_delivery_route_conflict")
                return legacy_id, path, data, receipt
        elif bound:
            raise ValueError("outbox_delivery_route_conflict")

    # A torn receipt or a sibling target's receipt says nothing about this
    # directory's envelope. Preserve the old record and bind our exact key.
    data = _legacy_payload(configured, legacy_id, target_id, event_id, event)
    if data is None:
        return None
    return delivery_id, configured, data, {}


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


def _written_receipt(
    project: Path,
    path: Path,
    data: bytes,
    previous: dict[str, Any],
    delivery_id: str,
    event_id: str,
    target_id: str,
) -> dict[str, Any]:
    envelope = json.loads(data)
    digest = hashlib.sha256(data).hexdigest()
    if "payload_sha256" in previous and previous["payload_sha256"] != digest:
        raise ValueError("outbox_receipt_payload_mismatch")
    timestamp = "delivery_time" if "delivery_time" in envelope else "created_at"
    receipt = {
        **previous,
        "schema_version": 1,
        "delivery_id": delivery_id,
        "target_id": target_id,
        "event_id": event_id,
        "delivery_time": envelope[timestamp],
        "payload_sha256": digest,
        "status": "written",
        "exit_code": 0,
        "blocking": False,
        "message": "Outbox payload written",
        "outbox": rel(path, project),
    }
    if envelope["delivery_id"] != delivery_id:
        receipt["payload_delivery_id"] = envelope["delivery_id"]
    original = envelope["event"]
    if _is_chat_observation(original) and "payload_sha256" not in previous:
        observation = {
            key: original[key]
            for key in ("source", "time", "event_type")
            if key in original
        }
        reference = _chat_reference(original)
        if reference is not None:
            observation["data"] = {
                "message": {
                    "content_ref": {
                        key: reference[key]
                        for key in ("path", "message_id", "line")
                        if key in reference
                    }
                }
            }
        receipt["runtime_observation"] = observation
    elif isinstance(original.get("source"), str) and original["source"].startswith(
        "processforge.runtime."
    ):
        receipt["runtime_observation"] = {
            key: original[key]
            for key in ("source", "time", "correlation_id")
            if key in original
        }
    return receipt


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
    legacy = None
    if not previous or "payload_delivery_id" in previous:
        legacy = _legacy_pair(
            project,
            directory,
            results,
            event_id,
            target_id,
            payload["event"],
            delivery_id,
            previous,
        )
        if legacy is None and previous:
            raise ValueError("outbox_receipt_invalid")
    if legacy is not None:
        delivery_id, path, data, previous = legacy
        receipt_path = results / f"{delivery_id}.json"
    else:
        if previous and previous.get("outbox") != rel(path, project):
            raise ValueError("outbox_delivery_route_conflict")
        timestamp = "created_at" if "created_at" in payload else "delivery_time"
        data = _payload_bytes(path, payload, timestamp, previous)
    receipt = _written_receipt(
        project, path, data, previous, delivery_id, event_id, target_id
    )
    if receipt != previous:
        write_receipt(receipt_path, receipt, first=not previous)
    return delivery_id, rel(path, project), rel(receipt_path, project)
