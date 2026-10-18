from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


class ProcessArtifactDeclarationPolicy:
    """Collect artifact identifiers declared by a process definition."""

    def defined_ids(self, process: dict[str, Any]) -> set[str]:
        definitions = process.get("artifact_definitions")
        if isinstance(definitions, dict):
            return {str(key) for key in definitions.keys()}
        return {str(item.get("id")) for item in _as_list(definitions) if isinstance(item, dict) and item.get("id")}

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
        for stage in _as_list(process.get("stages")):
            if isinstance(stage, dict):
                produced.update(str(item) for item in _string_list(stage.get("produced_artifacts")))
        return produced
