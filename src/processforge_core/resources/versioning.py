"""Existing shared resource version algorithm."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ResourceVersionPolicy:
    """Existing numeric/lexical version rules, without state or I/O."""

    def key(self, value: str) -> tuple[int, tuple[int, ...] | str]:
        text = value.strip()
        match = re.fullmatch('v?(\\d+)(?:\\.(\\d+))?(?:\\.(\\d+))?(?:[-+][A-Za-z0-9.-]+)?', text)
        if not match:
            return (1, text)
        parts = tuple((int(part) for part in match.groups(default='0')))
        return (0, parts)

    def is_newer(self, available: str, installed: str | None) -> tuple[bool, str | None]:
        if not installed:
            return (True, None)
        available_key = self.key(available)
        installed_key = self.key(installed)
        warning = None
        if available_key[0] or installed_key[0]:
            warning = 'non-semver version compared lexically'
            return (str(available) > str(installed), warning)
        return (available_key[1] > installed_key[1], warning)
