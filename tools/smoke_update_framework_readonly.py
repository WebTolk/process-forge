#!/usr/bin/env python3
"""Smoke checks for read-only ProcessForge update framework surfaces."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "pf.py"


def run_pf(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"pf {' '.join(args)} failed with {result.returncode}\nstdout follows\n{result.stdout}\nstderr follows\n{result.stderr}"
        )
    return result.stdout


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-smoke-") as tmp:
        workplace = Path(tmp) / "workplace"
        run_pf("workplace-init", "--workplace", str(workplace), "--apply")

        write(
            workplace / "registries" / "update-sources.yaml",
            """
schema_version: 1
product: processforge
updated_at: "2026-07-20T00:00:00Z"
defaults:
  channel: stable
  cache_ttl_seconds: 3600
  require_https: true
  require_sha256_for_download: true
  require_sha256_for_install: true
  require_signature_for_install: false
sources:
  - id: official
    name: Official catalog
    enabled: true
    provider: processforge_json
    priority: 10
    url: "https://updates.example.com/processforge/catalog.json"
    channels: [stable]
    subjects:
      - type: processforge_distribution
        ids: [processforge]
""",
        )
        write(
            workplace / "packages" / "docs.example" / "package.yaml",
            """
schema_version: 1
id: docs-example
name: Example docs
version: "1.1.0"
kind: documentation
scope: global
update_sites:
  - id: official
    enabled: true
    type: processforge_json
    priority: 10
    url: "https://updates.example.com/processforge/entities/docs-example.json"
    channels: [stable]
resources:
  - id: api-docs
    kind: local_mirror
    title: API docs
    load_policy: on_demand
    update_policy:
      cadence: manual
      update_sites:
        - id: upstream
          enabled: true
          type: processforge_json
          url: "https://updates.example.com/processforge/resources/api-docs.json"
""",
        )
        normalized = workplace / "runtime" / "update" / "fixtures" / "manifest.json"
        write(
            normalized,
            json.dumps(
                {
                    "schema_version": 1,
                    "product": {"id": "processforge"},
                    "generated_at": "2026-07-20T00:00:00Z",
                    "subjects": [
                        {
                            "type": "knowledge_package",
                            "id": "docs-example",
                            "versions": [
                                {
                                    "version": "1.2.0",
                                    "channels": ["stable"],
                                    "stability": "stable",
                                    "prerelease": False,
                                    "yanked": False,
                                    "source": {"id": "knowledge_package:docs-example:official", "provider": "processforge_json"},
                                    "artifacts": [
                                        {
                                            "type": "full",
                                            "format": "zip",
                                            "url": "https://updates.example.com/processforge/docs-example-1.2.0.zip",
                                            "sha256": "0" * 64,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            ),
        )

        installed_subjects = workplace / "registries" / "installed-subjects.yaml"
        before = sha256(installed_subjects)
        validate_out = run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace))
        list_out = run_pf("update", "bootstrap-source", "list", "--workplace", str(workplace))
        rebuild_out = run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace))
        entity_out = run_pf("update", "entity-sources", "list", "--workplace", str(workplace), "--subject-type", "knowledge_package")
        manifest_out = run_pf("update", "manifest", "validate", "--file", str(normalized))
        after = sha256(installed_subjects)
        if before != after:
            raise AssertionError("entity-sources rebuild modified installed-subjects.yaml")
        if "PASS:" not in validate_out:
            raise AssertionError(validate_out)
        if "official" not in list_out:
            raise AssertionError(list_out)
        if "SITES: 2" not in rebuild_out:
            raise AssertionError(rebuild_out)
        if "knowledge_package:docs-example:official" not in entity_out:
            raise AssertionError(entity_out)
        if "valid normalized update manifest" not in manifest_out:
            raise AssertionError(manifest_out)

    print("PASS: update framework read-only smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
