"""Public support and encoding policies: existing algorithms owned by Core."""

from __future__ import annotations

import fnmatch
from pathlib import Path
import re
from typing import Any

from processforge_core.common.checks import Check, check
from processforge_core.common.paths import rel
from processforge_core.common.policies import policy_entries
from processforge_core.common.values import as_list
from processforge_core.work.context_documents import ContextContractInputs

RUSSIAN_MOJIBAKE_MARKERS = ("Рџ", "РЎ", "РЋ", "Р€", "вЂ", "Гђ", "Г‘")


class PublicSourcePolicy:
    def __init__(self, distribution_root: Path, inputs: ContextContractInputs) -> None:
        self._distribution_root = distribution_root
        self._inputs = inputs

    def core_hardcode_violations(self, root: Path) -> list[str]:
        policy = self._inputs.documents.policy("core-hardcode-policy.yaml", root, distribution_root=self._distribution_root)
        patterns = policy_entries(policy, "forbidden_core_patterns")
        if not patterns:
            return []
        targets = policy.get("targets")
        target_patterns = [str(item) for item in targets] if isinstance(targets, list) else ["tools/processforge.py"]
        allowed_patterns = [str(item) for item in policy.get("allowed_paths", [])] if isinstance(policy.get("allowed_paths"), list) else []
        target_paths: list[Path] = []
        for target in target_patterns:
            matches = [path for path in root.glob(target) if path.is_file()] if any(char in target for char in "*?[]") else [root / target]
            target_paths.extend(path for path in matches if path.is_file())
        violations: list[str] = []
        for path in sorted(set(target_paths), key=lambda item: item.as_posix()):
            target = rel(path, root)
            if any(fnmatch.fnmatch(target, pattern) for pattern in allowed_patterns):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for entry in patterns:
                entry_targets = [str(item) for item in entry.get("targets", [])] if isinstance(entry.get("targets"), list) else []
                if entry_targets and not any(fnmatch.fnmatch(target, pattern) for pattern in entry_targets):
                    continue
                entry_allowed = [str(item) for item in entry.get("allowed_paths", [])] if isinstance(entry.get("allowed_paths"), list) else []
                if any(fnmatch.fnmatch(target, pattern) for pattern in entry_allowed):
                    continue
                raw_pattern = entry.get("pattern") or entry.get("id")
                if not raw_pattern:
                    continue
                flags = re.IGNORECASE if bool(entry.get("case_insensitive", False)) else 0
                try:
                    matched = re.search(str(raw_pattern), text, flags)
                except re.error:
                    matched = str(raw_pattern) in text
                if matched:
                    violations.append(f"{target}: {entry.get('id', raw_pattern)}")
        return violations

    def public_support_policy_violations(self, archive_path: str, text: str, policy: dict[str, Any]) -> list[str]:
        violations: list[str] = []
        group = archive_path.split("/", 1)[0]
        for entry in policy_entries(policy, "blocked_public_surface_patterns"):
            groups = [str(item) for item in as_list(entry.get("groups")) if item]
            if groups and group not in groups:
                continue
            allowed_paths = [str(item) for item in as_list(entry.get("allowed_paths")) if item]
            if any(fnmatch.fnmatch(archive_path, pattern) for pattern in allowed_paths):
                continue
            raw_pattern = entry.get("pattern") or entry.get("id")
            if not raw_pattern:
                continue
            flags = re.IGNORECASE if entry.get("case_insensitive", True) else 0
            try:
                matched = re.search(str(raw_pattern), text, flags)
            except re.error:
                matched = str(raw_pattern).lower() in text.lower() if flags else str(raw_pattern) in text
            if matched:
                violations.append(str(entry.get("message", entry.get("id", raw_pattern))))
        return violations

    def russian_documentation_files(self, root: Path) -> list[Path]:
        files = [root / "README.ru.md", root / "QUICKSTART.ru.md"]
        ru_root = root / "docs" / "ru"
        if ru_root.is_dir():
            files.extend(path for path in ru_root.rglob("*.md") if path.is_file())
        return sorted({path for path in files if path.is_file()}, key=lambda path: rel(path, root))

    def russian_mojibake_checks(self, root: Path) -> list[Check]:
        checks: list[Check] = []
        failures: list[str] = []
        for path in self.russian_documentation_files(root):
            text = path.read_text(encoding="utf-8", errors="replace")
            markers = [marker for marker in RUSSIAN_MOJIBAKE_MARKERS if marker in text]
            if markers:
                failures.append(f"{rel(path, root)} markers={','.join(markers)}")
        if failures:
            checks.extend(check("FAIL", f"Russian documentation mojibake: {item}") for item in failures)
        else:
            checks.append(check("PASS", "Russian documentation has no known mojibake markers"))
        return checks
