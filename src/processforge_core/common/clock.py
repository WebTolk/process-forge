"""Shared UTC timestamp primitive."""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
