"""Live capability provider projection from the existing project/workplace registries."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..documents.answers import AnswersDocumentReader
from .metadata import ProjectMetadataReader


@dataclass(frozen=True)
class CapabilityRegistryReader:
    project_root: Path
    answers: AnswersDocumentReader = field(
        default_factory=AnswersDocumentReader,
        kw_only=True,
        repr=False,
        compare=False,
    )

    @staticmethod
    def values(entry: object) -> list[str]:
        values: list[str] = []
        if not isinstance(entry, dict):
            return values
        for key in ("capability", "capabilities", "provides", "provides_capabilities"):
            value = entry.get(key)
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(str(item) for item in value if isinstance(item, (str, int, float)))
            elif isinstance(value, dict):
                nested = value.get("capabilities")
                if isinstance(nested, list):
                    values.extend(str(item) for item in nested if isinstance(item, (str, int, float)))
        return values

    def read(self, workplace_manifest: Path | None = None) -> dict[str, str]:
        providers: dict[str, str] = {}

        def collect(registry_root: Path, scope: str) -> None:
            for rel_path, collection_key in [
                ("registries/tools.yaml", "tools"),
                ("registries/mcp.yaml", "mcp_servers"),
            ]:
                path = registry_root / rel_path
                if not path.is_file():
                    continue
                try:
                    data = self.answers.read(path)
                except SystemExit:
                    continue
                entries = data.get(collection_key) if isinstance(data, dict) else None
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    if str(entry.get("status") or "available") in {"disabled", "missing"}:
                        continue
                    provider_id = str(entry.get("id", rel_path))
                    provider_ref = provider_id if scope == "project" else f"{scope}:{provider_id}"
                    for capability in self.values(entry):
                        providers[capability] = provider_ref

        if workplace_manifest and workplace_manifest.is_file():
            collect(workplace_manifest.parent, "workplace")
        collect(ProjectMetadataReader(self.project_root).flow_root(), "project")
        return providers
