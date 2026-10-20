"""Knowledge resource index paths, references and project diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from ..common.paths import path_is_relative_to, rel
from ..common.text import check_with_hint
from ..common.yaml_io import yaml_error
from ..project.requirements import PlatformDependencyPreflightService
from ..work.context_documents import ContextContractInputs
from .project_packages import ProjectPackageCatalogReader
from .records import HEAVY_RESOURCE_KINDS, ResourceRecordService
from .identity import ResourceIdentityPolicy


class KnowledgeResourceIndexService:
    """Observe package resources through concrete Core owners on each operation."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.inputs = ContextContractInputs()
        self.records = ResourceRecordService()
        self.dependencies = PlatformDependencyPreflightService(distribution_root)

    def index_path(self, manifest_path: Path, workplace_root: Path, package_id: str) -> Path:
        if manifest_path.name == "package.yaml":
            return manifest_path.parent / "indexes" / "resource-index.yaml"
        paths = ResourceIdentityPolicy()
        validated_id = paths.validate_resource_id(package_id, "knowledge package")
        package_root = workplace_root / "packages"
        return paths.contained_resource_path(
            package_root,
            package_root / validated_id / "indexes" / "resource-index.yaml",
            "knowledge package",
        )

    def path_ref_missing(self, workplace_root: Path, resource: dict[str, Any]) -> str | None:
        path_ref = resource.get("path_ref")
        if not isinstance(path_ref, dict):
            return "missing path_ref"
        registry = str(path_ref.get("registry") or "")
        ref_id = str(path_ref.get("id") or "")
        if not registry or not ref_id:
            return None if path_ref.get("package") else "path_ref must include registry/id or package/relative_path"
        known = {
            "knowledge_roots": ("knowledge-roots.yaml", "knowledge_roots"),
            "package_roots": ("package-roots.yaml", "package_roots"),
            "templates": ("templates.yaml", "templates"),
            "tools": ("tools.yaml", "tools"),
            "mcp": ("mcp.yaml", "mcp_servers"),
            "private_resource_paths": ("private-resource-paths.yaml", "private_resource_paths"),
        }
        if registry in {"external_resources"}:
            return None
        if registry not in known:
            return f"unknown path_ref registry {registry}"
        registry_file, collection_key = known[registry]
        if ref_id not in self.dependencies.registry_ids(workplace_root, registry_file, collection_key):
            return f"path_ref target missing: {registry}/{ref_id}"
        return None

    def project_checks(self, project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None) -> list[Check]:
        checks: list[Check] = []
        checked = 0
        flow_root = self.inputs.locate_flow_root(project_root)
        for manifest_path in self.packages.candidates(project_root, distribution_root, workplace_manifest):
            manifest = self.inputs.load_yaml_document(manifest_path)
            if not manifest or yaml_error(manifest):
                continue
            resources = manifest.get("resources")
            if not isinstance(resources, list) or not resources:
                continue
            checked += 1
            package_id = str(manifest.get("id", manifest_path.stem))
            root_for_index = manifest_path.parent.parent if manifest_path.parent.name == "packages" else project_root
            if distribution_root:
                try:
                    manifest_path.relative_to(distribution_root)
                    root_for_index = distribution_root
                except ValueError:
                    pass
            index_path = self.index_path(manifest_path, root_for_index, package_id)
            project_local_package = path_is_relative_to(manifest_path, flow_root / "packages")
            if index_path.is_file():
                checks.append(check("PASS", f"knowledge resource index for {package_id} found"))
            elif project_local_package:
                checks.append(check("PASS", f"knowledge resource index for {package_id} optional for project-local package resources"))
            else:
                checks.append(
                    check_with_hint(
                        "WARN",
                        f"knowledge resource index for {package_id} missing",
                        f"Expected resource index: {rel(index_path, project_root)}",
                        f"python bin/pf.py knowledge-resource-index-build --project-root . --package {package_id} --apply",
                    )
                )
            for resource in resources:
                if not isinstance(resource, dict):
                    checks.append(check("FAIL", f"{package_id} contains non-object resource"))
                    continue
                normalized = self.records.normalize(resource, package_id)
                if "path" in resource and Path(str(resource.get("path"))).is_absolute():
                    checks.append(check("FAIL", f"{package_id}:{resource.get('id', 'resource')} exposes an absolute path instead of path_ref"))
                if "path_ref" not in normalized:
                    checks.append(check("FAIL", f"{package_id}:{resource.get('id', 'resource')} missing path_ref"))
                kind = str(resource.get("kind") or "reference")
                if kind in HEAVY_RESOURCE_KINDS and not resource.get("load_policy"):
                    checks.append(check("WARN", f"{package_id}:{resource.get('id', 'resource')} heavy resource should declare load_policy"))
        if checked == 0:
            checks.append(check("PASS", "knowledge resource indexes checked (no package resources declared)"))
        return checks
