from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..common.paths import path_matches_pattern, rel
from ..common.values import list_value


class ProjectDetectionService:
    """Evaluate platform detection rules against current project files."""

    def files(self, project_root: Path) -> list[Path]:
        if not project_root.exists():
            return []
        ignored_dirs = {".git", ".idea", ".serena", "__pycache__", "runtime", "cache"}
        files: list[Path] = []
        for path in project_root.rglob("*"):
            if any(part in ignored_dirs for part in path.relative_to(project_root).parts):
                continue
            if path.is_file():
                files.append(path)
        return sorted(files, key=lambda item: item.relative_to(project_root).as_posix())

    def group_matches(self, values: Any, available: set[str], *, all_required: bool) -> bool:
        patterns = list_value(values)
        if not patterns:
            return False
        checks = [any(path_matches_pattern(item, pattern) for item in available) for pattern in patterns]
        return all(checks) if all_required else any(checks)

    def matches(self, contract: dict[str, Any], project_root: Path) -> bool:
        detection = contract.get("detection") if isinstance(contract.get("detection"), dict) else {}
        if not detection:
            return False
        files = self.files(project_root)
        rel_files = {rel(path, project_root) for path in files}
        directories = {
            item.as_posix()
            for path in files
            for item in [path.relative_to(project_root).parent]
            if item.as_posix() != "."
        }
        directories.update(path.name for path in project_root.iterdir() if path.is_dir() and path.name not in {".git", ".idea", ".serena"})
        dir_rules = detection.get("directories") if isinstance(detection.get("directories"), dict) else {}
        file_rules = detection.get("files") if isinstance(detection.get("files"), dict) else {}
        matched = False
        if self.group_matches(dir_rules.get("any"), directories, all_required=False):
            matched = True
        if self.group_matches(dir_rules.get("all"), directories, all_required=True):
            matched = True
        if self.group_matches(file_rules.get("any"), rel_files, all_required=False):
            matched = True
        if self.group_matches(file_rules.get("all"), rel_files, all_required=True):
            matched = True
        contains_rules = detection.get("file_contains") if isinstance(detection.get("file_contains"), list) else []
        for rule in contains_rules:
            if not isinstance(rule, dict) or not rule.get("pattern"):
                continue
            candidate_patterns = list_value(rule.get("files")) or ["*"]
            candidate_files = [path for path in files if any(path_matches_pattern(rel(path, project_root), pattern) for pattern in candidate_patterns)]
            for path in candidate_files[:200]:
                text = path.read_text(encoding="utf-8", errors="ignore")[:200000]
                try:
                    if re.search(str(rule["pattern"]), text):
                        matched = True
                        break
                except re.error:
                    if str(rule["pattern"]) in text:
                        matched = True
                        break
            if matched:
                break
        return matched
