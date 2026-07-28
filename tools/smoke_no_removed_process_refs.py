#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = ["docs", "examples", "packages", "templates", "schemas", "processes", "prompts", ".pf/process-forge.yaml"]
ALLOW = {"docs/concepts/process-directory-layout.md", "docs/ru/concepts/process-directory-layout.md", "tools/smoke_no_removed_process_refs.py"}


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
        rel_path = path.relative_to(ROOT).as_posix()
        if rel_path in ALLOW:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "process-template-install" in text:
            offenders.append(rel_path)
    assert not offenders, "\n".join(offenders)
    print("PASS: no removed process refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
