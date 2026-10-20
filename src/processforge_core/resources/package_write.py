"""Existing knowledge package manifest and resource index write composition."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import processforge_core.common.clock as _core_common_clock
from processforge_core.common.text import ensure_trailing_newline
from processforge_core.common.yaml_dump import dump_yaml
from processforge_core.resources.index_checks import KnowledgeResourceIndexService
from processforge_core.resources.project_packages import PackageRootResolution, ProjectPackageCatalogReader
from processforge_core.resources.records import ResourceRecordService


class PackageManifestWriter:
    """Write existing package documents using their concrete Core owners."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.indexes = KnowledgeResourceIndexService(distribution_root)
        self.records = ResourceRecordService()

    def manifest_path_for_write(self, workplace_root: Path, package_id: str, package_root_id: str | None = None) -> tuple[PackageRootResolution, Path]:
        existing = self.packages.find_manifests(workplace_root, package_id)
        if package_root_id:
            root, default_path = self.packages.resolve_path(workplace_root, package_id, package_root_id, mode="write")
            for existing_root, existing_path in existing:
                if existing_root.root_id == root.root_id:
                    return existing_root, existing_path
            return root, default_path
        if len(existing) > 1:
            roots = ", ".join(f"{root.root_id}:{path.as_posix()}" for root, path in existing)
            raise SystemExit(f"FAIL: duplicate package id '{package_id}' found across package roots: {roots}; pass --package-root")
        if len(existing) == 1:
            root, path = existing[0]
            if not root.resolved_path.is_dir() and not root.fallback:
                raise SystemExit(f"FAIL: package root '{root.root_id}' path does not exist: {root.resolved_path.as_posix()}")
            return root, path
        root, default_path = self.packages.resolve_path(workplace_root, package_id, None, mode="write")
        if root.fallback:
            root.resolved_path.mkdir(parents=True, exist_ok=True)
        return root, default_path

    def build_index(self, package_manifest: dict[str, Any], workplace_root: Path | None = None, package_root_id: str | None = None) -> dict[str, Any]:
        package_id = str(package_manifest.get("id", "package"))
        resources = [
            self.records.normalize(resource, package_id, workplace_root)
            for resource in package_manifest.get("resources", [])
            if isinstance(resource, dict)
        ]
        return {
            "schema_version": 1,
            "package": {
                "id": package_id,
                "version": str(package_manifest.get("version", "1.0.0")),
                "package_root": package_root_id or str(package_manifest.get("package_root", "")) or None,
            },
            "generated_at": _core_common_clock.now_utc(),
            "load_policy": {
                "default": "on_demand",
                "heavy_resources": "index_only_until_requested",
                "do_not_load_full_content": True,
            },
            "resources": resources,
        }

    def write(self, workplace_root: Path, package_id: str, package_manifest: dict[str, Any], package_root_id: str | None = None) -> tuple[Path, Path, PackageRootResolution]:
        package_root, manifest_path = self.manifest_path_for_write(workplace_root, package_id, package_root_id)
        package_manifest["package_root"] = package_root.root_id
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(ensure_trailing_newline(dump_yaml(package_manifest)), encoding="utf-8")
        index_path = self.indexes.index_path(manifest_path, workplace_root, package_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(ensure_trailing_newline(dump_yaml(self.build_index(package_manifest, workplace_root, package_root.root_id))), encoding="utf-8")
        return manifest_path, index_path, package_root
