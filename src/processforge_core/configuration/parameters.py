"""Parameter merging with ordered provenance."""

from __future__ import annotations

import copy
from typing import Any


class ParameterMergePolicy:
    """Merge parameter maps without retaining per-merge state."""

    def merge_maps(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
        source_id: str,
        path: str = "",
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        provenance = provenance if provenance is not None else {}
        result = copy.deepcopy(base)
        for key, value in override.items():
            key_text = str(key)
            key_path = self._path(path, key_text)
            if value is None:
                if key_text in result:
                    del result[key_text]
                    provenance[key_path] = {"source": source_id, "action": "delete"}
                continue
            if key_text in result:
                result[key_text] = self._merge_value(result[key_text], value, source_id, key_path, provenance)
            else:
                result[key_text] = copy.deepcopy(value)
                provenance[key_path] = {"source": source_id, "action": "add"}
        return result

    def _path(self, base: str, key: str) -> str:
        return f"{base}.{key}" if base else key

    def _list_item_path(self, base: str, item_id: str) -> str:
        return f"{base}[id={item_id}]" if base else f"[id={item_id}]"

    def _list_merges_by_id(self, base: Any, override: Any) -> bool:
        if not isinstance(base, list) or not isinstance(override, list):
            return False
        if not base or not override:
            return False
        combined = [*base, *override]
        return all(isinstance(item, dict) and item.get("id") not in (None, "") for item in combined)

    def _merge_value(
        self,
        base: Any,
        override: Any,
        source_id: str,
        path: str,
        provenance: dict[str, Any],
    ) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            return self.merge_maps(base, override, source_id, path, provenance)
        if self._list_merges_by_id(base, override):
            result = [copy.deepcopy(item) for item in base]
            index = {str(item["id"]): idx for idx, item in enumerate(result) if isinstance(item, dict) and item.get("id") not in (None, "")}
            for item in override:
                item_id = str(item["id"])
                item_path = self._list_item_path(path, item_id)
                if item.get("__delete__") is True or item.get("_delete") is True:
                    if item_id in index:
                        del result[index[item_id]]
                        provenance[item_path] = {"source": source_id, "action": "delete"}
                        index = {str(value["id"]): idx for idx, value in enumerate(result) if isinstance(value, dict) and value.get("id") not in (None, "")}
                    continue
                if item_id in index:
                    result[index[item_id]] = self.merge_maps(result[index[item_id]], item, source_id, item_path, provenance)
                else:
                    result.append(copy.deepcopy(item))
                    provenance[item_path] = {"source": source_id, "action": "add"}
            return result
        provenance[path or "<root>"] = {"source": source_id, "action": "replace"}
        return copy.deepcopy(override)
