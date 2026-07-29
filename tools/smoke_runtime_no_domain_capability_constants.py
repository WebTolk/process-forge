#!/usr/bin/env python3
"""Smoke runtime has no built-in user capability provider constants."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES = [
    ROOT / "tools" / "processforge.py",
    ROOT / "bin" / "pf.py",
]
FILES.extend((ROOT / "schemas").glob("*.json"))
FILES.extend((ROOT / "templates").glob("*.yaml"))
FILES.extend((ROOT / "templates" / "registries").glob("*.yaml"))

FORBIDDEN_EXACT = [
    "BUILTIN_CAPABILITIES",
    "BUILTIN_SEED_CAPABILITIES",
    '"provider": "builtin"',
    "provider: builtin",
]

FORBIDDEN_CAPABILITY_WORDS = [
    "php",
    "html",
    "css",
    "javascript",
    "seo",
    "content_planning",
    "writing",
    "research",
    "review",
    "xdebug",
    "screaming-frog",
    "joomla",
    "laravel",
]


def capability_declaration(line: str) -> bool:
    return bool(re.search(r"\b(capability|capabilities|provides_capabilities|required_capabilities)\b\s*[:=]", line))


def main() -> None:
    failures: list[str] = []
    for path in FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_EXACT:
            if marker in text:
                failures.append(f"{path.relative_to(ROOT)} contains {marker}")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not capability_declaration(line):
                continue
            lower = line.lower()
            for word in FORBIDDEN_CAPABILITY_WORDS:
                if re.search(rf"(?<![a-z0-9_.-]){re.escape(word)}(?![a-z0-9_.-])", lower):
                    failures.append(f"{path.relative_to(ROOT)}:{lineno} hardcodes domain capability word {word}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("PASS: smoke_runtime_no_domain_capability_constants")


if __name__ == "__main__":
    main()
