from __future__ import annotations

import hashlib
import re


def safe_id(value: str, default: str = "project") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or default


def opaque_identity_digest(identity: str) -> str:
    """Return a filesystem-safe key without normalizing the opaque identity."""

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
