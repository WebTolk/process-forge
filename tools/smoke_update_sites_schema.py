#!/usr/bin/env python3
"""Smoke-test unified update-site schema without provider routing."""

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
            workplace / "packages" / "minimal.pkg" / "package.yaml",
            """
id: minimal.pkg
type: process_package
version: 1.0.0
update_sites:
  - manifest_url: file:///tmp/minimal-update.json
    changelog_url: file:///tmp/minimal-changelog.md
""",
        )
        minimal = require_ok(run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), "--dry-run"))
        if "minimal" not in minimal:
            raise AssertionError(minimal)
        write_yaml(
            workplace / "packages" / "bad.pkg" / "package.yaml",
            """
id: bad.pkg
type: process_package
version: 1.0.0
update_sites:
  - id: bad
    enabled: true
    url: file:///tmp/bad-update.json
    changelog_url: file:///tmp/bad-changelog.md
""",
        )
        failed = run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), "--dry-run")
        if failed.returncode == 0 or "unsupported url field" not in failed.stdout:
            raise AssertionError(failed.stdout)
    print("PASS: unified update-site schema smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
