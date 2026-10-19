"""Shared text formatting with existing newline and check hint semantics."""

from __future__ import annotations

from .checks import Check, check


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def check_with_hint(level: str, message: str, why: str, fix: str, alternative: str | None = None) -> Check:
    details = [message, "", "Why:", f"  {why}", "", "Fix:"]
    details.extend(f"  {line}" if line else "" for line in fix.splitlines())
    if alternative:
        details.extend(["", "Or:"])
        details.extend(f"  {line}" if line else "" for line in alternative.splitlines())
    return check(level, "\n".join(details))
