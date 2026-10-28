"""Existing standalone YAML scalar formatting and recursive serialization."""

from __future__ import annotations

import json
from typing import Any


def format_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if any(
        ord(char) < 0x20 or 0x7F <= ord(char) <= 0x9F or char in "\u2028\u2029"
        for char in text
    ):
        # JSON escapes preserve ASCII controls, quotes and backslashes in YAML.
        # Keep non-BMP characters intact; YAML does not combine surrogate pairs.
        quoted = json.dumps(text, ensure_ascii=False)
        return "".join(
            f"\\u{ord(char):04x}"
            if 0x7F <= ord(char) <= 0x9F or char in "\u2028\u2029"
            else char
            for char in quoted
        )
    yaml_literals = {"*", "null", "true", "false", "yes", "no", "on", "off", "~"}
    special_start = ("-", "?", "&", "*", "!", "%", "@", "`", ">", "|", "'", '"', ",")
    if (
        text.lower() in yaml_literals
        or text == "..."
        or text.startswith(special_start)
        or any(char in text for char in [":", "#", "{", "}", "[", "]", "\\"])
        or text.strip() != text
    ):
        return "'" + text.replace("'", "''") + "'"
    return text


def dump_yaml(data: Any, indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(data, dict):
        if not data:
            lines.append(f"{prefix}{{}}")
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(dump_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {format_scalar(value)}")
    elif isinstance(data, list):
        if not data:
            lines.append(f"{prefix}[]")
        for item in data:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(dump_yaml(item, indent + 2))
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.append(dump_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {format_scalar(item)}")
    else:
        lines.append(f"{prefix}{format_scalar(data)}")
    return "\n".join(lines)
