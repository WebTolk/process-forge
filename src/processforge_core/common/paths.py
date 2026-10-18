from __future__ import annotations

import fnmatch
from pathlib import Path


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def path_matches_pattern(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name
    return fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern)
