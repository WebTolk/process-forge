from __future__ import annotations

from typing import Any

from processforge_core.common.paths import path_matches_pattern


class ProjectClassifierRulePolicy:
    """Match classifier rules against the available project paths."""

    def matches(self, rule: dict[str, Any], available_paths: set[str]) -> bool:
        when = rule.get("when")
        if not isinstance(when, dict):
            return False
        all_conditions = when.get("all")
        any_conditions = when.get("any")
        if isinstance(all_conditions, list):
            return bool(all_conditions) and all(
                isinstance(item, dict) and self._condition_matches(item, available_paths)
                for item in all_conditions
            )
        if isinstance(any_conditions, list):
            return any(
                isinstance(item, dict) and self._condition_matches(item, available_paths)
                for item in any_conditions
            )
        return False

    def _condition_matches(self, condition: dict[str, Any], available_paths: set[str]) -> bool:
        exists = condition.get("exists")
        if not isinstance(exists, str) or not exists.strip():
            return False
        pattern = exists.strip().replace("\\", "/")
        return any(path_matches_pattern(path, pattern) for path in available_paths)
