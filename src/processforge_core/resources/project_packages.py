"""Live project package discovery and its legacy public root representation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.values import as_list, list_value
from ..common.yaml_io import _parse_simple_yaml, yaml_error
from ..documents.reader import YamlDocumentReader
from ..process_catalog.official_read import OfficialProcessPackReader
from ..project.metadata import ProjectMetadataReader
from ..work.context_documents import ContextContractInputs
from .snapshot import WorkspacePathReferenceReader, _PackageRootResolution


@dataclass
class PackageRootResolution:
    root_id: str
    original_path: str
    resolved_path: Path
    status: str
    warnings: list[str]
    fallback: bool = False
    entry: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProjectPackageCatalogReader:
    distribution_root: Path

    def root_from_entry(self, workplace_root: Path, entry: dict[str, Any]) -> PackageRootResolution:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        root = paths.package_root_resolution_from_entry(workplace_root, entry)
        return self._public_root(root)

    def _public_root(self, root: _PackageRootResolution) -> PackageRootResolution:
        return PackageRootResolution(
            root_id=root.root_id,
            original_path=root.original_path,
            resolved_path=root.resolved_path,
            status=root.status,
            warnings=root.warnings,
            fallback=root.fallback,
            entry=root.entry,
        )

    def root_entries(self, workplace_root: Path) -> list[dict[str, Any]]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        return paths.package_root_entries(workplace_root)

    def resolve_root(self, workplace_root: Path, package_root_id: str | None = None, *, mode: str = "read") -> PackageRootResolution:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        return self._public_root(paths.resolve_package_root(workplace_root, package_root_id, mode=mode))

    def path_candidates(self, root_path: Path, package_id: str) -> list[Path]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            root_path, root_path,
            inputs=ContextContractInputs(documents=documents),
        )
        return paths.package_path_candidates(root_path, package_id)

    def resolve_path(self, workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[PackageRootResolution, Path]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        root, path = paths.resolve_package_path(workplace_root, package_id, package_root_id, mode=mode)
        return self._public_root(root), path

    def find_manifests(self, workplace_root: Path, package_id: str) -> list[tuple[PackageRootResolution, Path]]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        manifests = paths.find_workplace_package_manifests(workplace_root, package_id)
        public_roots: dict[int, PackageRootResolution] = {}
        public_manifests: list[tuple[PackageRootResolution, Path]] = []
        for root, path in manifests:
            identity = id(root)
            if identity not in public_roots:
                public_roots[identity] = self._public_root(root)
            public_manifests.append((public_roots[identity], path))
        return public_manifests

    def load_manifest(self, workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[Path, dict[str, Any], PackageRootResolution]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root,
            inputs=ContextContractInputs(documents=documents),
        )
        path, data, root = paths.load_workplace_package_manifest(workplace_root, package_id, package_root_id, mode=mode)
        return path, data, self._public_root(root)

    def workplace_roots(self, workplace_manifest: Path | None) -> list[PackageRootResolution]:
        if not workplace_manifest or not workplace_manifest.is_file():
            return []
        workplace_root = workplace_manifest.parent
        documents = YamlDocumentReader(_parse_simple_yaml)
        paths = WorkspacePathReferenceReader(
            workplace_root, workplace_root, workplace_manifest=workplace_manifest,
            inputs=ContextContractInputs(documents=documents),
        )
        return [self.root_from_entry(workplace_root, entry) for entry in paths.package_root_entries(workplace_root)]

    def workplace_root_paths(self, workplace_manifest: Path | None) -> list[Path]:
        return [root.resolved_path for root in self.workplace_roots(workplace_manifest)]

    def candidates(self, project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None = None) -> list[Path]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        project = ProjectMetadataReader(project_root, documents=documents)
        flow_root = project.flow_root()
        candidates: list[Path] = []
        candidates.extend(project.manifest_path_refs("packages"))
        roots: list[Path | None] = [
            flow_root / "packages",
            distribution_root / "packages" if distribution_root else None,
            (distribution_root or self.distribution_root) / "seeds" / "knowledge-packages",
        ]
        roots.extend(self.workplace_root_paths(workplace_manifest))
        for root in roots:
            if root and root.is_dir():
                candidates.extend(sorted(root.glob("*.yaml")))
                candidates.extend(sorted(root.glob("*.yml")))
                candidates.extend(sorted(root.glob("*/package.yaml")))
                candidates.extend(sorted(root.glob("*/package.yml")))
        for process_pack_path, process_pack in OfficialProcessPackReader(
            workplace_manifest, distribution_root=self.distribution_root, documents=documents,
        ).active_records():
            provided = process_pack.get("provides") if isinstance(process_pack.get("provides"), dict) else {}
            for package_id in as_list(provided.get("knowledge_packages")):
                if not package_id:
                    continue
                package_path = process_pack_path.parent / "knowledge-packages" / f"{package_id}.yaml"
                if package_path.is_file():
                    candidates.append(package_path)
        unique: list[Path] = []
        seen: set[Path] = set()
        for path in candidates:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)
        return unique

    def index(self, project_root: Path, distribution_root: Path | None, workplace_manifest: Path | None = None) -> dict[str, dict[str, Any]]:
        documents = YamlDocumentReader(_parse_simple_yaml)
        index: dict[str, dict[str, Any]] = {}
        duplicates: dict[str, list[str]] = {}
        workplace_roots = self.workplace_roots(workplace_manifest)
        for path in self.candidates(project_root, distribution_root, workplace_manifest):
            data = documents.load(path)
            if not data or yaml_error(data):
                continue
            package_id = data.get("id")
            if not package_id:
                continue
            record = dict(data)
            record["__manifest_path"] = path
            for root in workplace_roots:
                try:
                    path.relative_to(root.resolved_path)
                    record["__package_root_id"] = root.root_id
                    break
                except ValueError:
                    continue
            if str(package_id) in index:
                duplicates.setdefault(str(package_id), [index[str(package_id)]["__manifest_path"].as_posix()]).append(path.as_posix())
            index[str(package_id)] = record
        if duplicates:
            index["__duplicates__"] = {"packages": duplicates}
        return index

    def dependencies(self, manifest: dict[str, Any]) -> list[str]:
        dependencies = set(list_value(manifest.get("dependencies")))
        requires = manifest.get("requires") if isinstance(manifest.get("requires"), dict) else {}
        dependencies.update(list_value(requires.get("knowledge_packages")))
        return sorted(item for item in dependencies if item)
