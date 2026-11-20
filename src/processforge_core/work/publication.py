"""Existing atomic Work text and YAML publication through explicit dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..maintenance.temporary_disposal import atomic_staging


@dataclass(frozen=True, kw_only=True)
class WorkDocumentPublisher:
    text_writer: Callable[[], Callable[[Path, str], None]] = field(repr=False, compare=False)
    yaml_formatter: Callable[[], Callable[[dict[str, Any]], str]] = field(repr=False, compare=False)

    def write_yaml(self, path: Path, value: dict[str, Any]) -> None:
        self.text_writer()(path, self.yaml_formatter()(value).rstrip() + "\n")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with atomic_staging(path) as temporary:
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(path)
