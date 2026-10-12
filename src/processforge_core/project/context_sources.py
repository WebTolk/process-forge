"""Existing broad context source records and ordered live inventory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.digests import FileDigestReader
from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from .metadata import ProjectMetadataReader


@dataclass(frozen=True)
class ProjectContextSourcesReader:
    """Read the ordered broad context inventory from current bytes."""
    project_root: Path
    documents: YamlDocumentReader = field(default_factory=lambda: YamlDocumentReader(_parse_simple_yaml), kw_only=True, repr=False, compare=False)
    digests: FileDigestReader = field(default_factory=FileDigestReader, kw_only=True, repr=False, compare=False)

    def record(self, path: Path, kind: str, required: bool, selection_reason: str, load_policy: str) -> dict[str, Any]:
        root = self.project_root
        exists = path.is_file()
        record: dict[str, Any] = {'path': rel(path, root), 'kind': kind, 'required': required, 'exists': exists, 'selection_reason': selection_reason, 'load_policy': load_policy}
        if exists:
            checksum = self.digests.sha256_file(path)
            record['checksum'] = checksum
            record['fingerprint'] = checksum
        else:
            record['checksum'] = 'missing'
            record['fingerprint'] = 'missing'
        return record

    def read(self, assignment: Path | None=None) -> list[dict[str, Any]]:
        project_root = self.project_root
        metadata = ProjectMetadataReader(project_root, self.documents)
        flow_root = metadata.flow_root()
        root_boot = project_root / 'AGENTS.md'
        has_root_boot = root_boot.is_file()
        candidates: list[tuple[Path, str, bool]] = [(root_boot if has_root_boot else flow_root / 'AGENTS.md', 'agent-boot', True), (flow_root / 'process-forge.yaml', 'project-flow', True), (flow_root / 'process-forge.local.yaml', 'local-config', False), (project_root / 'tools' / 'processforge.py', 'tool', False)]
        if has_root_boot:
            candidates.append((flow_root / 'AGENTS.md', 'agent-extended', False))
        candidates.extend(((path, 'process', False) for path in metadata.manifest_path_refs('processes')))
        candidates.extend(((path, 'package', False) for path in metadata.manifest_path_refs('packages')))
        for dirname, kind in [('processes', 'process'), ('packages', 'package')]:
            root = flow_root / dirname
            if root.is_dir():
                candidates.extend(((path, kind, False) for path in sorted(root.glob('*.yaml'))))
        template_root = flow_root / 'templates'
        if template_root.is_dir():
            candidates.extend(((path, 'template', False) for path in sorted(template_root.glob('*.yaml'))))
            candidates.extend(((path, 'template', False) for path in sorted(template_root.glob('*.md'))))
        if assignment is not None:
            candidates.append((assignment, 'assignment', True))
        seen: set[Path] = set()
        records: list[dict[str, Any]] = []
        for path, kind, required in candidates:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if required:
                reason = 'required for session bootstrap' if kind != 'assignment' else 'required by context compile assignment'
                if kind == 'agent-boot' and (not has_root_boot):
                    reason = 'legacy compatibility entry; root AGENTS.md is absent'
                policy = 'read_required'
            elif kind == 'agent-extended':
                reason = 'extended PF instructions; load when current obligations require them'
                policy = 'available'
            elif kind in {'process', 'package', 'template'}:
                reason = 'available in broad project context; not loaded by default for workers'
                policy = 'available'
            elif kind == 'local-config':
                reason = 'optional private local config'
                policy = 'recommended_if_present'
            else:
                reason = 'supporting context source'
                policy = 'recommended'
            records.append(self.record(path, kind, required, reason, policy))
        return records
