"""Canonical resource bucket primitives with the original ordering and coercions."""

from __future__ import annotations

from typing import Any

from ..common.values import list_value

RESOURCE_GROUP_KEYS = ("knowledge_packages", "tools", "mcp", "templates")
RESOURCE_BUCKET_KEYS = ("requires", "recommends", "optional", "excludes")


def default_resource_buckets() -> dict[str, dict[str, list[str]]]:
    return {bucket: {key: [] for key in RESOURCE_GROUP_KEYS} for bucket in RESOURCE_BUCKET_KEYS}


def resource_bucket(data: dict[str, Any] | None, bucket: str, key: str) -> list[str]:
    if not isinstance(data, dict):
        return []
    bucket_data = data.get(bucket) if isinstance(data.get(bucket), dict) else {}
    return list_value(bucket_data.get(key)) if isinstance(bucket_data, dict) else []


def merge_resource_buckets(target: dict[str, dict[str, list[str]]], resources: dict[str, Any] | None) -> None:
    for bucket in RESOURCE_BUCKET_KEYS:
        for key in RESOURCE_GROUP_KEYS:
            values = resource_bucket(resources, bucket, key)
            if values:
                target[bucket][key].extend(values)


def dedupe_sorted(values: list[str]) -> list[str]:
    return sorted({str(item) for item in values if str(item)})
