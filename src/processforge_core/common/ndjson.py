from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NdjsonReader:
    """Read live NDJSON rows with the existing line and parse-error contract."""

    def read(self, path: Path) -> list[tuple[int, Any, str | None]]:
        rows: list[tuple[int, Any, str | None]] = []
        if not path.is_file():
            return rows
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append((line_number, json.loads(line), None))
            except json.JSONDecodeError as exc:
                rows.append((line_number, None, str(exc)))
        return rows
