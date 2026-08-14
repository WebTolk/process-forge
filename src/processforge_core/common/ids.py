from __future__ import annotations

import re


def safe_id(value: str, default: str = "project") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or default
