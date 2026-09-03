#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from processforge import release_test_commands


def labels(root: Path) -> set[str]:
    return {command.label for command in release_test_commands(root, clean_first=True, public=True)}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-release-test-source-") as raw:
        source_root = Path(raw)
        (source_root / ".git").mkdir()
        assert "release package" in labels(source_root)

    with tempfile.TemporaryDirectory(prefix="pf-release-test-extracted-") as raw:
        extracted_root = Path(raw)
        extracted_labels = labels(extracted_root)
        assert "clean release artifacts" in extracted_labels
        assert "release package" not in extracted_labels

    print("PASS: extracted release-test skips source-only release packaging")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
