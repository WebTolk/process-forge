"""Existing atomic Work text and YAML publication through explicit dependencies."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, kw_only=True)
class WorkDocumentPublisher:
    text_writer: Callable[[], Callable[[Path, str], None]] = field(repr=False, compare=False)
    yaml_formatter: Callable[[], Callable[[dict[str, Any]], str]] = field(repr=False, compare=False)

    def write_yaml(self, path: Path, value: dict[str, Any]) -> None:
        self.text_writer()(path, self.yaml_formatter()(value).rstrip() + "\n")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
