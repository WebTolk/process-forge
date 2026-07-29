#!/usr/bin/env python3
"""Smoke that familiar file names do not trigger built-in classification."""

import tempfile
from pathlib import Path

from smoke_domain_neutral_core_helpers import load_processforge


def main() -> None:
    pf = load_processforge()
    with tempfile.TemporaryDirectory(prefix="pf-no-file-guess-") as tmp:
        project = Path(tmp) / "project"
        for name in [
            "composer.json",
            "package.json",
            "pyproject.toml",
            "some.php",
            "some.py",
            "some.js",
            "phpunit.xml",
            ".github/workflows/test.yml",
        ]:
            path = project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        detected = pf.detect_project(project)
        if detected["status"] != "unclassified" or detected["project_kind"] != ["unknown"]:
            raise AssertionError(detected)
        if detected["languages"] or detected["frameworks"] or detected["platforms"]:
            raise AssertionError(detected)
    print("PASS: smoke_no_hardcoded_file_project_detection")


if __name__ == "__main__":
    main()
