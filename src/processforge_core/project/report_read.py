"""Existing Markdown report projections through concrete Core readers."""

from __future__ import annotations

from pathlib import Path
import re

from ..common.ids import safe_id
from ..common.paths import rel
from .metadata import ProjectMetadataReader


class ReportProjectionReader:
    def section_items(self, path: Path, marker: str) -> list[str]:
        if not path.is_file():
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker not in text:
            return []
        section = text.split(marker, 1)[1].split("\n## ", 1)[0]
        items: list[str] = []
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and stripped != "- None.":
                items.append(stripped[2:].strip())
        return items

    def section_has_items(self, path: Path, marker: str) -> bool:
        return bool(self.section_items(path, marker))

    def has_missing_required_capabilities(self, path: Path) -> bool:
        return self.section_has_items(path, "## Missing Required Capabilities")

    def waiver_help(self) -> str:
        return """create .pf/artifacts/capability-waivers.yaml with explicit evidence, for example:
schema_version: 1
capability_waivers:
  - capability: filesystem.read
    status: active
    reason: runtime access verified; registry provider declaration is pending
    evidence: .pf/artifacts/delivery-report.md"""

    def resource_status(self, project_root: Path, kind: str, resource_id: str) -> tuple[str, str]:
        report = ProjectMetadataReader(project_root).flow_root() / "reviews" / "parity" / "resources" / f"{safe_id(kind + '-' + resource_id, 'resource')}.md"
        if not report.is_file():
            return "SKIP", ""
        text = report.read_text(encoding="utf-8", errors="replace")
        match = re.search("Result:" + r"\s+`(PASS|WARN|SKIP|FAIL)`", text)
        return (match.group(1) if match else "WARN"), rel(report, project_root)
