"""Properties of the Core distribution owned by this process.

Loaded identity is a value captured at application boot. Installed identity is
an observation of the same distribution on disk, never a neighbouring checkout.
Metadata identity does not establish the integrity of the installed payload.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypedDict

from processforge_core.maintenance.update import (
    CORE_MANIFEST_NAME,
    CoreUpdateError,
    manifest_file_map,
)

_VERSION = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
_COMMIT = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
_MANIFEST_LIMIT = 8 * 1024 * 1024
_OWN_LOADED = object()


class CoreIdentityRecord(TypedDict):
    """Describe the portable version1 identity record."""

    version: str
    build_id: str
    source_commit: str
    source_kind: str
    status: str
    reason: str


class CoreIdentityReport(TypedDict):
    """Describe metadata comparison without implying payload integrity."""

    schema_version: int
    loaded: CoreIdentityRecord
    installed: CoreIdentityRecord
    status: str
    reason: str
    reload_required: bool | None


@dataclass(frozen=True, slots=True)
class CoreIdentity:
    """Portable metadata identity with an explicit qualification limit."""

    version: str = "unknown"
    build_id: str = "unknown"
    source_commit: str = "unknown"
    source_kind: str = "unknown"
    status: str = "unknown"
    reason: str = "metadata_unavailable"

    def record(self) -> CoreIdentityRecord:
        """Return a fresh portable record of this immutable value."""
        return {
            "version": self.version,
            "build_id": self.build_id,
            "source_commit": self.source_commit,
            "source_kind": self.source_kind,
            "status": self.status,
            "reason": self.reason,
        }

    @classmethod
    def from_record(cls, value: object) -> CoreIdentity:
        """Validate an observed process record without trusting arbitrary text."""
        if not isinstance(value, dict):
            return cls(reason="loaded_identity_unavailable")
        names = (
            "version",
            "build_id",
            "source_commit",
            "source_kind",
            "status",
            "reason",
        )
        record: dict[str, str] = {}
        for name in names:
            item = value.get(name)
            if not isinstance(item, str) or len(item) > 128:
                return cls(reason="loaded_identity_invalid")
            record[name] = item
        if (
            (
                record["version"] != "unknown"
                and not _VERSION.fullmatch(record["version"])
            )
            or not re.fullmatch(
                r"unknown|manifest:sha256:[a-f0-9]{64}|git:(?:[a-f0-9]{40}|[a-f0-9]{64})",
                record["build_id"],
            )
            or (
                record["source_commit"] != "unknown"
                and not _COMMIT.fullmatch(record["source_commit"])
            )
            or record["source_kind"]
            not in {"unknown", "manifest", "source_checkout", "unmanaged"}
            or record["status"] not in {"ready", "partial", "unknown"}
            or (
                record["reason"]
                and not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", record["reason"])
            )
        ):
            return cls(reason="loaded_identity_invalid")
        return cls(**record)


class CoreIdentityReadPort(Protocol):
    """Observe the metadata of one explicitly selected Core distribution."""

    def read(self) -> CoreIdentity:
        """Return identity or a bounded reason for unavailable metadata."""
        ...


class _MetadataLimitError(ValueError):
    pass


class DistributionMetadataReader:
    """Read bounded distribution metadata without loading CLI or transports."""

    def __init__(self, distribution_root: Path) -> None:
        """Bind reads to the selected distribution, independently of cwd.

        Args:
            distribution_root: The Core source, archive or installed root.
        """
        self._root = distribution_root.resolve()

    @staticmethod
    def _read(path: Path, limit: int) -> bytes | None:
        try:
            with path.open("rb") as stream:
                content = stream.read(limit + 1)
        except FileNotFoundError:
            return None
        if len(content) > limit:
            raise _MetadataLimitError
        return content

    def _source_commit(self) -> tuple[str, str]:
        """Read Git's current ref, including worktrees and packed refs.

        This observes a source revision only. It neither scans the working tree
        nor claims that uncommitted source bytes match that revision.
        """
        marker = self._root / ".git"
        if not marker.exists():
            return "unknown", "unmanaged"
        try:
            git_dir = marker
            if not marker.is_dir():
                pointer = (self._read(marker, 4096) or b"").decode("utf-8").strip()
                if not pointer.startswith("gitdir: ") or "\n" in pointer:
                    return "unknown", "source_checkout"
                git_dir = (self._root / pointer[8:]).resolve()
            common_pointer = self._read(git_dir / "commondir", 4096)
            common_dir = git_dir
            if common_pointer is not None:
                common_text = common_pointer.decode("utf-8").strip()
                if not common_text or "\n" in common_text:
                    return "unknown", "source_checkout"
                common_dir = (git_dir / common_text).resolve()
            head = self._read(git_dir / "HEAD", 512)
            value = head.decode("utf-8").strip() if head is not None else ""
            for _ in range(5):
                if _COMMIT.fullmatch(value):
                    return value.lower(), "source_checkout"
                if not value.startswith("ref: "):
                    break
                reference = value[5:]
                if (
                    not reference.startswith("refs/")
                    or "\\" in reference
                    or any(part in {"", ".", ".."} for part in reference.split("/"))
                ):
                    break
                loose = self._read(common_dir / reference, 512)
                if loose is not None:
                    value = loose.decode("utf-8").strip()
                    continue
                packed = self._read(common_dir / "packed-refs", 4 * 1024 * 1024)
                for line in (packed or b"").decode("utf-8").splitlines():
                    fields = line.split(" ", 1)
                    if len(fields) == 2 and fields[1] == reference:
                        value = fields[0]
                        break
                else:
                    break
            return "unknown", "source_checkout"
        except (OSError, UnicodeError, ValueError, RuntimeError):
            return "unknown", "source_checkout"

    def read(self) -> CoreIdentity:
        """Capture coherent VERSION/manifest metadata and source provenance."""
        version_path = self._root / "VERSION"
        manifest_path = self._root / CORE_MANIFEST_NAME
        try:
            version_bytes = self._read(version_path, 1024)
            if version_bytes is None:
                return CoreIdentity(reason="version_missing")
            try:
                version = version_bytes.decode("utf-8").strip()
            except UnicodeError:
                return CoreIdentity(reason="version_invalid")
            if len(version) > 128 or not _VERSION.fullmatch(version):
                return CoreIdentity(reason="version_invalid")
            manifest_bytes = self._read(manifest_path, _MANIFEST_LIMIT)
            if manifest_bytes is not None:
                try:
                    data = json.loads(manifest_bytes.decode("utf-8"))
                    if (
                        not isinstance(data, dict)
                        or type(data.get("schema_version")) is not int
                        or data.get("kind") != "processforge.core_manifest"
                        or not isinstance(data.get("source"), dict)
                    ):
                        return CoreIdentity(reason="manifest_invalid")
                    manifest_file_map(data)
                except (
                    CoreUpdateError,
                    UnicodeError,
                    ValueError,
                    TypeError,
                    RecursionError,
                ):
                    return CoreIdentity(reason="manifest_invalid")
                if data.get("version") != version:
                    return CoreIdentity(reason="version_manifest_mismatch")
                raw_commit = data["source"].get("commit")
                commit = (
                    raw_commit.lower()
                    if isinstance(raw_commit, str) and _COMMIT.fullmatch(raw_commit)
                    else "unknown"
                )
                identity = CoreIdentity(
                    version=version,
                    build_id="manifest:sha256:"
                    + hashlib.sha256(manifest_bytes).hexdigest(),
                    source_commit=commit,
                    source_kind="manifest",
                    status="ready" if commit != "unknown" else "partial",
                    reason="" if commit != "unknown" else "source_revision_unavailable",
                )
            else:
                commit, kind = self._source_commit()
                identity = CoreIdentity(
                    version=version,
                    build_id="git:" + commit if commit != "unknown" else "unknown",
                    source_commit=commit,
                    source_kind=kind,
                    status="ready" if commit != "unknown" else "partial",
                    reason="" if commit != "unknown" else "build_metadata_unavailable",
                )
            if version_bytes != self._read(
                version_path, 1024
            ) or manifest_bytes != self._read(manifest_path, _MANIFEST_LIMIT):
                return CoreIdentity(reason="metadata_changed")
            return identity
        except _MetadataLimitError:
            return CoreIdentity(reason="metadata_too_large")
        except OSError:
            return CoreIdentity(reason="metadata_unreadable")


class CoreProperties:
    """Expose a boot snapshot and live installed metadata through one owner."""

    __slots__ = ("_reader", "_loaded")

    def __init__(self, reader: CoreIdentityReadPort) -> None:
        """Capture loaded identity from an explicitly supplied metadata port.

        Args:
            reader: Observer of this distribution's current disk metadata.
        """
        self._reader = reader
        self._loaded = reader.read()

    @classmethod
    def from_distribution(cls, distribution_root: Path) -> CoreProperties:
        """Compose properties for an explicitly selected source/distribution."""
        return cls(DistributionMetadataReader(distribution_root))

    @property
    def loaded(self) -> CoreIdentity:
        """Identity captured when this Core application was constructed."""
        return self._loaded

    def installed(self) -> CoreIdentity:
        """Observe current disk metadata without changing the loaded identity."""
        return self._reader.read()

    def report(self, *, loaded: object = _OWN_LOADED) -> CoreIdentityReport:
        """Compare captured or explicitly observed loaded identity to live disk.

        An absent remote record stays unknown; it is never replaced by this
        observer's own loaded build. Equal labels alone do not prove equality.
        """
        observed = (
            self._loaded if loaded is _OWN_LOADED else CoreIdentity.from_record(loaded)
        )
        installed = self.installed()
        reload_required: bool | None = None
        status = "unknown"
        if observed.version == "unknown" or observed.status == "unknown":
            reason = "loaded_identity_unavailable"
        elif installed.version == "unknown" or installed.status == "unknown":
            reason = "installed_identity_unavailable"
        elif observed.version != installed.version:
            status, reason, reload_required = "reload_required", "release_changed", True
        elif "unknown" in {observed.build_id, installed.build_id}:
            reason = "build_identity_unavailable"
        elif observed.build_id != installed.build_id:
            status, reason, reload_required = "reload_required", "build_changed", True
        else:
            status, reason, reload_required = "current", "", False
        return {
            "schema_version": 1,
            "loaded": observed.record(),
            "installed": installed.record(),
            "status": status,
            "reason": reason,
            "reload_required": reload_required,
        }

    @property
    def spec_version(self) -> str:
        """Version of the existing PF specification, independent of release."""
        return "1.0"

    @property
    def schema_bundle_version(self) -> str:
        """Version of the existing schema bundle, independent of release."""
        return "1.0"
