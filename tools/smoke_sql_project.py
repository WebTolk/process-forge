"""Fresh SQL project fixtures through the sealed public initialization route."""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def publish_fixture(root: Path) -> Path:
    """Capture a complete isolated fixture distribution without native adoption."""
    import pf_native_control as native

    inventory = runpy.run_path(str(ROOT / "tools/validate-process-forge-checksums.py"))
    payload = {
        name: inventory["released_content"](path)
        for name, path in inventory["public_file_entries"](ROOT)
    }
    payload[native.INVENTORY] = b""
    build = native.build_publication(
        payload,
        version=(ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        source={"fixture": True},
        generated_at="fixture",
    )
    for name, content in {**build.payload, native.MANIFEST: build.manifest}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return root


def initialize_sql_project(project: Path, workplace: Path) -> None:
    """Create a physically new test flow; existing roots require real migration."""
    if (project / ".pf").exists():
        raise AssertionError("SQL fixture project already exists")
    distribution = publish_fixture(project.parent / "sql-initializer")
    result = subprocess.run(
        [
            sys.executable,
            str(distribution / "bin/pf.py"),
            "project-onboard",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic",
            "--coordination-mode",
            "simple",
            "--apply",
        ],
        cwd=distribution,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    if not (project / ".pf/data/execution-storage.json").is_file():
        raise AssertionError("fresh fixture has no SQL execution storage")
