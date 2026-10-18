from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

from ..common.checks import Check, check
from ..common.yaml_io import yaml_error
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .schema_checks import UpdateSchemaChecks


class UpdateDocumentReader:
    """Read the existing update registries, paths and document formats."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.inputs = ContextContractInputs()
        self.schema_checks = UpdateSchemaChecks(distribution_root)

    def registry_file(self, workplace_root: Path, registry_key: str, default_name: str) -> Path:
        manifest = workplace_root / "workplace.yaml"
        if manifest.is_file():
            data = self.inputs.load_yaml_document(manifest)
            registries = data.get("registries") if isinstance(data, dict) else None
            raw = registries.get(registry_key) if isinstance(registries, dict) else None
            if isinstance(raw, str) and raw.strip():
                references = WorkspacePathReferenceReader(workplace_root, workplace_root, inputs=self.inputs)
                return references.path_resolution_to_path(references.workplace_path_resolution(workplace_root, raw))
        return workplace_root / "registries" / default_name

    def source_registry(self, workplace_root: Path) -> Path:
        return self.registry_file(workplace_root, "update_sources", "update-sources.yaml")

    def installed_registry(self, workplace_root: Path) -> Path:
        return self.registry_file(workplace_root, "installed_subjects", "installed-subjects.yaml")

    def overrides_path(self, workplace_root: Path) -> Path:
        return self.registry_file(workplace_root, "update_site_overrides", "update-site-overrides.yaml")

    def derived_sites_path(self, workplace_root: Path) -> Path:
        return workplace_root / "runtime" / "update" / "installed-update-sites.json"

    def yaml(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        data = self.inputs.load_yaml_document(path)
        return data if isinstance(data, dict) and not yaml_error(data) else {}

    def doctor_yaml(
        self,
        path: Path,
        schema_name: str,
        label: str,
        checks: list[Check],
    ) -> dict[str, Any] | None:
        """Load and schema-check a governed YAML document without mutating it."""
        data = self.inputs.load_yaml_document(path)
        error = yaml_error(data)
        if error:
            checks.append(check("FAIL", f"{label} YAML parse failed: {error}"))
            return None
        if not isinstance(data, dict) or not data:
            checks.append(check("FAIL", f"{label} must be a non-empty YAML object"))
            return None
        checks.append(check("PASS", f"{label} is valid YAML"))
        self.schema_checks.append(checks, data, schema_name, label)
        return data

    def manifest_candidates(self, root: Path, patterns: list[str]) -> list[Path]:
        if not root.is_dir():
            return []
        candidates: list[Path] = []
        for pattern in patterns:
            candidates.extend(sorted(root.glob(pattern)))
        return [path.resolve() for path in candidates if path.is_file()]

    def registry_paths(self, workplace_root: Path, registry_name: str, collection_key: str) -> list[Path]:
        data = self.yaml(workplace_root / "registries" / registry_name)
        entries = data.get(collection_key) if isinstance(data.get(collection_key), list) else []
        paths: list[Path] = []
        references = WorkspacePathReferenceReader(workplace_root, workplace_root, inputs=self.inputs)
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                paths.append(references.path_resolution_to_path(references.workplace_path_resolution(workplace_root, str(entry.get("path")))))
        return paths

    def index(self, distribution_root: Path) -> dict[str, Any]:
        candidates = [
            distribution_root / "updates" / "processforge-update-index.yaml",
            distribution_root / "updates" / "channels.yaml",
        ]
        for path in candidates:
            if path.is_file():
                data = self.inputs.load_yaml_document(path)
                return data if isinstance(data, dict) else {}
        return {}

    def file_url_path(self, value: str, base: Path | None = None) -> Path:
        text = value.strip()
        if text.startswith("file://"):
            parsed = urlparse(text)
            raw = url2pathname(parsed.path or "")
            if os.name == "nt" and re.match(r"^/[A-Za-z]:/", raw):
                raw = raw[1:]
            return Path(raw).expanduser().resolve()
        path = Path(text).expanduser()
        if not path.is_absolute() and base is not None:
            path = base / path
        return path.resolve()

    def document(self, path: Path) -> dict[str, Any]:
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {}
            return data if isinstance(data, dict) else {}
        return self.yaml(path)

    def text(self, text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def runtime_root(self, workplace_root: Path) -> Path:
        return workplace_root / "runtime" / "update"

    def candidates_path(self, workplace_root: Path) -> Path:
        return self.runtime_root(workplace_root) / "candidates.json"

    def notifications_path(self, workplace_root: Path) -> Path:
        return self.runtime_root(workplace_root) / "notifications.json"

    def staged_path(self, workplace_root: Path, candidate_id: str) -> Path:
        return self.runtime_root(workplace_root) / "staged" / candidate_id / "stage-record.yaml"

    def staged_record(self, workplace_root: Path, candidate_id: str) -> dict[str, Any]:
        return self.yaml(self.staged_path(workplace_root, candidate_id))
