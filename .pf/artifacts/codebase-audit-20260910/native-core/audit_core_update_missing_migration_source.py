#!/usr/bin/env python3
"""Reproduce an archive migration source that passes plan validation but is absent."""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from processforge_core.core_update import (  # noqa: E402
    CORE_MANIFEST_NAME,
    apply_update,
    build_plan,
    make_core_manifest,
    manifest_bytes,
)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-audit-migration-") as raw:
        root = Path(raw)
        core = root / "core"
        core.mkdir()
        workplace = root / "workplace"
        (workplace / "registries").mkdir(parents=True)
        (workplace / "workplace.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        migration = """schema_version: 1
kind: processforge.workplace_migration
id: broken-source
from_versions: []
allow_unmanaged_installed_core: true
to_version: 2.0.0
operations:
  - id: missing-driver
    type: copy_if_missing
    source: templates/missing.yaml
    target: runtime-drivers/missing.yaml
"""
        manifest = make_core_manifest(version="2.0.0", source={"fixture": True}, files=[])
        archive = root / "release.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("updates/migrations/broken.yaml", migration)
            package.writestr(CORE_MANIFEST_NAME, manifest_bytes(manifest))

        plan = build_plan(core, archive, workplace_root=workplace)
        print("PLAN_STATUS", plan["status"])
        print("MIGRATION_STATUS", plan["workplace_migration"]["status"])
        try:
            apply_update(core, archive, confirm=True, workplace_root=workplace)
        except BaseException as exc:  # capture the contract failure exactly
            print("APPLY_EXCEPTION", type(exc).__name__, repr(exc))
        print("IN_PROGRESS_EXISTS", (core / "runtime" / "core-update" / "in-progress.json").is_file())
        progress = core / "runtime" / "core-update" / "in-progress.json"
        if progress.is_file():
            print("IN_PROGRESS_STATUS", json.loads(progress.read_text(encoding="utf-8"))["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
