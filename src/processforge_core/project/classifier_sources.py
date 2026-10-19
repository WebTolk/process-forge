"""Existing classifier discovery, registry sources and provenance labels."""

from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any

from ..common.paths import path_is_relative_to, rel
from ..common.values import as_list
from ..common.yaml_io import yaml_error
from ..process_catalog.official_read import OfficialProcessPackReader
from ..process_catalog.service import official_pack_manifest_records
from ..resources.registries import WorkplaceRegistryReader
from ..work.context_documents import ContextContractInputs
from .classification import ProjectClassifierRulePolicy
from .scan_policy import ProjectScanPolicy


class ProjectClassifierSourceReader:
    """Read current classifier inputs against an explicit distribution root."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root
        self.inputs = ContextContractInputs()
        self.classifier_rules = ProjectClassifierRulePolicy()

    def list_classifier_files(self, project_root: Path) -> list[Path]:
        """Walk product markers without entering flow state or excluded trees."""
        flow_root = self.inputs.locate_flow_root(project_root)
        ignored_names = {".git", ".idea", ".serena", "__pycache__", "runtime", "cache"}
        files: list[Path] = []
        for directory, dirnames, filenames in os.walk(project_root, topdown=True, followlinks=False):
            parent = Path(directory)
            retained = []
            for name in dirnames:
                path = parent / name
                if name in ignored_names or path == flow_root:
                    continue
                try:
                    info = path.lstat()
                except OSError:
                    continue
                # Windows junctions are reparse points but need not be symlinks.
                # Neither may reintroduce flow state through an alias or cycle.
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    continue
                retained.append(name)
            dirnames[:] = retained
            for name in filenames:
                path = parent / name
                if name not in ignored_names and path.is_file():
                    files.append(path)
        return sorted(files, key=lambda item: item.relative_to(project_root).as_posix())

    def project_classifier_registry_documents(
        self,
        workplace_manifest: Path | None,
        project_root: Path,
    ) -> list[tuple[dict[str, Any], Path]]:
        documents: list[tuple[dict[str, Any], Path]] = []
        if workplace_manifest and workplace_manifest.is_file():
            registry = WorkplaceRegistryReader(inputs=self.inputs).load_workplace_registry(workplace_manifest, "project_classifiers", "project-classifiers.yaml")
            documents.append((registry, workplace_manifest.parent))
        flow_registry = self.inputs.locate_flow_root(project_root) / "registries" / "project-classifiers.yaml"
        if flow_registry.is_file():
            data = self.inputs.load_yaml_document(flow_registry)
            if isinstance(data, dict) and not yaml_error(data):
                documents.append((data, flow_registry.parent.parent))
        for manifest_path, manifest in OfficialProcessPackReader(workplace_manifest, distribution_root=self.distribution_root).active_records():
            provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
            declared_ids = {str(item) for item in as_list(provided.get("project_classifiers")) if str(item)}
            registry_path = manifest_path.parent / "project-classifiers" / "registry-entry.yaml"
            registry = self.inputs.load_yaml_document(registry_path)
            if not isinstance(registry, dict) or yaml_error(registry):
                continue
            entries = [
                entry
                for entry in as_list(registry.get("project_classifiers"))
                if isinstance(entry, dict)
                and (not declared_ids or str(entry.get("id") or "") in declared_ids)
            ]
            documents.append(
                (
                    {"schema_version": 1, "project_classifiers": entries},
                    manifest_path.parent,
                )
            )
        return documents

    def project_classifier_paths(
        self,
        workplace_manifest: Path | None,
        project_root: Path,
        explicit_paths: list[Path] | None = None,
    ) -> list[Path]:
        candidates = [path.expanduser().resolve() for path in explicit_paths or []]
        for registry, base in self.project_classifier_registry_documents(workplace_manifest, project_root):
            entries = registry.get("project_classifiers")
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or str(entry.get("status", "active")) not in {"active", "enabled", "configured"}:
                    continue
                raw_path = entry.get("path")
                if raw_path:
                    candidates.append(WorkplaceRegistryReader(inputs=self.inputs).resolve_registry_relative_path(base, str(raw_path), workplace_manifest))
        unique: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen and resolved.is_file():
                seen.add(resolved)
                unique.append(resolved)
        return unique

    def project_available_paths(self, project_root: Path, files: list[Path] | None = None) -> set[str]:
        """Product markers for classification, excluding PF's own flow state."""
        source_files = files if files is not None else self.list_classifier_files(project_root)
        flow_root = self.inputs.locate_flow_root(project_root)
        # Receipts and captured fixtures are not application manifests. Classifier
        # definitions in the flow registry are loaded separately and remain usable.
        source_files = [path for path in source_files if not path.is_relative_to(flow_root)]
        available_paths = {rel(path, project_root) for path in source_files}
        for path in source_files:
            parent = path.relative_to(project_root).parent
            while parent != Path("."):
                available_paths.add(parent.as_posix())
                parent = parent.parent
        available_paths.update(
            path.name
            for path in project_root.iterdir()
            if path.is_dir() and path != flow_root and path.name not in {".git", ".idea", ".serena"}
        )
        return available_paths

    def processforge_distribution_root_for_path(self, path: Path) -> Path | None:
        """Return the nearest ProcessForge distribution owning ``path``."""
        resolved = path.resolve()
        for candidate in (resolved.parent, *resolved.parents):
            if ProjectScanPolicy.looks_like_processforge_distribution(candidate):
                return candidate
        return None

    def project_classifier_source_label(
        self,
        path: Path, project_root: Path, *, workplace_manifest: Path | None = None
    ) -> str:
        """Render classifier provenance stably across source and installed layouts."""
        distribution_root = self.processforge_distribution_root_for_path(path)
        if workplace_manifest is not None and distribution_root is not None:
            workplace_root = workplace_manifest.parent.resolve()
            if path_is_relative_to(path, workplace_root) and not path_is_relative_to(distribution_root, workplace_root):
                distribution_root = None
        if path_is_relative_to(path, project_root):
            if distribution_root and distribution_root == project_root.resolve():
                return rel(path, distribution_root)
            return rel(path, project_root)
        if distribution_root:
            return rel(path, distribution_root)
        return path.name

    def inactive_official_classifier_hints(self, workplace_manifest: Path | None, project_root: Path, files: list[Path] | None = None) -> list[str]:
        active_ids = OfficialProcessPackReader(workplace_manifest, distribution_root=self.distribution_root).active_ids()
        available_paths = self.project_available_paths(project_root, files)
        hints: list[str] = []
        seen: set[str] = set()
        for manifest_path, manifest in official_pack_manifest_records(self.distribution_root):
            pack_id = str(manifest.get("id") or "")
            if not pack_id or pack_id in active_ids:
                continue
            provided = manifest.get("provides") if isinstance(manifest.get("provides"), dict) else {}
            declared_ids = {str(item) for item in as_list(provided.get("project_classifiers")) if str(item)}
            if not declared_ids:
                continue
            registry_path = manifest_path.parent / "project-classifiers" / "registry-entry.yaml"
            registry = self.inputs.load_yaml_document(registry_path)
            if not isinstance(registry, dict) or yaml_error(registry):
                continue
            for entry in as_list(registry.get("project_classifiers")):
                if not isinstance(entry, dict) or str(entry.get("status", "active")) not in {"active", "enabled", "configured"}:
                    continue
                classifier_id = str(entry.get("id") or "")
                if classifier_id and classifier_id not in declared_ids:
                    continue
                raw_path = entry.get("path")
                if not raw_path:
                    continue
                classifier_path = WorkplaceRegistryReader(inputs=self.inputs).resolve_registry_relative_path(manifest_path.parent, str(raw_path), workplace_manifest)
                classifier = self.inputs.load_yaml_document(classifier_path)
                if (
                    not isinstance(classifier, dict)
                    or yaml_error(classifier)
                    or classifier.get("kind") != "processforge.project_classifier"
                    or str(classifier.get("status", "active")) != "active"
                ):
                    continue
                for rule in classifier.get("rules", []) if isinstance(classifier.get("rules"), list) else []:
                    if not isinstance(rule, dict) or not self.classifier_rules.matches(rule, available_paths):
                        continue
                    key = f"{pack_id}:{classifier_id or classifier.get('id')}"
                    if key in seen:
                        continue
                    seen.add(key)
                    hints.append(
                        f"{pack_id} could classify this project via {classifier.get('id') or classifier_id}; "
                        f"activate with `python bin/pf.py pack-activate --id {pack_id} --workplace <workplace-root> --apply`, "
                        "then rerun project-context-refresh."
                    )
        return hints
