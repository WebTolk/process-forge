"""Shared policy entry projections and identifier matching."""

from __future__ import annotations

import re
from typing import Any


def policy_entries(policy: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = policy.get(key)
    if not isinstance(values, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in values:
        if isinstance(item, str):
            entries.append({"id": item})
        elif isinstance(item, dict):
            entries.append(item)
    return entries

def policy_id_matches(identifier: str, entry: dict[str, Any]) -> bool:
    if str(entry.get("id", "")) == identifier:
        return True
    pattern = entry.get("pattern")
    return bool(pattern and re.fullmatch(str(pattern), identifier))
