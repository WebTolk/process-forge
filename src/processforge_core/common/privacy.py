"""Shared privacy patterns and predicates for public content."""
from __future__ import annotations

import json
import re
from typing import Any


BACKSLASH = chr(92)

LOCAL_PATH_PATTERNS = [
    re.compile(r"(?<![A-Za-z])[A-Za-z]:" + re.escape(BACKSLASH)),
    re.compile(r"(?<![A-Za-z])[A-Za-z]:/"),
    re.compile("/" + "home" + "/[A-Za-z0-9_.-]+/"),
    re.compile("/" + "Users" + "/[A-Za-z0-9_.-]+/"),
    re.compile("/" + "srv" + "/"),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


def is_public_path_safe(text: str) -> bool:
    return not any(pattern.search(text) for pattern in LOCAL_PATH_PATTERNS)


def contains_secret_value(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS)


def public_yaml_has_private_path(data: dict[str, Any]) -> bool:
    return not is_public_path_safe(json.dumps(data, ensure_ascii=False))
