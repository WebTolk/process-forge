"""Validate current workplace registry paths through concrete Core readers."""

from __future__ import annotations

from pathlib import Path

from ..common.checks import Check, check
from ..common.text import check_with_hint
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..resources.project_packages import ProjectPackageCatalogReader
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs


class WorkplaceRegistryValidationService:
    """Preserve ordered registry diagnostics using current operation roots."""

    def __init__(self, distribution_root: Path) -> None:
        self.documents = YamlDocumentReader(_parse_simple_yaml)
        self.inputs = ContextContractInputs(documents=self.documents)
        self.package_catalog = ProjectPackageCatalogReader(distribution_root)

    def paths(self, workplace_root: Path, workplace_manifest: Path) -> list[Check]:
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root, workplace_manifest=workplace_manifest,
            inputs=self.inputs,
        )
        checks: list[Check] = []
        constants = paths.load_workplace_path_constants(workplace_manifest, workplace_root)
        manifest_data = self.documents.load(workplace_manifest)
        registries = manifest_data.get("registries", {}) if isinstance(manifest_data.get("registries"), dict) else {}
        for key, default_name in [
            ("distributions", "distributions.yaml"),
            ("platforms", "platforms.yaml"),
            ("knowledge_roots", "knowledge-roots.yaml"),
            ("package_roots", "package-roots.yaml"),
            ("templates", "templates.yaml"),
            ("tools", "tools.yaml"),
            ("mcp", "mcp.yaml"),
            ("process_packs", "process-packs.yaml"),
        ]:
            raw_path = str(registries.get(key) or f"registries/{default_name}")
            resolution = paths.resolve_path_with_constants(raw_path, workplace_root, constants)
            errors = resolution.get("errors", [])
            if errors:
                checks.append(check("FAIL", f"registry {key} path failed: {', '.join(errors)}"))
            else:
                path = paths.path_resolution_to_path(resolution)
                checks.append(check("PASS" if path.is_file() else "FAIL", f"registry {key} resolves to {paths.normalize_path_string(str(path))}"))
        registry_specs = [
            ("knowledge-roots.yaml", "knowledge_roots", "path"),
            ("package-roots.yaml", "package_roots", "path"),
            ("templates.yaml", "template_roots", "path"),
            ("tools.yaml", "tools", "command"),
            ("mcp.yaml", "mcp_servers", "command"),
        ]
        for registry_file, collection_key, path_key in registry_specs:
            registry_path = paths.resolve_registry_path(workplace_manifest, collection_key if collection_key != "mcp_servers" else "mcp", registry_file)
            if collection_key == "template_roots":
                registry_path = paths.resolve_registry_path(workplace_manifest, "templates", registry_file)
            elif collection_key == "tools":
                registry_path = paths.resolve_registry_path(workplace_manifest, "tools", registry_file)
            elif collection_key == "knowledge_roots":
                registry_path = paths.resolve_registry_path(workplace_manifest, "knowledge_roots", registry_file)
            elif collection_key == "package_roots":
                registry_path = paths.resolve_registry_path(workplace_manifest, "package_roots", registry_file)
            if not registry_path.is_file():
                continue
            data = self.documents.load(registry_path)
            entries = data.get(collection_key) if isinstance(data, dict) else None
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get(path_key):
                    continue
                entry_id = str(entry.get("id", "entry"))
                resolution = paths.resolve_path_with_constants(str(entry[path_key]), workplace_root, constants)
                errors = resolution.get("errors", [])
                if errors:
                    checks.append(check("FAIL", f"{collection_key}.{entry_id}.{path_key} failed: {', '.join(errors)}"))
                    continue
                if path_key == "path":
                    resolved_path = paths.path_resolution_to_path(resolution)
                    requires_existing = str(entry.get("status", "available")) == "available" or bool(entry.get("must_exist", False))
                    level = "PASS" if resolved_path.exists() or not requires_existing else "WARN"
                    checks.append(check(level, f"{collection_key}.{entry_id}.path resolves ({resolution.get('path_status')})"))
                else:
                    checks.append(check("PASS", f"{collection_key}.{entry_id}.{path_key} resolves constants"))
        return checks

    def packages(self, workplace_root: Path) -> list[Check]:
        checks: list[Check] = []
        registry_path = workplace_root / "registries" / "package-roots.yaml"
        if not registry_path.is_file():
            return [check("WARN", "registries/package-roots.yaml missing; package writes will use fallback <workplace-root>/packages")]
        entries = self.package_catalog.root_entries(workplace_root)
        if not entries:
            return [check("WARN", "package_roots registry is empty; package writes will use fallback <workplace-root>/packages")]
        ids: dict[str, int] = {}
        for entry in entries:
            root_id = str(entry.get("id", ""))
            ids[root_id] = ids.get(root_id, 0) + 1
        for root_id, count in sorted(ids.items()):
            checks.append(check("FAIL" if count > 1 else "PASS", f"package_root id {root_id or '<missing>'} unique"))
        selectable = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            root = self.package_catalog.root_from_entry(workplace_root, entry)
            label = f"package_root {root.root_id}"
            if root.warnings:
                checks.append(
                    check_with_hint(
                        "FAIL",
                        f"{label} path cannot resolve: {'; '.join(root.warnings)}",
                        "The package root registry points to a path ProcessForge cannot use.",
                        "edit registries/package-roots.yaml so this package_root path exists and is relative to the workplace when possible",
                    )
                )
                continue
            exists = root.resolved_path.is_dir()
            status = str(entry.get("status", "available"))
            must_exist = status == "available" or bool(entry.get("must_exist", False))
            checks.append(
                check("PASS", f"{label} path exists")
                if exists or not must_exist
                else check_with_hint(
                    "FAIL",
                    f"{label} path missing",
                    "This package_root is marked available or must_exist but the directory is absent.",
                    f"create the package root directory or update registries/package-roots.yaml for {root.root_id}",
                )
            )
            if exists and status == "available":
                selectable = True
            if str(entry.get("writable", True)).lower() != "false" and exists:
                checks.append(check("PASS", f"{label} writable candidate"))
        checks.append(
            check("PASS", "default/first available package_root can be selected")
            if selectable
            else check_with_hint(
                "FAIL",
                "default/first available package_root can be selected",
                "Authoring commands need at least one available package_root unless every write passes an explicit --package-root.",
                "python bin/pf.py workplace-init --workplace <workplace-root> --apply",
                "add an available entry to registries/package-roots.yaml",
            )
        )
        return checks
