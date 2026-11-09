"""Atomic publication of local Runtime records without abandoned staging."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

SERVICE_STATE_MAX_BYTES = 65536
_DETAILS = "_runtime_state_details"
_DETAIL_KIND = "pf.runtime.service-details"
_CONTROL_FIELDS = frozenset(
    {
        "schema_version",
        "runtime_version",
        "processforge_core_version",
        "core_identity",
        "instance_id",
        "pid",
        "started_at",
        "updated_at",
        "stale_detected_at",
        "endpoint",
        "workplace_root",
        "status",
        "health",
        "capabilities",
        "token_hash",
        "metrics",
    }
)


class RuntimeServiceStateWriter:
    """Prepare once; briefly retry only a Windows replacement conflict.

    The private 50 ms window limits retry admission and requested sleeps, not
    OS call duration or thread scheduling. Failed publication removes only its
    own staging file and never removes the destination or masks the failure.
    """

    def write(self, path: Path, payload: dict[str, Any]) -> None:
        self._publish(
            path,
            lambda: (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ),
        )

    def write_text(self, path: Path, text: str) -> None:
        self._publish(path, lambda: text)

    def _publish(self, path: Path, render: Callable[[], str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        try:
            tmp.write_text(render(), encoding="utf-8")
            self._replace(tmp, path)
        except BaseException as publication_error:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as cleanup_error:
                publication_error.add_note(
                    "temporary_cleanup:runtime_state:cleanup_pending:"
                    + str(
                        getattr(cleanup_error, "winerror", None) or cleanup_error.errno
                    )
                )
            raise

    @staticmethod
    def _replace(tmp: Path, path: Path) -> None:
        try:
            os.replace(tmp, path)
            return
        except OSError as error:
            if sys.platform != "win32" or getattr(error, "winerror", None) not in {
                5,
                32,
                33,
            }:
                raise
            original_error = error

        deadline = time.monotonic() + 0.05
        # The attempt cap also terminates a frozen/coarse clock. Preparation
        # and the payload are never repeated, even after multiple conflicts.
        for _ in range(5):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.01, remaining))
            if time.monotonic() >= deadline:
                break
            try:
                os.replace(tmp, path)
                return  # A successful OS call remains success past the deadline.
            except OSError as error:
                if getattr(error, "winerror", None) not in {5, 32, 33}:
                    raise
        raise original_error


class RuntimeServiceStateStore:
    """Publish bounded control and lossless details under existing owner locking.

    The caller serializes writers using the Runtime's existing state/singleton
    ownership. Replacing control is the only commit point. Two fixed slots keep
    the accepted details intact on failure without accumulating snapshot files.
    """

    def __init__(self, writer: RuntimeServiceStateWriter | None = None) -> None:
        self.writer = writer if writer is not None else RuntimeServiceStateWriter()

    @staticmethod
    def _render(payload: dict[str, Any]) -> str:
        return (
            json.dumps(
                payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
            )
            + "\n"
        )

    @staticmethod
    def _encoded(text: str) -> bytes:
        # The existing writer uses text mode's native newline translation.
        return text.replace("\n", os.linesep).encode("utf-8")

    @staticmethod
    def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("runtime_state_duplicate_key")
            result[key] = value
        return result

    @staticmethod
    def _constant(_value: str) -> Any:
        raise ValueError("runtime_state_nonfinite")

    @staticmethod
    def _float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("runtime_state_nonfinite")
        return parsed

    @classmethod
    def _object(cls, raw: bytes) -> dict[str, Any]:
        try:
            value = json.loads(
                raw,
                object_pairs_hook=cls._pairs,
                parse_constant=cls._constant,
                parse_float=cls._float,
            )
        except (UnicodeError, RecursionError) as error:
            raise ValueError("runtime_state_invalid_json") from error
        if not isinstance(value, dict):
            raise ValueError("runtime_state_invalid_object")
        return value

    @staticmethod
    def _regular(path: Path) -> os.stat_result:
        observed = path.lstat()
        if not stat.S_ISREG(observed.st_mode) or (
            getattr(observed, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError("runtime_state_unsafe_file")
        return observed

    @classmethod
    def _control(cls, path: Path) -> dict[str, Any]:
        cls._regular(path)
        raw = path.read_bytes()
        value = cls._object(raw)
        # Legacy records contained full diagnostics and may exceed this budget.
        # Only an ordinary owner write converts them to the bounded format.
        if _DETAILS in value and len(raw) > SERVICE_STATE_MAX_BYTES:
            raise ValueError("runtime_state_control_too_large")
        return value

    @staticmethod
    def _reference(control: dict[str, Any]) -> dict[str, Any] | None:
        if _DETAILS not in control:
            return None
        reference = control[_DETAILS]
        if (
            not isinstance(reference, dict)
            or set(reference) != {"schema_version", "slot", "size", "sha256"}
            or type(reference["schema_version"]) is not int
            or reference["schema_version"] != 1
            or type(reference["slot"]) is not int
            or reference["slot"] not in {0, 1}
            or type(reference["size"]) is not int
            or not 0 < reference["size"] < sys.maxsize
            or not isinstance(reference["sha256"], str)
            or len(reference["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in reference["sha256"])
        ):
            raise ValueError("runtime_state_details_reference_invalid")
        return reference

    @staticmethod
    def _slot(path: Path, slot: int) -> Path:
        return path.with_name(f"service-details.{slot}.json")

    @classmethod
    def _envelope(cls, raw: bytes) -> dict[str, Any]:
        value = cls._object(raw)
        if (
            set(value) != {"kind", "schema_version", "instance_id", "payload"}
            or value["kind"] != _DETAIL_KIND
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or not isinstance(value["payload"], dict)
            or (
                value["instance_id"] is not None
                and not isinstance(value["instance_id"], str)
            )
        ):
            raise ValueError("runtime_state_details_unrecognized")
        return value

    @staticmethod
    def _project(payload: dict[str, Any]) -> dict[str, Any]:
        control = {
            key: value for key, value in payload.items() if key in _CONTROL_FIELDS
        }
        configuration = payload.get("configuration")
        if isinstance(configuration, dict):
            control["configuration"] = {
                key: configuration[key]
                for key in ("status", "metrics_interval_seconds")
                if key in configuration
            }
        scheduler = payload.get("scheduler")
        jobs = scheduler.get("jobs") if isinstance(scheduler, dict) else None
        if isinstance(jobs, dict):
            control["scheduler"] = {
                "jobs": {
                    name: {
                        key: job[key]
                        for key in ("period_seconds", "last_run", "last_result")
                        if key in job
                    }
                    for name, job in jobs.items()
                    if isinstance(job, dict)
                }
            }
        return control

    def write(self, path: Path, payload: dict[str, Any]) -> None:
        """Preserve accepted control/details until the final atomic replacement."""
        if _DETAILS in payload:
            raise ValueError("runtime_state_requires_full_snapshot")
        if payload.get("instance_id") is not None and not isinstance(
            payload["instance_id"], str
        ):
            raise ValueError("runtime_state_control_invalid")
        status = payload.get("status")
        if not isinstance(status, str) or status not in {
            "starting",
            "ready",
            "running",
            "stopped",
            "stale",
            "stopping",
            "failed",
        }:
            raise ValueError("runtime_state_control_invalid")
        try:
            old = self._control(path)
        except FileNotFoundError:
            old = {}
        previous = self._reference(old)
        slot = 1 - previous["slot"] if previous is not None else 0
        destination = self._slot(path, slot)
        try:
            self._regular(destination)
        except FileNotFoundError:
            pass
        else:
            # A known inactive snapshot can be reused. A name alone does not
            # authorize replacing an unknown, partial, or redirected file.
            self._envelope(destination.read_bytes())
        control = self._project(payload)
        details = {
            "kind": _DETAIL_KIND,
            "schema_version": 1,
            "instance_id": payload.get("instance_id"),
            "payload": {
                key: value
                for key, value in payload.items()
                if key not in _CONTROL_FIELDS
            },
        }
        details_text = self._render(details)
        details_bytes = self._encoded(details_text)
        control[_DETAILS] = {
            "schema_version": 1,
            "slot": slot,
            "size": len(details_bytes),
            "sha256": hashlib.sha256(details_bytes).hexdigest(),
        }
        control_text = self._render(control)
        if len(self._encoded(control_text)) > SERVICE_STATE_MAX_BYTES:
            raise ValueError("runtime_state_control_too_large")
        self.writer.write_text(destination, details_text)
        self.writer.write_text(path, control_text)

    @classmethod
    def _merge(cls, details: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
        result = dict(details)
        for key, value in control.items():
            current = result.get(key)
            result[key] = (
                cls._merge(current, value)
                if isinstance(current, dict) and isinstance(value, dict)
                else value
            )
        return result

    @classmethod
    def _restore(cls, path: Path, control: dict[str, Any]) -> dict[str, Any]:
        reference = cls._reference(control)
        if reference is None:
            return dict(control)
        source = cls._slot(path, reference["slot"])
        observed = cls._regular(source)
        if observed.st_size != reference["size"]:
            raise ValueError("runtime_state_details_size_changed")
        with source.open("rb") as stream:
            raw = stream.read(reference["size"] + 1)
        if (
            len(raw) != reference["size"]
            or hashlib.sha256(raw).hexdigest() != reference["sha256"]
        ):
            raise ValueError("runtime_state_details_changed")
        envelope = cls._envelope(raw)
        if envelope["instance_id"] != control.get("instance_id"):
            raise ValueError("runtime_state_details_owner_changed")
        return cls._merge(envelope["payload"], cls.without_details(control))

    def read(self, path: Path, control: dict[str, Any] | None = None) -> dict[str, Any]:
        """Restore one snapshot; a rotated slot permits only a same-owner retry."""
        current = self._control(path) if control is None else control
        owner = current.get("instance_id"), current.get("pid")
        for attempt in range(3):
            try:
                return self._restore(path, current)
            except (OSError, ValueError):
                if attempt == 2:
                    raise
                fresh = self._control(path)
                if (
                    fresh == current
                    or (fresh.get("instance_id"), fresh.get("pid")) != owner
                ):
                    raise
                current = fresh
        raise AssertionError("unreachable")

    @staticmethod
    def without_details(control: dict[str, Any]) -> dict[str, Any]:
        """Keep control truth while explicitly reporting an unavailable report."""
        return {key: value for key, value in control.items() if key != _DETAILS}
