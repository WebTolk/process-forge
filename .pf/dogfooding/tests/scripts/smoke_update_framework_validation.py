#!/usr/bin/env python3
"""Regression smoke checks for update framework validation failures."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("PF_REPO_ROOT", Path(__file__).resolve().parents[4])).resolve()
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from processforge_subprocess import diagnostic_text, run_command as run_processforge_command

CLI = ROOT / "bin" / "pf.py"
VALID_SHA256 = "0" * 64
PF_TIMEOUT_SECONDS = 30


def run_pf(*args: str, expect_success: bool) -> str:
    command_label = "pf " + " ".join(args)
    print(f"RUN: {command_label}", flush=True)
    result = run_processforge_command([sys.executable, str(CLI), *args], cwd=ROOT, timeout=PF_TIMEOUT_SECONDS)
    if result.timed_out:
        raise AssertionError(diagnostic_text(result))
    if expect_success and result.returncode != 0:
        raise AssertionError(diagnostic_text(result))
    if not expect_success and result.returncode == 0:
        raise AssertionError(
            f"pf {' '.join(args)} unexpectedly passed\nstdout follows\n{result.stdout}\nstderr follows\n{result.stderr}"
        )
    return result.stdout + result.stderr


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def valid_manifest() -> dict[str, object]:
    return {
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
                                "sha256": VALID_SHA256,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def registry_yaml(source_body: str) -> str:
    return f"""
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
{source_body.rstrip()}
"""


def valid_source_body() -> str:
    return """
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
"""


def assert_fails(label: str, output: str) -> None:
    if "FAIL:" not in output:
        raise AssertionError(f"{label} did not print a FAIL line\n{output}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-validation-smoke-") as tmp:
        tmp_root = Path(tmp)
        workplace = tmp_root / "workplace"
        run_pf("workplace-init", "--workplace", str(workplace), "--apply", expect_success=True)

        valid_manifest_path = tmp_root / "valid-manifest.json"
        write_json(valid_manifest_path, valid_manifest())
        run_pf("update", "manifest", "validate", "--file", str(valid_manifest_path), expect_success=True)

        incomplete = valid_manifest()
        incomplete["subjects"][0]["versions"] = [{"artifacts": [{"type": "full", "format": "zip", "url": "https://updates.example.com/package.zip", "sha256": VALID_SHA256}]}]
        incomplete_path = tmp_root / "incomplete-manifest.json"
        write_json(incomplete_path, incomplete)
        assert_fails("incomplete normalized manifest", run_pf("update", "manifest", "validate", "--file", str(incomplete_path), expect_success=False))

        bad_sha = copy.deepcopy(valid_manifest())
        bad_sha["subjects"][0]["versions"][0]["artifacts"][0]["sha256"] = "not-a-sha"
        bad_sha_path = tmp_root / "bad-sha-manifest.json"
        write_json(bad_sha_path, bad_sha)
        assert_fails("bad artifact sha256", run_pf("update", "manifest", "validate", "--file", str(bad_sha_path), expect_success=False))

        http_artifact = copy.deepcopy(valid_manifest())
        http_artifact["subjects"][0]["versions"][0]["artifacts"][0]["url"] = "http://updates.example.com/package.zip"
        http_artifact_path = tmp_root / "http-artifact-manifest.json"
        write_json(http_artifact_path, http_artifact)
        assert_fails("http artifact URL", run_pf("update", "manifest", "validate", "--file", str(http_artifact_path), expect_success=False))

        trusted_http_artifact = copy.deepcopy(http_artifact)
        trusted_http_artifact["subjects"][0]["versions"][0]["artifacts"][0]["trust"] = {"require_https": False}
        trusted_http_artifact_path = tmp_root / "trusted-http-artifact-manifest.json"
        write_json(trusted_http_artifact_path, trusted_http_artifact)
        run_pf("update", "manifest", "validate", "--file", str(trusted_http_artifact_path), expect_success=True)

        registry_path = workplace / "registries" / "update-sources.yaml"
        write_text(registry_path, registry_yaml(valid_source_body()))
        run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace), expect_success=True)

        write_text(registry_path, registry_yaml(valid_source_body().replace('url: "https://updates.example.com/processforge/catalog.json"', 'url: "https:/bad"')))
        assert_fails("malformed source URL", run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace), expect_success=False))

        write_text(registry_path, registry_yaml(valid_source_body().replace("    priority: 10\n", "")))
        assert_fails("missing source priority", run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace), expect_success=False))

        raw_header_source = (
            valid_source_body()
            + """
    headers_env:
      Authorization: "Bearer raw-token"
"""
        )
        write_text(registry_path, registry_yaml(raw_header_source))
        assert_fails("raw-looking headers_env value", run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace), expect_success=False))

        trusted_http_source = valid_source_body().replace('url: "https://updates.example.com/processforge/catalog.json"', 'url: "http://localhost:8080/catalog.json"')
        trusted_http_source += """
    trust:
      require_https: false
"""
        write_text(registry_path, registry_yaml(trusted_http_source))
        run_pf("update", "bootstrap-source", "validate", "--workplace", str(workplace), expect_success=True)

        write_text(registry_path, registry_yaml(valid_source_body()))

        overrides_path = workplace / "registries" / "update-site-overrides.yaml"
        write_text(
            overrides_path,
            """
schema_version: 1
updated_at: "2026-07-20T00:00:00Z"
overrides:
  - site_id: "knowledge_package:docs-example:official"
    preserved_local:
      headers_env:
        Authorization: "Bearer raw-token"
""",
        )
        assert_fails("raw-looking override header value", run_pf("update", "entity-sources", "rebuild", "--workplace", str(workplace), expect_success=False))

    print("PASS: update framework validation regression smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
