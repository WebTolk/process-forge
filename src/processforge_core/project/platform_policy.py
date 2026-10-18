"""Pure projections of platform contract references and requirements."""
from __future__ import annotations

from typing import Any

from ..common.values import list_value
from .platforms import PlatformContractReader


class PlatformContractPolicy:
    """Project contract data using the canonical platform catalog identity."""

    def __init__(self, catalog: PlatformContractReader):
        self.catalog = catalog

    def normalize_ref(self, value: Any, *, default_required: bool = True) -> dict[str, Any] | None:
        if isinstance(value, str):
            ref_id = value.strip()
            if not ref_id:
                return None
            return {"id": self.catalog.contract_id(ref_id), "required": default_required}
        if isinstance(value, dict):
            raw_id = value.get("id") or value.get("platform") or value.get("package_id")
            if not raw_id:
                return None
            record: dict[str, Any] = {"id": self.catalog.contract_id(str(raw_id)), "required": bool(value.get("required", default_required))}
            if value.get("version"):
                record["version"] = str(value["version"])
            return record
        return None

    def refs(self, value: Any, *, default_required: bool = True) -> list[dict[str, Any]]:
        values = value if isinstance(value, list) else ([value] if value else [])
        refs: list[dict[str, Any]] = []
        for item in values:
            ref = self.normalize_ref(item, default_required=default_required)
            if ref:
                refs.append(ref)
        return refs

    def extends(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        return self.refs(contract.get("extends"), default_required=True)

    def required_platforms(self, contract: dict[str, Any]) -> list[dict[str, Any]]:
        requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
        return self.refs(requires.get("platforms"), default_required=True)

    def required_capabilities(self, contract: dict[str, Any]) -> list[str]:
        requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
        return sorted(set(list_value(contract.get("capabilities"))).union(list_value(requires.get("capabilities"))))

    def required_items(self, contract: dict[str, Any], key: str) -> list[str]:
        requires = contract.get("requires", {}) if isinstance(contract.get("requires"), dict) else {}
        includes = contract.get("includes", {}) if isinstance(contract.get("includes"), dict) else {}
        required = set(list_value(requires.get(key)))
        for item in includes.get(key, []) if isinstance(includes.get(key), list) else []:
            if isinstance(item, dict) and item.get("required") is True:
                item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
                if item_id:
                    required.add(str(item_id))
        return sorted(required)

    def includes(self, contract: dict[str, Any], key: str) -> list[str]:
        includes = contract.get("includes", {}) if isinstance(contract.get("includes"), dict) else {}
        output: list[str] = []
        value = includes.get(key)
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    output.append(item)
                elif isinstance(item, dict) and item.get("required") is not True:
                    item_id = item.get("id") or item.get("package") or item.get("template") or item.get("capability")
                    if item_id:
                        output.append(str(item_id))
        return sorted(set(output))

    def recommended_items(self, contract: dict[str, Any], key: str) -> list[str]:
        recommends = contract.get("recommends") if isinstance(contract.get("recommends"), dict) else {}
        values = list_value(recommends.get(key))
        values.extend(self.includes(contract, key))
        return sorted(set(values))

    def optional_items(self, contract: dict[str, Any], key: str) -> list[str]:
        optional = contract.get("optional") if isinstance(contract.get("optional"), dict) else {}
        return sorted(set(list_value(optional.get(key))))
