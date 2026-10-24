"""Compose the shared service in an existing configured PF workplace."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from processforge_core.accounting.model import identifier
from processforge_core.accounting.service import AccountingService
from processforge_core.accounting.storage import (
    AccountingStorageError,
    SQLiteAccountingRepository,
)
from processforge_core.configuration import ConfigurationProvider
from processforge_core.database import DatabaseFactory, SQLiteDriver
from processforge_core.project.metadata import ProjectMetadataReader


def read_json(path: Path) -> dict[str, Any]:
    """Read only a bounded explicit metadata document."""
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("accounting_metadata_size_limit")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("accounting_metadata_object_required")
    return data


class _ReadOnlyRepository(SQLiteAccountingRepository):
    """Use Core's read snapshots without its creating/migrating constructor."""

    def __init__(self, path: Path, *, driver: SQLiteDriver | None = None) -> None:
        self.driver = driver if driver is not None else DatabaseFactory.resolve_driver()
        self.path = path
        self.busy_timeout_ms = 1000

    def ingest(self, *args: Any, **kwargs: Any) -> int:
        raise PermissionError("read_only_accounting")


@dataclass(frozen=True, kw_only=True)
class WorkplaceAccounting:
    """Explicit project mapping and durable location; no installation fallback."""

    workplace: Path
    project_root: Path
    project_id: str
    configuration: ConfigurationProvider | None = None

    @classmethod
    def discover(
        cls,
        project_root: Path,
        workplace: Path | None = None,
        *,
        configuration: ConfigurationProvider | None = None,
    ) -> WorkplaceAccounting:
        """Use the existing narrow reader and require the actual PF project id."""
        project_root = project_root.resolve()
        reader = ProjectMetadataReader(project_root)
        project = reader.manifest().get("project")
        if not isinstance(project, dict) or not isinstance(project.get("id"), str):
            raise ValueError("explicit_pf_project_id_required")
        project_id = project["id"]
        identifier(project_id, "project_id")
        if workplace is None:
            manifest = reader.workplace_manifest()
            if manifest is None:
                raise ValueError("configured_workplace_required")
            workplace = manifest.parent
        elif workplace.name == "workplace.yaml":
            workplace = workplace.parent
        if not workplace.is_absolute():
            workplace = project_root / workplace
        workplace = workplace.resolve()
        if not (workplace / "workplace.yaml").is_file():
            raise ValueError("existing_workplace_required")
        if workplace == project_root or workplace.is_relative_to(project_root):
            raise ValueError("accounting_workplace_must_be_outside_checkout")
        return cls(
            workplace=workplace,
            project_root=project_root,
            project_id=project_id,
            configuration=configuration,
        )

    @property
    def directory(self) -> Path:
        """Return the workplace durable accounting directory."""
        return self.workplace / "data" / "accounting"

    @property
    def database(self) -> Path:
        """Return the one normalized store shared by clients and projects."""
        return self.directory / "accounting.sqlite3"

    def _safe_paths(self) -> None:
        for path in (
            self.workplace / "data",
            self.directory,
            self.database,
            self.directory / "identity.json",
            self.directory / "projects",
        ):
            if path.is_symlink() or (
                hasattr(path, "is_junction") and path.is_junction()
            ):
                raise AccountingStorageError("accounting_unsafe_path")

    def _mapping_path(self) -> Path:
        digest = hashlib.sha256(self.project_id.encode()).hexdigest()
        return self.directory / "projects" / f"{digest}.json"

    def ensure_identity(self) -> str:
        """Persist origin and exact project-id mapping under one bounded writer lock."""
        self._safe_paths()
        self.directory.mkdir(parents=True, exist_ok=True)
        lock = self.directory / ".identity.lock"
        descriptor: int | None = None
        for _ in range(50):
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                break
            except FileExistsError:
                time.sleep(0.02)
        if descriptor is None:
            raise AccountingStorageError("accounting_identity_busy")
        try:
            origin_path = self.directory / "identity.json"
            if origin_path.exists():
                origin = read_json(origin_path)
                if origin.get("schema_version") != 1:
                    raise ValueError("accounting_identity_version")
                origin_id = origin["origin_id"]
                identifier(origin_id, "origin_id")
            else:
                if self.database.exists():
                    raise AccountingStorageError(
                        "accounting_origin_missing_for_existing_store"
                    )
                origin_id = "local-" + uuid4().hex
                _atomic_json(origin_path, {"schema_version": 1, "origin_id": origin_id})
            mappings = self.directory / "projects"
            mappings.mkdir(exist_ok=True)
            mapping = self._mapping_path()
            if mapping.is_symlink():
                raise AccountingStorageError("accounting_unsafe_mapping")
            expected = {"schema_version": 1, "project_id": self.project_id}
            if mapping.exists():
                if read_json(mapping) != expected:
                    raise ValueError("accounting_project_mapping_conflict")
            else:
                _atomic_json(mapping, expected)
            return origin_id
        finally:
            os.close(descriptor)
            lock.unlink()

    def allowed_projects(self, *, workplace_scope: bool = False) -> tuple[str, ...]:
        """Require an explicit human-local choice for wider workplace visibility."""
        self._safe_paths()
        if not workplace_scope:
            return (self.project_id,)
        projects: set[str] = {self.project_id}
        mappings = self.directory / "projects"
        if mappings.is_dir():
            for count, path in enumerate(mappings.glob("*.json"), start=1):
                if count > 500 or path.is_symlink():
                    raise ValueError("accounting_project_mapping_limit_or_unsafe")
                data = read_json(path)
                project = data.get("project_id")
                if not isinstance(project, str):
                    raise ValueError("accounting_project_mapping_invalid")
                identifier(project, "project_id")
                if (
                    data.get("schema_version") != 1
                    or path.stem != hashlib.sha256(project.encode()).hexdigest()
                ):
                    raise ValueError("accounting_project_mapping_invalid")
                projects.add(project)
        return tuple(sorted(projects))

    def service(self, *, create: bool = False) -> AccountingService | None:
        """Compose Core queries read-only; explicit collection may create storage."""
        from processforge_core.composition import build_configuration_provider

        provider = (
            self.configuration
            if self.configuration is not None
            else build_configuration_provider(
                project_root=self.project_root,
                workplace_root=self.workplace,
            )
        )
        driver = DatabaseFactory.resolve_driver(provider.current().database)
        self._safe_paths()
        if create:
            self.ensure_identity()
            repository = SQLiteAccountingRepository(self.database, driver=driver)
        elif self.database.is_file():
            repository = _ReadOnlyRepository(self.database, driver=driver)
        else:
            return None
        return AccountingService(repository)


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    # Staging stays beside its destination, not in another filesystem.
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
