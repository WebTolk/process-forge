#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = [".pf/process-forge.yaml", "docs", "examples", "packages", "packs", "templates", "schemas", "processes", "prompts"]
PROCESS_REF = re.compile(
    r"(?:\.\./)?(?:(?:examples/domain-packs|packs/official)/[a-z0-9][a-z0-9_-]*/)?processes/[a-z0-9][a-z0-9_-]*\.yaml"
)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for item in ACTIVE_ROOTS:
        path = ROOT / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*") if child.is_file() and child.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt"}))
    return files


def main() -> int:
    offenders: list[str] = []
    for path in iter_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in PROCESS_REF.finditer(text):
            value = match.group(0)
            normalized = value.removeprefix("../")
            if normalized.startswith(("processes/core/", "processes/user/", "processes/custom/")):
                continue
            if normalized.startswith(("examples/domain-packs/", "packs/official/")):
                continue
            offenders.append(f"{path.relative_to(ROOT).as_posix()}: {value}")
    assert not offenders, "\n".join(offenders[:40])
    print("PASS: PF project process refs follow core/user/custom/official layout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
