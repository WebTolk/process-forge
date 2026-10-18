"""Live runtime driver registry and definition reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from processforge_core.common.ids import safe_id
from processforge_core.common.paths import rel
from processforge_core.common.yaml_io import _parse_simple_yaml
from processforge_core.documents.reader import YamlDocumentReader
from processforge_core.project.metadata import ProjectMetadataReader
from processforge_core.runtime.drivers import RuntimeDriverDefinitionPolicy


class RuntimeDriverCatalogReader:
    """Read the existing driver catalog using a supplied distribution root."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.documents = YamlDocumentReader(_parse_simple_yaml)
        self.definition_policy = RuntimeDriverDefinitionPolicy()

    def registry_paths(self, workplace_manifest: Path | None = None, project_root: Path | None = None) -> list[Path]:
        paths = [self.distribution_root / "templates" / "registries" / "runtime-drivers.yaml"]
        if workplace_manifest and workplace_manifest.is_file():
            paths.append(workplace_manifest.parent / "registries" / "runtime-drivers.yaml")
        if project_root:
            paths.append(ProjectMetadataReader(project_root).flow_root() / "runtime" / "registries" / "runtime-drivers.local.yaml")
        return paths

    def entries(self, registry_path: Path) -> list[dict[str, Any]]:
        if not registry_path.is_file():
            return []
        data = self.documents.load(registry_path)
        entries = data.get("runtime_drivers") if isinstance(data, dict) else []
        return [item for item in entries if isinstance(item, dict)]

    def entry_path(self, registry_path: Path, entry: dict[str, Any]) -> Path | None:
        raw = entry.get("path")
        if not raw:
            return None
        text = str(raw).replace("{processforge_root}", str(self.distribution_root)).replace("${PF_DISTRIBUTION}", str(self.distribution_root))
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = (registry_path.parent / path).resolve()
        return path

    def load_path(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise SystemExit(f"FAIL: runtime driver not found: {path}")
        data = self.documents.read(path)
        data.setdefault("_source_path", str(path))
        return data

    def registered_path(self, driver_id: str, *, workplace_manifest: Path | None = None, project_root: Path | None = None) -> Path | None:
        """Select the existing registry path by exact ID without path fallback."""
        for registry_path in self.registry_paths(workplace_manifest, project_root):
            for entry in self.entries(registry_path):
                if str(entry.get("id")) != driver_id:
                    continue
                path = self.entry_path(registry_path, entry)
                if path and path.is_file():
                    return path
        return None

    def resolve(self, driver_ref: str, *, workplace_manifest: Path | None = None, project_root: Path | None = None) -> dict[str, Any]:
        direct = Path(driver_ref).expanduser()
        if direct.suffix in {".yaml", ".yml", ".json"} or direct.is_file():
            if not direct.is_absolute():
                base = project_root or self.distribution_root
                direct = (base / direct).resolve()
            return self.load_path(direct)
        driver_id = safe_id(driver_ref, "manual")
        path = self.registered_path(driver_id, workplace_manifest=workplace_manifest, project_root=project_root)
        if path is not None:
            return self.load_path(path)
        builtin = self.definition_policy.default_documents().get(driver_id)
        if builtin:
            result = json.loads(json.dumps(builtin))
            result["_source_path"] = "builtin"
            return result
        raise SystemExit(f"FAIL: runtime driver not found: {driver_ref}")

    def ref_is_direct_path(self, driver_ref: str) -> bool:
        direct = Path(driver_ref).expanduser()
        return direct.suffix in {".yaml", ".yml", ".json"} or direct.is_file()

    def normalized_ref(self, driver_ref: str, project_root: Path) -> str:
        direct = Path(driver_ref).expanduser()
        if not direct.is_absolute():
            direct = (project_root / direct).resolve()
        try:
            return direct.relative_to(project_root).as_posix()
        except ValueError:
            return str(direct)

    def ids(self, *, workplace_manifest: Path | None = None, project_root: Path | None = None) -> list[tuple[str, str, str]]:
        found: dict[str, tuple[str, str, str]] = {}
        for registry_path in self.registry_paths(workplace_manifest, project_root):
            source = rel(registry_path, self.distribution_root) if registry_path.is_relative_to(self.distribution_root) else str(registry_path)
            for entry in self.entries(registry_path):
                driver_id = str(entry.get("id") or "")
                if not driver_id:
                    continue
                path = self.entry_path(registry_path, entry)
                status = str(entry.get("status") or ("available" if path and path.is_file() else "missing"))
                found[driver_id] = (driver_id, status, source)
        for driver_id in self.definition_policy.default_documents():
            found.setdefault(driver_id, (driver_id, "available", "builtin"))
        return sorted(found.values())
