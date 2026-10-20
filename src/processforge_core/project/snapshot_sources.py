"""Concrete current-byte inputs for the existing project context snapshot."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.digests import FileDigestReader
from ..common.ids import safe_id
from ..common.paths import rel
from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..process_catalog.official_read import OfficialProcessPackReader
from .metadata import ProjectMetadataReader

__all__ = ()


def local_workplace_manifest_reference(local_text: str) -> Path | None:
    """Retain the raw-text local manifest reference, independently of YAML."""
    manifest_pattern = r"(?m)^\s*" + "manifest:" + r"\s*(.+?)\s*$"
    match = re.search(manifest_pattern, local_text)
    if not match:
        return None
    value = match.group(1).strip().strip('"').strip("'")
    return Path(value)


@dataclass(frozen=True)
class ProjectSnapshotSourcesReader:
    """Collect ordered live fingerprints without context policy or writes."""

    project_root: Path
    distribution_root: Path = field(
        default_factory=lambda: Path(__file__).parents[3], kw_only=True
    )
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
        kw_only=True,
        repr=False,
        compare=False,
    )
    digests: FileDigestReader = field(
        default_factory=FileDigestReader, kw_only=True, repr=False, compare=False
    )

    @staticmethod
    def _workplace_manifest_path(local_config: Path) -> Path | None:
        workplace = local_workplace_manifest_reference(
            local_config.read_text(encoding="utf-8", errors="replace"),
        )
        if workplace is None:
            return None
        workplace_path = workplace.expanduser()
        if not workplace_path.is_absolute():
            workplace_path = (local_config.parent / workplace_path).resolve()
        return workplace_path

    def _official_pack_sources(
        self,
        workplace_path: Path,
    ) -> Iterator[tuple[Path, str, str]]:
        packs = OfficialProcessPackReader(
            workplace_path,
            distribution_root=self.distribution_root,
            documents=self.documents,
        )
        for manifest_path, manifest in packs.active_records():
            pack_id = str(manifest.get("id") or manifest_path.parent.name)
            paths = [manifest_path]
            paths.extend(
                sorted((manifest_path.parent / "project-classifiers").glob("*.yaml"))
            )
            for path in paths:
                source_id = safe_id(
                    f"official-pack-{pack_id}-{path.stem}", "official-pack"
                )
                display = f"<distribution-pack>/{pack_id}/{path.relative_to(manifest_path.parent).as_posix()}"
                yield path, source_id, display

    def official_pack_checksum_variants(
        self,
        source_ids: set[str],
    ) -> dict[str, tuple[str, str, str]]:
        """Read raw, LF and CRLF digests for selected live official sources.

        This operation does not change recorded raw fingerprints or cache bytes
        between checks. The first digest lets the policy detect a write between
        its initial fingerprint read and this representation comparison.
        """
        if not source_ids:
            return {}
        local_config = (
            ProjectMetadataReader(self.project_root, self.documents).flow_root()
            / "process-forge.local.yaml"
        )
        if not local_config.is_file():
            return {}
        workplace_path = self._workplace_manifest_path(local_config)
        if workplace_path is None:
            return {}
        variants: dict[str, tuple[str, str, str]] = {}
        for path, source_id, _display in self._official_pack_sources(workplace_path):
            if source_id not in source_ids or not path.is_file():
                continue
            content = path.read_bytes()
            lf_content = content.replace(b"\r\n", b"\n")
            variants[source_id] = (
                self.digests.sha256_bytes(content),
                self.digests.sha256_bytes(lf_content),
                self.digests.sha256_bytes(lf_content.replace(b"\n", b"\r\n")),
            )
        return variants

    def fingerprint(
        self,
        path: Path,
        source_id: str,
        kind: str,
        *,
        private: bool = False,
        display_path: str | None = None,
    ) -> dict[str, Any]:
        exists = path.is_file()
        record: dict[str, Any] = {
            "id": source_id,
            "path": display_path or rel(path, self.project_root),
            "kind": kind,
            "checksum": self.digests.sha256_file(path) if exists else "missing",
        }
        if private:
            record["private"] = True
        if not exists:
            record["exists"] = False
        return record

    def read(self) -> list[dict[str, Any]]:
        project_root = self.project_root
        metadata = ProjectMetadataReader(project_root, self.documents)
        flow_root = metadata.flow_root()
        sources: list[dict[str, Any]] = [
            self.fingerprint(
                flow_root / "process-forge.yaml", "project_manifest", "manifest"
            ),
        ]
        local_config = flow_root / "process-forge.local.yaml"
        if local_config.is_file():
            sources.append(
                self.fingerprint(
                    local_config, "local_config", "local-config", private=True
                )
            )
            workplace_path = self._workplace_manifest_path(local_config)
            if workplace_path is not None:
                sources.append(
                    self.fingerprint(
                        workplace_path,
                        "workplace_manifest",
                        "workplace",
                        private=True,
                        display_path="<private-workplace-manifest-ref>",
                    )
                )
                workplace_root = workplace_path.parent
                for rel_path, kind in [
                    (
                        "registries/specializations.yaml",
                        "workplace-specialization-registry",
                    ),
                    (
                        "registries/project-classifiers.yaml",
                        "workplace-project-classifier-registry",
                    ),
                    (
                        "registries/process-packs.yaml",
                        "workplace-process-pack-registry",
                    ),
                    ("registries/tools.yaml", "workplace-tool-registry"),
                    ("registries/mcp.yaml", "workplace-mcp-registry"),
                    ("registries/templates.yaml", "workplace-template-registry"),
                    ("registries/parameters.yaml", "workplace-parameter-registry"),
                ]:
                    path = workplace_root / rel_path
                    if path.is_file():
                        sources.append(
                            self.fingerprint(
                                path,
                                safe_id(f"{kind}-{rel_path}", kind),
                                kind,
                                private=True,
                                display_path=f"<private-workplace-ref>/{rel_path}",
                            )
                        )
                for path, source_id, display_path in self._official_pack_sources(
                    workplace_path
                ):
                    sources.append(
                        self.fingerprint(
                            path,
                            source_id,
                            "official-process-pack",
                            private=True,
                            display_path=display_path,
                        )
                    )
                for dirname, kind in [
                    ("specializations", "workplace-specialization"),
                    ("specializations/user", "workplace-specialization"),
                    ("specializations/custom", "workplace-specialization"),
                    ("project-classifiers", "workplace-project-classifier"),
                ]:
                    root = workplace_root / dirname
                    if root.is_dir():
                        for path in sorted(
                            item for item in root.glob("*.y*ml") if item.is_file()
                        ):
                            sources.append(
                                self.fingerprint(
                                    path,
                                    safe_id(f"{kind}-{dirname}-{path.name}", kind),
                                    kind,
                                    private=True,
                                    display_path=f"<private-workplace-ref>/{dirname}/{path.name}",
                                )
                            )
        for path in metadata.manifest_path_refs("processes"):
            source_id = safe_id(f"process-{rel(path, project_root)}", "process-source")
            sources.append(self.fingerprint(path, source_id, "process"))
        for path in metadata.manifest_path_refs("packages"):
            source_id = safe_id(f"package-{rel(path, project_root)}", "package-source")
            sources.append(self.fingerprint(path, source_id, "package"))
        overrides = flow_root / "project-overrides.yaml"
        if overrides.is_file():
            sources.append(
                self.fingerprint(overrides, "project-overrides", "project-overrides")
            )
        for path, source_id, private in [
            (flow_root / "parameters.yaml", "project-parameters", False),
            (flow_root / "parameters.local.yaml", "project-local-parameters", True),
        ]:
            if path.is_file():
                sources.append(
                    self.fingerprint(
                        path, source_id, "project-parameters", private=private
                    )
                )
        for dirname, kind in [
            ("processes", "process-override"),
            ("packages", "package-override"),
            ("registries", "registry"),
            ("project-classifiers", "project-classifier"),
            ("templates", "template-override"),
            ("specializations", "specialization"),
            ("specializations/overrides", "specialization-override"),
            ("tools/overrides", "tool-override"),
            ("mcp/overrides", "mcp-override"),
            ("knowledge", "project-knowledge"),
            ("rules", "project-rules"),
        ]:
            root = flow_root / dirname
            if root.is_dir():
                for path in sorted(
                    item
                    for item in root.rglob("*")
                    if item.is_file()
                    and item.suffix.lower() in {".yaml", ".yml", ".json", ".md"}
                ):
                    source_id = safe_id(
                        f"{kind}-{rel(path, flow_root)}", f"{kind}-source"
                    )
                    sources.append(self.fingerprint(path, source_id, kind))
        return sources
