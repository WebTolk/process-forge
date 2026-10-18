"""Shared JSON document reads with native decoding and filesystem errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def json_read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
