"""Live catalog reads owned by Core, independent of CLI and Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..project.metadata import ProjectMetadataReader
from ..work.context_documents import ContextContractInputs
from . import service
from .models import ProcessCatalogContext, ProcessDefinitionRef


_PATH_CONSTANT = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
_DEFAULT_PATH_CONSTANTS = {
    "PF_WORKPLACE": ".",
    "PF_DISTRIBUTION": "distributions/processforge",
    "PF_KNOWLEDGE": "knowledge",
    "PF_TEMPLATES": "reusable-templates",
    "PF_TOOLS": "tools",
    "PF_MCP": "mcp",
    "PF_PLATFORM_CONTRACTS": "platform-contracts",
    "PF_SPECIALIZATIONS": "specializations",
    "PF_PROCESS_TEMPLATES": "process-templates",
    "PF_RUNTIME": "runtime",
    "PF_CACHE": "cache",
}


@dataclass(frozen=True)
class _CatalogWorkplaceReader:
    documents: YamlDocumentReader

    def manifest(self, metadata: ProjectMetadataReader) -> Path | None:
        local = metadata.flow_root() / "process-forge.local.yaml"
        if local.is_file():
            # Preserve the existing local manifest text lookup, including its
            # precedence over auto discovery even when no manifest is declared.
            text = local.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"(?m)^\s*manifest:\s*(.+?)\s*$", text)
            if match is None:
                return None
            path = Path(match.group(1).strip().strip('"').strip("'"))
            return path if path.is_absolute() else (local.parent / path).resolve()
        manifest = metadata.flow_root() / "process-forge.yaml"
        if manifest.is_file():
            data = metadata.manifest()
            workplace = data.get("workplace") if isinstance(data, dict) else None
            if isinstance(workplace, dict) and workplace.get("reference") == "auto":
                candidate = metadata.project_root / "workplace.yaml"
                return candidate if candidate.is_file() else None
        return None

    def registry_path(self, manifest: Path) -> Path:
        data = self.documents.load(manifest)
        registries = data.get("registries") if isinstance(data.get("registries"), dict) else {}
        raw = str(registries.get("process_packs") or "registries/process-packs.yaml")
        constants = dict(_DEFAULT_PATH_CONSTANTS)
        declared = data.get("path_constants")
        if isinstance(declared, dict):
            for key, value in declared.items():
                if isinstance(key, str):
                    constants[key] = "" if value is None else str(value)
        constants["_WORKPLACE_ROOT"] = manifest.parent.as_posix()
        visiting: list[str] = []

        def expand(name: str) -> str:
            if name in visiting or name not in constants:
                return "${" + name + "}"
            value = str(constants.get(name, ""))
            if value == "":
                return ""
            visiting.append(name)
            result = _PATH_CONSTANT.sub(lambda match: expand(match.group(1)), value)
            visiting.pop()
            return result

        # Registry resolution historically uses the expanded path even when
        # expansion diagnostics exist. Do not introduce a new refusal here.
        for _ in range(20):
            if not _PATH_CONSTANT.search(raw):
                break
            before = raw
            raw = _PATH_CONSTANT.sub(lambda match: expand(match.group(1)), raw)
            if raw == before:
                break
        raw = raw.replace("\\", "/")
        if ContextContractInputs(self.documents).path_string_is_absolute(raw):
            return Path(raw)
        return (manifest.parent / raw).resolve()

    def active_pack_ids(self, manifest: Path | None) -> frozenset[str]:
        if manifest is None or not manifest.is_file():
            return frozenset()
        registry = self.documents.load(self.registry_path(manifest))
        entries = service._as_list(registry.get("process_packs"))
        active: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status") or "active")
            if entry.get("id") and status in {"active", "enabled", "configured"}:
                active.add(str(entry["id"]))
        return frozenset(active)


@dataclass(frozen=True)
class ProcessCatalogReadService:
    project_root: Path
    distribution_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[3], kw_only=True,
    )
    workplace_manifest: Path | None = field(default=None, kw_only=True)
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml), kw_only=True,
    )

    def context(self) -> ProcessCatalogContext:
        root = self.project_root.expanduser().resolve()
        metadata = ProjectMetadataReader(root, self.documents)
        workplace = _CatalogWorkplaceReader(self.documents)
        manifest = self.workplace_manifest
        if manifest is None:
            manifest = workplace.manifest(metadata)
        return ProcessCatalogContext(
            project_root=root,
            flow_root=metadata.flow_root(),
            distribution_root=self.distribution_root.resolve(),
            active_official_pack_ids=workplace.active_pack_ids(manifest),
        )

    def entries(
        self, *, strict: bool = False, include_available_official: bool = False,
    ) -> list[ProcessDefinitionRef]:
        return service.process_catalog_entries(
            self.context(), strict=strict,
            include_available_official=include_available_official,
        )

    def resolve_definition(
        self, process_or_path: str, *, include_available_official: bool = False,
    ) -> ProcessDefinitionRef:
        return service.resolve_process_definition(
            self.context(), process_or_path,
            include_available_official=include_available_official,
        )
