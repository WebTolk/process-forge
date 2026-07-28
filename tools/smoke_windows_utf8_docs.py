#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    paths = [ROOT / "docs" / "getting-started" / "installation.md", ROOT / "docs" / "ru" / "getting-started" / "installation.md"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    for token in ["chcp 65001", "$OutputEncoding", "[Console]::OutputEncoding", "Identifiers and YAML remain ASCII-safe"]:
        assert token in text, token
    print("PASS: Windows UTF-8 docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
