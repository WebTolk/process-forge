"""Existing atomic authoring journal storage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import uuid

from ..common.text import ensure_trailing_newline
from ..common.yaml_dump import dump_yaml
from .inputs import AuthoringInputService
from .plans import AuthoringPlan


class AuthoringJournalStore:
    def write_data(self, path: Path, journal: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(ensure_trailing_newline(dump_yaml(journal)), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def write(self, plan: AuthoringPlan, journal: dict[str, Any]) -> None:
        self.write_data(AuthoringInputService().journal_path(plan), journal)
