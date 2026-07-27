#!/usr/bin/env python3
"""Smoke-test unified update-site schema and legacy URL warnings."""

from __future__ import annotations

import tempfile
from pathlib import Path

from update_smoke_helpers import require_ok, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-sites-schema-") as raw:
        workplace = Path(raw)
        write_yaml(
            workplace / "packages" / "acme.pkg" / "package.yaml",
            """
id: acme.pkg
type: process_package
version: 1.0.0
update_sites:
  - id: main
    enabled: true
    provider: processforge_json_file
    manifest_url: file:///tmp/acme-update.json
    changelog_url: file:///tmp/acme-changelog.md
    channel: stable
    priority: 10
    trust:
      require_https: false
      require_sha256: true
      allow_unsigned: true
      signature_required: false
    policy:
      check_interval_hours: 24
      auto_check: true
      auto_stage: false
      auto_apply: false
      notify_operator: true
""",
        )
        require_ok(run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), "--dry-run"))
        write_yaml(
            workplace / "packages" / "legacy.pkg" / "package.yaml",
            """
id: legacy.pkg
type: process_package
version: 1.0.0
update_sites:
  - id: legacy
    enabled: true
    provider: processforge_json_file
    url: file:///tmp/legacy-update.json
""",
        )
        legacy = require_ok(run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), "--dry-run"))
        if "legacy" not in legacy:
            raise AssertionError(legacy)
        write_yaml(
            workplace / "packages" / "bad.pkg" / "package.yaml",
            """
id: bad.pkg
type: process_package
version: 1.0.0
update_sites:
  - id: bad
    enabled: true
    provider: processforge_json
""",
        )
        failed = run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), "--dry-run")
        if failed.returncode == 0 or "requires manifest_url" not in failed.stdout:
            raise AssertionError(failed.stdout)
    print("PASS: unified update-site schema smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
