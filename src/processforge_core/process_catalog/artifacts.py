from __future__ import annotations

from typing import Any

from processforge_core.common.values import as_list, string_list






class ProcessArtifactDeclarationPolicy:
    """Collect artifact identifiers declared by a process definition."""

    def defined_ids(self, process: dict[str, Any]) -> set[str]:
        definitions = process.get("artifact_definitions")
        if isinstance(definitions, dict):
            return {str(key) for key in definitions.keys()}
        return {str(item.get("id")) for item in as_list(definitions) if isinstance(item, dict) and item.get("id")}

    def declared_ids(self, process: dict[str, Any]) -> set[str]:
        ids = self.defined_ids(process)
        for key in ["input_definitions", "external_artifacts", "virtual_artifacts", "generated_files"]:
            value = process.get(key)
            if isinstance(value, dict):
                ids.update(str(item) for item in value.keys())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get("id"):
                        ids.add(str(item["id"]))
        return ids

    def produced_ids(self, process: dict[str, Any]) -> set[str]:
        produced: set[str] = set()
        for stage in as_list(process.get("stages")):
            if isinstance(stage, dict):
                produced.update(str(item) for item in string_list(stage.get("produced_artifacts")))
        return produced
