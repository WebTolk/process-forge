"""Existing official-pack profile activation selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from processforge_core.common.values import as_list
from processforge_core.process_catalog.service import official_pack_manifest_records


class OfficialPackProfileReader:
    """Select profile entries using the canonical live manifest reader."""

    def __init__(self, distribution_root: Path) -> None:
        self.distribution_root = distribution_root

    def official_pack_registry_entries_for_profile(self, profile: str) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for _path, manifest in official_pack_manifest_records(self.distribution_root):
            activation = manifest.get("activation") if isinstance(manifest.get("activation"), dict) else {}
            profiles = {str(item) for item in as_list(activation.get("profiles")) if str(item)}
            if profile not in profiles:
                continue
            selected.append(
                {
                    "id": str(manifest["id"]),
                    "origin": "official",
                    "status": "active",
                    "version": str(manifest.get("version") or ""),
                }
            )
        return selected
