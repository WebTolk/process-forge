"""Shared Markdown list rendering with the existing empty-value contract."""

from __future__ import annotations


def markdown_list(items: list[str], empty: str = "None.") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)
