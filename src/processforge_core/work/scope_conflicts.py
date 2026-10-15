"""Operation-local write-scope comparisons with the existing conflict contract."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import fnmatch
import os
from pathlib import Path
import re

from .context_documents import ContextContractInputs


@dataclass
class ScopeConflictService:
    """Own one lazy file inventory for a single validation, plan or tick."""

    project_root: Path
    inputs: ContextContractInputs = field(default_factory=ContextContractInputs)
    _keys: dict[str, str] = field(default_factory=dict, init=False)
    _pairs: dict[tuple[str, str], tuple[bool, str]] = field(default_factory=dict, init=False)
    _files: list[str] | None = field(default=None, init=False)

    def _key(self, value: str) -> str:
        if value not in self._keys:
            text = self.inputs.normalize_assignment_path(value)
            self._keys[value] = text.lower() if os.name == "nt" else text
        return self._keys[value]

    def _repo_files(self) -> list[str]:
        if self._files is None:
            files: list[str] = []
            skipped = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
            for path in self.project_root.rglob("*"):
                if any(part in skipped for part in path.parts):
                    continue
                if path.is_file():
                    files.append(self._key(path.relative_to(self.project_root).as_posix()))
            self._files = files
        return self._files

    def overlap(self, left: str, right: str) -> tuple[bool, str]:
        left_key, right_key = self._key(left), self._key(right)
        pair = (left_key, right_key)
        if pair not in self._pairs:
            self._pairs[pair] = self._overlap(left_key, right_key)
        return self._pairs[pair]

    def _overlap(self, left: str, right: str) -> tuple[bool, str]:
        left_glob = any(char in left for char in "*?[")
        right_glob = any(char in right for char in "*?[")
        if not left_glob and not right_glob:
            return left == right, "same_file"
        if left_glob and not right_glob:
            return fnmatch.fnmatch(right, left), "glob_matches_file"
        if right_glob and not left_glob:
            return fnmatch.fnmatch(left, right), "file_matches_glob"
        if left == right:
            return True, "same_glob"
        left_prefix = re.split(r"[*?\[]", left, maxsplit=1)[0]
        right_prefix = re.split(r"[*?\[]", right, maxsplit=1)[0]
        comparable = left_prefix.startswith(right_prefix) or right_prefix.startswith(left_prefix)
        # Every fnmatch match starts with its literal prefix, even when a later
        # bracket expression is malformed. Incomparable nonempty prefixes
        # cannot share a file or satisfy the conservative prefix fallback.
        if left_prefix and right_prefix and not comparable:
            return False, ""
        if any(fnmatch.fnmatch(item, left) and fnmatch.fnmatch(item, right) for item in self._repo_files()):
            return True, "glob_matches_same_file"
        if left_prefix and right_prefix and comparable:
            return True, "possible_glob_overlap"
        return False, ""

    def conflicts(
        self,
        current_id: str,
        current_scope: Sequence[str],
        other_id: str,
        other_scope: Sequence[str],
        *,
        reason_prefix: str = "",
    ) -> list[dict[str, str]]:
        conflicts: list[dict[str, str]] = []
        for current_item in current_scope:
            for other_item in other_scope:
                overlaps, reason = self.overlap(current_item, other_item)
                if overlaps:
                    conflicts.append({
                        "current_assignment": current_id,
                        "current_scope": current_item,
                        "other_assignment": other_id,
                        "other_scope": other_item,
                        "reason": reason_prefix + reason,
                    })
        return conflicts
