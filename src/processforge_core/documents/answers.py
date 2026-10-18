"""Strict reads of existing answers and capability registry documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..common.privacy import SECRET_VALUE_PATTERNS
from ..common.yaml_io import _parse_simple_yaml


class AnswersDocumentReader:
    """Read the strict answers mapping without retaining document state."""

    def read(self, path: Path | None) -> dict[str, Any]:
        if path is None:
            return {}
        if not path.is_file():
            raise SystemExit(f"FAIL: answers file not found: {path}")
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS):
            raise SystemExit("FAIL: answers file appears to contain a secret value")
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        except ModuleNotFoundError:
            return _parse_simple_yaml(text)

    def strings(self, value: Any) -> list[str]:
        strings: list[str] = []
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, list):
            for item in value:
                strings.extend(self.strings(item))
        elif isinstance(value, dict):
            for item in value.values():
                strings.extend(self.strings(item))
        return strings
