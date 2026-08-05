#!/usr/bin/env python3
"""Helpers for deterministic local update-system smoke tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run_pf(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=str(cwd or ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_ok(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode != 0:
        raise AssertionError(result.stdout)
    return result.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_yaml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_package_zip(artifact: Path, *, subject_id: str, subject_type: str, version: str, body: str = "updated") -> str:
    artifact.parent.mkdir(parents=True, exist_ok=True)
    manifest = f"""id: {subject_id}
type: {subject_type}
version: {version}
content: {body}
"""
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("package.yaml", manifest)
        archive.writestr("README.md", f"{subject_id} {version}\n")
    return sha256(artifact)


def make_update_fixture(workplace: Path, *, subject_id: str = "acme.software-processes", subject_type: str = "process_package", tool: bool = False) -> dict[str, Path | str]:
    packages = workplace / "packages" / subject_id
    packages.mkdir(parents=True, exist_ok=True)
    if tool:
        tool_path = workplace / "tools" / "local-linter.py"
        write_yaml(tool_path, "print('old tool')")
        registry = workplace / "registries" / "tools.yaml"
        write_yaml(
            registry,
            f"""
schema_version: 1
tools:
  - id: {subject_id}
    type: tool_definition
    version: 1.0.0
    update_policy:
      mode: replace_file
      executable_paths:
        - tools/local-linter.py
    update_sites:
      - id: tool-main
        enabled: true
        manifest_url: file:///{(workplace / 'updates' / 'manifest.json').as_posix()}
        changelog_url: file:///{(workplace / 'updates' / 'CHANGELOG.md').as_posix()}
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
          notify_director_inbox: true
          mode: replace_file
          executable_paths:
            - tools/local-linter.py
""",
        )
        artifact = workplace / "updates" / "local-linter-1.1.0.py"
        write_yaml(artifact, "print('new tool')")
        subject_type = "tool_definition"
    else:
        write_yaml(
            packages / "package.yaml",
            f"""
id: {subject_id}
type: {subject_type}
version: 1.0.0
update_sites:
  - id: acme-main
    enabled: true
    manifest_url: file:///{(workplace / 'updates' / 'manifest.json').as_posix()}
    changelog_url: file:///{(workplace / 'updates' / 'CHANGELOG.md').as_posix()}
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
      notify_director_inbox: true
      allow_stage: true
      allow_apply: true
      backup_before_apply: true
      install_path: packages/{subject_id}
""",
        )
        artifact = workplace / "updates" / f"{subject_id}-1.1.0.zip"
        make_package_zip(artifact, subject_id=subject_id, subject_type=subject_type, version="1.1.0")
    write_yaml(
        workplace / "registries" / "installed-subjects.yaml",
        f"""
schema_version: 1
subjects:
  - id: {subject_id}
    type: {subject_type}
    scope: global
    version: 1.0.0
    install_path: {'tools/local-linter.py' if tool else f'packages/{subject_id}'}
    update_policy:
      mode: {'replace_file' if tool else 'manual'}
      executable_paths:
        - tools/local-linter.py
""",
    )
    changelog = workplace / "updates" / "CHANGELOG.md"
    write_yaml(changelog, "# Changelog\n\n- 1.1.0 local deterministic update.")
    manifest = {
        "schema_version": 1,
        "kind": "processforge.update_manifest",
        "subject": {"id": subject_id, "type": subject_type, "name": subject_id},
        "channels": {
            "stable": {
                "latest": "1.1.0",
                "versions": [
                    {
                        "version": "1.1.0",
                        "released_at": "2026-07-27T10:00:00Z",
                        "download_url": f"file:///{artifact.as_posix()}",
                        "sha256": sha256(artifact),
                        "changelog_url": f"file:///{changelog.as_posix()}",
                        "breaking": False,
                        "migration_required": False,
                        "update_policy": {"mode": "replace_file", "executable_paths": ["tools/local-linter.py"]} if tool else {"install_path": f"packages/{subject_id}"},
                    }
                ],
            }
        },
    }
    write_json(workplace / "updates" / "manifest.json", manifest)
    return {"artifact": artifact, "manifest": workplace / "updates" / "manifest.json", "changelog": changelog, "subject_id": subject_id, "subject_type": subject_type}


def first_candidate_id(workplace: Path) -> str:
    data = json.loads((workplace / "runtime" / "update" / "candidates.json").read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])
    if not candidates:
        raise AssertionError("no update candidates")
    return str(candidates[0]["id"])
