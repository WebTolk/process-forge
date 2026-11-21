"""Restore a package from its local update history."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.ids import safe_id
from .documents import UpdateDocumentReader
from .update_metadata import SubjectMetadataBackup

_FILE_SUBJECT_TYPES = ("tool_definition", "tool_package", "tool")


def package_file_mode(subject: dict[str, Any], policy: dict[str, Any]) -> bool:
    return (
        policy.get("mode") == "replace_file"
        or subject.get("type") in _FILE_SUBJECT_TYPES
    )


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except RuntimeError as error:
        raise ValueError("package_rollback_path_changed") from error


def _own_path(path: Path) -> Path:
    if _resolved(path) != path:
        raise ValueError("package_rollback_path_changed")
    return path


def _receipt_path(workplace: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("package_rollback_history_invalid")
    return _resolved(workplace / value)


def _candidate(
    document: dict[str, Any], candidate_id: str, version_key: str
) -> dict[str, Any]:
    subject = document.get("subject")
    version = document.get(version_key)
    if (
        not isinstance(subject, dict)
        or not all(
            isinstance(subject.get(k), str) and subject[k].strip()
            for k in ("type", "id")
        )
        or not isinstance(version, str)
        or not version.strip()
    ):
        raise ValueError("package_rollback_history_invalid")
    return {
        "id": candidate_id,
        "subject": {"type": subject["type"], "id": subject["id"]},
        "available_version": version,
    }


def _version_one(record: dict[str, Any]) -> bool:
    version = record.get("schema_version")
    return type(version) is int and version == 1


def _staged_candidate(
    documents: UpdateDocumentReader, path: Path, candidate_id: str, missing: str
) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(missing)
    record = documents.yaml(path)
    staged = record.get("candidate")
    verification = record.get("verification")
    if (
        not _version_one(record)
        or record.get("candidate_id") != candidate_id
        or record.get("status") != "verified"
        or not isinstance(staged, dict)
        or staged.get("id") != candidate_id
        or not isinstance(verification, dict)
        or verification.get("sha256") != "pass"
    ):
        raise ValueError("package_rollback_stage_invalid")
    candidate = _candidate(staged, candidate_id, "available_version")
    policy = staged.get("update_policy", {})
    if not isinstance(policy, dict):
        raise ValueError("package_rollback_stage_invalid")
    candidate["file_mode"] = package_file_mode(candidate["subject"], policy)
    return candidate


@dataclass(frozen=True)
class PackageRollback:
    """The bound destination and validated backup for one package update."""

    destination: Path
    metadata: SubjectMetadataBackup
    previous: Path | None = None
    file_mode: bool = False

    @classmethod
    def load(
        cls,
        documents: UpdateDocumentReader,
        workplace: Path,
        candidate_id: str,
    ) -> PackageRollback:
        if not candidate_id or safe_id(candidate_id) != candidate_id:
            raise ValueError("package_rollback_candidate_id_invalid")
        logical_root = documents.runtime_root(workplace)
        history_root = _resolved(logical_root)

        def history_path(path: Path) -> Path:
            return _own_path(history_root / path.relative_to(logical_root))

        def read_stage(missing: str) -> dict[str, Any]:
            return _staged_candidate(
                documents,
                history_path(documents.staged_path(workplace, candidate_id)),
                candidate_id,
                missing,
            )

        applied = history_path(documents.applied_path(workplace, candidate_id))
        backup_dir = history_path(documents.backup_dir(workplace, candidate_id))
        staged = None
        recorded_destination = None
        record = documents.yaml(applied) if applied.exists() else None
        if record is not None:
            if (
                not _version_one(record)
                or record.get("candidate_id") != candidate_id
                or record.get("status") != "applied"
                or _receipt_path(workplace, record.get("backup_path")) != backup_dir
            ):
                raise ValueError("package_rollback_history_invalid")
            candidate = _candidate(record, candidate_id, "installed_version")
            recorded_destination = _receipt_path(workplace, record.get("install_path"))
        else:
            staged = read_stage(f"candidate not found: {candidate_id}")
            candidate = staged

        metadata = SubjectMetadataBackup.load(
            documents.installed_registry(workplace),
            _own_path(backup_dir / "installed-subject.yaml"),
            candidate,
            recorded_destination,
        )
        if record is not None and (
            (
                "previous_version" in record
                and record["previous_version"] != metadata.previous_version
            )
            or (
                "previous_subject_present" in record
                and record["previous_subject_present"]
                is not (metadata.data["before"] is not None)
            )
        ):
            raise ValueError("package_rollback_preimage_version_mismatch")
        destination = _own_path(metadata.install_path)
        if (
            _receipt_path(workplace, metadata.data["after"].get("install_path"))
            != destination
            or destination.is_relative_to(history_root)
            or history_root.is_relative_to(destination)
        ):
            raise ValueError("package_rollback_history_invalid")
        if metadata.data["phase"] == "prepared":
            raise ValueError("package_payload_backup_incomplete")
        if metadata.data["phase"] == "rolled_back":
            return cls(destination, metadata)

        previous_file = _own_path(backup_dir / "previous-file")
        previous_tree = _own_path(backup_dir / "previous")
        copies = [path for path in (previous_file, previous_tree) if path.exists()]
        if len(copies) != int(metadata.data["payload_existed"]):
            raise ValueError("package_payload_backup_invalid")
        previous = copies[0] if copies else None
        payload_kind = metadata.data.get("payload_kind")
        if payload_kind is not None:
            file_mode = payload_kind == "file"
        elif candidate["subject"]["type"] in _FILE_SUBJECT_TYPES:
            file_mode = True
        elif previous is not None:
            file_mode = previous == previous_file
        else:
            staged = staged or read_stage("package_rollback_payload_kind_missing")
            if any(
                staged[key] != candidate[key]
                for key in ("subject", "available_version")
            ):
                raise ValueError("package_rollback_stage_invalid")
            file_mode = staged["file_mode"]

        if previous is not None:
            expected = previous_file if file_mode else previous_tree
            valid = previous.is_file() if file_mode else previous.is_dir()
            if previous != expected or not valid:
                raise ValueError("package_payload_backup_invalid")
        if destination.exists() and not (
            destination.is_file() if file_mode else destination.is_dir()
        ):
            raise ValueError("package_rollback_destination_changed")
        return cls(destination, metadata, previous, file_mode)

    def restore(self) -> None:
        if self.metadata.data["phase"] == "rolled_back":
            return
        target = self.destination
        if self.file_mode:
            if self.previous is not None:
                shutil.copy2(self.previous, target)
            else:
                target.unlink(missing_ok=True)
        else:
            if target.exists():
                shutil.rmtree(target)
            if self.previous is not None:
                shutil.copytree(self.previous, target)
        self.metadata.restore()
