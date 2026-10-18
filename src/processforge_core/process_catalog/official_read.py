"""Concrete live selection of the existing active official process packs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..common.yaml_io import _parse_simple_yaml
from ..documents.reader import YamlDocumentReader
from ..resources.snapshot import WorkspacePathReferenceReader
from ..work.context_documents import ContextContractInputs
from .service import official_pack_manifest_records

__all__ = ()


@dataclass(frozen=True)
class OfficialProcessPackReader:
    """Retain the list-only Workplace selection used by snapshot sources.

    Construction does no I/O. Catalog rules that normalize scalar entries have
    their own existing contract and are not changed by this reader.
    """
    workplace_manifest: Path | None
    distribution_root: Path = field(default_factory=lambda: Path(__file__).parents[3], kw_only=True)
    documents: YamlDocumentReader = field(
        default_factory=lambda: YamlDocumentReader(_parse_simple_yaml),
        kw_only=True, repr=False, compare=False,
    )

    def registry(self) -> dict[str, Any]:
        manifest = self.workplace_manifest
        if not manifest or not manifest.is_file():
            return {"schema_version": 1, "process_packs": []}
        paths = WorkspacePathReferenceReader(
            manifest.parent, manifest.parent, workplace_manifest=manifest,
            inputs=ContextContractInputs(documents=self.documents),
        )
        registry = paths.load_workplace_registry(manifest, "process_packs", "process-packs.yaml")
        return registry if isinstance(registry, dict) else {"schema_version": 1, "process_packs": []}

    def active_ids(self) -> set[str]:
        entries = self.registry().get("process_packs")
        active: set[str] = set()
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status") or "active")
            if entry.get("id") and status in {"active", "enabled", "configured"}:
                active.add(str(entry["id"]))
        return active

    def active_records(self) -> list[tuple[Path, dict[str, Any]]]:
        active_ids = self.active_ids()
        return [
            (path, manifest)
            for path, manifest in official_pack_manifest_records(self.distribution_root, documents=self.documents)
            if str(manifest.get("id") or "") in active_ids
        ]
