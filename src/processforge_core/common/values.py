from __future__ import annotations

from typing import Any


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def list_value(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                output.append(item)
            elif isinstance(item, dict):
                item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
                if item_id:
                    output.append(str(item_id))
        return output
    return []


def parameter_payload(data: dict[str, Any]) -> dict[str, Any]:
    parameters = data.get("parameters") if isinstance(data, dict) else {}
    return parameters if isinstance(parameters, dict) else {}


def registry_ids(data: dict[str, Any], collection_key: str) -> set[str]:
    entries = data.get(collection_key) if isinstance(data, dict) else None
    ids: set[str] = set()
    if not isinstance(entries, list):
        return ids
    for entry in entries:
        if isinstance(entry, dict):
            for key in ["id", "package_id", "capability"]:
                value = entry.get(key)
                if value:
                    ids.add(str(value))
    return ids
