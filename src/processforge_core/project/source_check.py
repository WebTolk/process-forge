"""Existing recorded/live source comparison, without context policy or writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .snapshot_sources import ProjectSnapshotSourcesReader


@dataclass(frozen=True)
class ProjectSnapshotSourceCheckService:
    """Compare live fingerprints with portable official-pack line endings."""

    project_root: Path
    distribution_root: Path = field(
        default_factory=lambda: Path(__file__).parents[3], kw_only=True
    )
    sources: ProjectSnapshotSourcesReader | None = field(
        default=None, kw_only=True, repr=False, compare=False
    )

    def compare(self, snapshot: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        recorded_sources = {}
        sources = (
            snapshot.get("sources", {})
            if isinstance(snapshot.get("sources"), dict)
            else {}
        )
        fingerprints = (
            sources.get("fingerprints", []) if isinstance(sources, dict) else []
        )
        if isinstance(fingerprints, list):
            for item in fingerprints:
                if isinstance(item, dict) and "id" in item:
                    recorded_sources[str(item["id"])] = str(
                        item.get("checksum", "missing")
                    )
        reader = (
            self.sources
            if self.sources is not None
            else ProjectSnapshotSourcesReader(
                self.project_root,
                distribution_root=self.distribution_root,
            )
        )
        current_sources = reader.read()
        current_by_id = {
            str(item["id"]): str(item.get("checksum", "missing"))
            for item in current_sources
        }
        official_mismatches = {
            str(item["id"])
            for item in current_sources
            if item.get("kind") == "official-process-pack"
            and str(item["id"]) in recorded_sources
            and recorded_sources[str(item["id"])]
            != str(item.get("checksum", "missing"))
        }
        checksum_variants: dict[str, tuple[str, str, str]] | None = None
        for source_id, checksum in current_by_id.items():
            if source_id.startswith("package-"):
                continue
            if source_id not in recorded_sources:
                reasons.append(f"source added: {source_id}")
            elif recorded_sources[source_id] != checksum:
                if source_id in official_mismatches:
                    if checksum_variants is None:
                        checksum_variants = reader.official_pack_checksum_variants(
                            official_mismatches
                        )
                    variants = checksum_variants.get(source_id)
                    if (
                        variants
                        and variants[0] == checksum
                        and recorded_sources[source_id] in variants
                    ):
                        continue
                reasons.append(f"source changed: {source_id}")
        for source_id in sorted(set(recorded_sources) - set(current_by_id)):
            if source_id.startswith("package-"):
                continue
            reasons.append(f"source removed: {source_id}")
        return reasons
