"""Existing session report, recent file and legacy context freshness reads."""

from __future__ import annotations

import re
from pathlib import Path

from ..common.paths import rel
from ..common.text import COLON_WS
from .context_sources import ProjectContextSourcesReader
from .metadata import ProjectMetadataReader


class ProjectSessionReadService:
    def report_status(self, path: Path) -> str:
        if not path.is_file():
            return "missing"
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"(?m)^status" + COLON_WS + r"([a-z_]+)\s*$", text)
        return match.group(1) if match else "missing"

    def recent_files(self, root: Path, dirname: str, limit: int = 5, *, rel_root: Path | None = None) -> list[str]:
        directory = root / dirname
        if not directory.is_dir():
            return []
        files = sorted((path for path in directory.rglob("*") if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
        return [rel(path, rel_root or root) for path in files[:limit]]

    def legacy_freshness(self, project_root: Path) -> tuple[str, list[str]]:
        index_path = ProjectMetadataReader(project_root).flow_root() / "contexts" / "context-index.yaml"
        if not index_path.is_file():
            return "missing", []
        text = index_path.read_text(encoding="utf-8", errors="replace")
        current_sources = ProjectContextSourcesReader(project_root).read()
        stale: list[str] = []
        for item in current_sources:
            path = str(item["path"])
            fingerprint = str(item.get("fingerprint", "missing"))
            if path not in text or fingerprint not in text:
                stale.append(path)
        return ("fresh" if not stale else "stale"), stale
