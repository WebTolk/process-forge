"""Live reads of existing update candidate documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .documents import UpdateDocumentReader
from .update import now_utc


class UpdateCandidateReader:
    def __init__(self, distribution_root: Path) -> None:
        self.documents = UpdateDocumentReader(distribution_root)

    def read(self, workplace_root: Path) -> dict[str, Any]:
        path = self.documents.candidates_path(workplace_root)
        if not path.is_file():
            return {"schema_version": 1, "generated_at": now_utc(), "channel": "stable", "candidates": [], "conflicts": []}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"schema_version": 1, "generated_at": now_utc(), "channel": "stable", "candidates": [], "conflicts": []}
        return data if isinstance(data, dict) else {"schema_version": 1, "generated_at": now_utc(), "channel": "stable", "candidates": [], "conflicts": []}

    def find(self, workplace_root: Path, candidate_id: str) -> dict[str, Any] | None:
        data = self.read(workplace_root)
        for item in data.get("candidates", []) if isinstance(data.get("candidates"), list) else []:
            if isinstance(item, dict) and item.get("id") == candidate_id:
                return item
        return None
