"""Knowledge package diagnostics through concrete live Core readers."""

from __future__ import annotations

from pathlib import Path

from ..common.checks import Check, check
from ..common.paths import rel
from ..common.policies import policy_entries, policy_id_matches
from ..common.privacy import is_public_path_safe
from ..common.text import check_with_hint
from ..common.yaml_io import yaml_error
from ..maintenance.documents import UpdateDocumentReader
from ..work.context_documents import ContextContractInputs
from .index_checks import KnowledgeResourceIndexService
from .project_packages import ProjectPackageCatalogReader
from .records import HEAVY_RESOURCE_KINDS, ResourceRecordService


class KnowledgePackageValidationService:
    """Observe each supplied workplace without retaining parsed documents."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.packages = ProjectPackageCatalogReader(distribution_root)
        self.documents = UpdateDocumentReader(distribution_root)
        self.inputs = ContextContractInputs()
        self.records = ResourceRecordService()
        self.indexes = KnowledgeResourceIndexService(distribution_root)

    def doctor(self, workplace_root: Path, package_id: str, package_root_id: str | None = None) -> list[Check]:
        manifest_path, manifest, package_root = self.packages.load_manifest(workplace_root, package_id, package_root_id, mode="read")
        checks: list[Check] = []
        if not manifest_path.is_file():
            return [
                check_with_hint(
                    "FAIL",
                    f"package {package_id} manifest missing",
                    "The package id cannot be resolved through registries/package-roots.yaml.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {package_id} --package-root global --title \"{package_id}\" --apply",
                )
            ]
        for warning in package_root.warnings:
            level = "WARN" if warning.startswith("WARN:") else "FAIL"
            checks.append(
                check_with_hint(
                    level,
                    warning,
                    "The package_root resolver found a registry/path issue.",
                    "check registries/package-roots.yaml and pass --package-root when multiple roots contain the same package id",
                )
            )
        checks.append(check("PASS", f"package {package_id} resolved through package root {package_root.root_id}"))
        loaded = self.documents.doctor_yaml(
            manifest_path,
            "package-manifest.schema.json",
            f"package {package_id} manifest",
            checks,
        )
        if loaded is None:
            return checks
        manifest = loaded
        resources = manifest.get("resources") if isinstance(manifest.get("resources"), list) else []
        for resource in resources:
            if not isinstance(resource, dict):
                checks.append(check("FAIL", f"package {package_id} contains non-object resource"))
                continue
            resource_id = str(resource.get("id", "resource"))
            normalized = self.records.normalize(resource, package_id, workplace_root)
            missing = self.indexes.path_ref_missing(workplace_root, normalized)
            checks.append(
                check("PASS", f"{package_id}:{resource_id} path_ref resolved")
                if not missing
                else check_with_hint(
                    "FAIL",
                    f"{package_id}:{resource_id} path_ref - {missing}",
                    "Public resource records must resolve through a known registry instead of embedding private paths.",
                    "update the resource to use path_ref.registry and path_ref.id from the workplace registries",
                )
            )
            kind = str(resource.get("kind") or "reference")
            if kind in HEAVY_RESOURCE_KINDS and not resource.get("load_policy"):
                checks.append(check("WARN", f"{package_id}:{resource_id} heavy resource should declare load_policy"))
            elif kind in HEAVY_RESOURCE_KINDS and str(resource.get("load_policy")) in {"always_index", "session_start", "project_init"}:
                checks.append(check("WARN", f"{package_id}:{resource_id} heavy resource should normally use on_demand"))
        index_path = self.indexes.index_path(manifest_path, workplace_root, package_id)
        if index_path.is_file():
            index = self.inputs.load_yaml_document(index_path)
            checks.append(check("PASS" if not yaml_error(index) else "FAIL", f"{rel(index_path, workplace_root)} is valid YAML"))
            indexed_ids = {str(item.get("id")) for item in index.get("resources", []) if isinstance(item, dict)}
            for resource in resources:
                if isinstance(resource, dict) and str(resource.get("id")) not in indexed_ids:
                    checks.append(check("WARN", f"{package_id}:{resource.get('id')} missing from resource index"))
        else:
            checks.append(check("WARN", f"{rel(index_path, workplace_root)} missing; run knowledge-index-refresh --apply"))
        text = manifest_path.read_text(encoding="utf-8", errors="replace")
        checks.append(check("PASS" if is_public_path_safe(text) else "FAIL", f"package {package_id} manifest has no private absolute paths"))
        navigation = manifest.get("navigation") if isinstance(manifest.get("navigation"), dict) else {}
        if navigation:
            checks.append(check("PASS", f"package {package_id} navigation configured"))
            allowed_sections = {"source_code", "development_articles", "documentation", "api_reference", "usage_rules"}
            for section in navigation:
                checks.append(check("PASS" if str(section) in allowed_sections else "WARN", f"navigation section recognized: {section}"))
        elif package_id.startswith("docs."):
            checks.append(check("WARN", f"package {package_id} navigation configured"))
        dependencies = self.packages.dependencies(manifest)
        package_index = self.packages.index(workplace_root, None, workplace_root / "workplace.yaml")
        for dependency_id in dependencies:
            checks.append(
                check("PASS", f"required knowledge package dependency available: {dependency_id}")
                if dependency_id in package_index
                else check_with_hint(
                    "FAIL",
                    f"required knowledge package dependency available: {dependency_id}",
                    "The package manifest declares this dependency generically.",
                    f"python bin/pf.py knowledge-package-create --workplace <workplace-root> --id {dependency_id} --package-root global --title \"{dependency_id}\" --apply",
                )
            )
        package_policy = self.inputs.documents.policy("package-id-policy.yaml", distribution_root=self.distribution_root)
        for entry in policy_entries(package_policy, "package_id_rules"):
            if policy_id_matches(package_id, entry):
                level = str(entry.get("level", "WARN")).upper()
                checks.append(
                    check_with_hint(
                        "FAIL" if level == "FAIL" else "WARN",
                        str(entry.get("message", f"package id policy matched: {package_id}")),
                        str(entry.get("why", "The package id matched a data-driven package id policy.")),
                        str(entry.get("fix", "update the package id or policy manifest")),
                    )
                )
        return checks
