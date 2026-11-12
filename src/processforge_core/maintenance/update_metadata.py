"""Selected installed-subject preimages for existing package apply/rollback."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..common.clock import now_utc
from .temporary_disposal import atomic_staging


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "subjects": []}
    try:
        with path.open(encoding="utf8") as stream:
            value = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise ValueError("installed_subject_yaml_invalid") from error
    if not isinstance(value, dict):
        raise ValueError("installed_subject_document_invalid")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_staging(path) as staging:
        with staging.open("w", encoding="utf8", newline="\n") as stream:
            yaml.safe_dump(value, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, path)


def _selected(
    document: dict[str, Any], subject: dict[str, Any]
) -> dict[str, Any] | None:
    rows = document.get("subjects")
    if document.get("schema_version") != 1 or not isinstance(rows, list):
        raise ValueError("installed_subject_registry_invalid")
    selected = [
        row
        for row in rows
        if isinstance(row, dict)
        and (row.get("type"), row.get("id")) == (subject.get("type"), subject.get("id"))
    ]
    if len(selected) > 1:
        raise ValueError("installed_subject_ambiguous")
    return selected[0] if selected else None


def _replace(
    registry: Path,
    subject: dict[str, Any],
    expected: tuple[dict[str, Any] | None, ...],
    replacement: dict[str, Any] | None,
) -> None:
    document = _read(registry)
    current = _selected(document, subject)
    if current not in expected:
        raise ValueError("installed_subject_changed")
    rows = document["subjects"]
    if current is not None:
        index = next(i for i, row in enumerate(rows) if row is current)
        if replacement is None:
            del rows[index]
        else:
            rows[index] = copy.deepcopy(replacement)
    elif replacement is not None:
        rows.append(copy.deepcopy(replacement))
    document["updated_at"] = now_utc()
    _write(registry, document)


def _postimage(
    before: dict[str, Any] | None,
    candidate: dict[str, Any],
    install_path: str | None,
) -> dict[str, Any]:
    subject = candidate.get("subject")
    if (
        not isinstance(subject, dict)
        or not subject.get("type")
        or not subject.get("id")
    ):
        raise ValueError("installed_subject_identity_required")
    if before is None:
        return {
            "type": subject["type"],
            "id": subject["id"],
            "scope": subject.get("scope") or "global",
            "version": candidate.get("available_version"),
            "installed_at": now_utc(),
            "install_path": install_path,
        }
    after = copy.deepcopy(before)
    after["version"] = candidate.get("available_version")
    after["updated_at"] = now_utc()
    if install_path is not None:
        after["install_path"] = install_path
    return after


def update_version(
    registry: Path, candidate: dict[str, Any], install_path: str | None
) -> None:
    """Compatibility helper; caller serializes the existing registry writer."""
    subject = candidate.get("subject", {})
    before = copy.deepcopy(_selected(_read(registry), subject))
    _replace(registry, subject, (before,), _postimage(before, candidate, install_path))


@dataclass
class SubjectMetadataBackup:
    """An explicit operation record; construction performs no I/O."""

    registry: Path
    path: Path
    data: dict[str, Any]

    @classmethod
    def capture(
        cls,
        registry: Path,
        path: Path,
        candidate: dict[str, Any],
        install_path: Path,
        installed_path_value: str,
    ) -> SubjectMetadataBackup:
        subject = candidate.get("subject", {})
        before = copy.deepcopy(_selected(_read(registry), subject))
        after = _postimage(before, candidate, installed_path_value)
        data = {
            "schema_version": 1,
            "candidate_id": candidate["id"],
            "subject": {"type": subject["type"], "id": subject["id"]},
            "install_path": str(install_path.resolve()),
            "before": before,
            "after": after,
            "phase": "prepared",
            "payload_existed": install_path.exists(),
        }
        _write(path, data)
        return cls(registry, path, data)

    @classmethod
    def load(
        cls,
        registry: Path,
        path: Path,
        candidate: dict[str, Any],
        install_path: Path,
    ) -> SubjectMetadataBackup:
        if not path.is_file():
            raise ValueError("package_metadata_preimage_missing")
        data = _read(path)
        subject = candidate.get("subject", {})
        identity = {"type": subject.get("type"), "id": subject.get("id")}
        if (
            data.get("schema_version") != 1
            or data.get("candidate_id") != candidate.get("id")
            or data.get("subject") != identity
            or data.get("install_path") != str(install_path.resolve())
            or not isinstance(data.get("after"), dict)
            or "before" not in data
            or data["after"].get("version") != candidate.get("available_version")
            or data.get("phase")
            not in {"prepared", "backup_ready", "applied", "rolled_back"}
            or not isinstance(data.get("payload_existed"), bool)
            or (data.get("before") is not None and not isinstance(data["before"], dict))
        ):
            raise ValueError("package_metadata_preimage_mismatch")
        for image in (data["before"], data["after"]):
            if image is not None and any(
                image.get(key) != value for key, value in identity.items()
            ):
                raise ValueError("package_metadata_preimage_mismatch")
        current = _selected(_read(registry), identity)
        allowed = (
            (data["before"],)
            if data["phase"] == "rolled_back"
            else (data["before"], data["after"])
        )
        if current not in allowed:
            raise ValueError("installed_subject_changed")
        return cls(registry, path, data)

    def phase(self, value: str) -> None:
        self.data["phase"] = value
        _write(self.path, self.data)

    def publish(self) -> None:
        _replace(
            self.registry,
            self.data["subject"],
            (self.data["before"],),
            self.data["after"],
        )
        self.phase("applied")

    def restore(self) -> None:
        _replace(
            self.registry,
            self.data["subject"],
            (self.data["before"], self.data["after"]),
            self.data["before"],
        )
        self.phase("rolled_back")
