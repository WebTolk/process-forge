#!/usr/bin/env python3
"""Regression for canonical-only platform authoring and legacy-state rejection."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def fingerprint(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "authoring-transactions" not in path.parts
    }


def init_workplace(path: Path) -> None:
    result = run("workplace-init", "--workplace", str(path), "--apply")
    assert result.returncode == 0, result.stdout


def legacy_contract(platform_id: str, title: str) -> dict:
    return {
        "schema_version": 1,
        "id": f"platform.{platform_id}",
        "title": title,
        "type": "platform_contract",
        "version": "1.0.0",
        "applies_to": {"platforms": [platform_id]},
        "requires": {"capabilities": ["filesystem.read"], "knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "includes": {"knowledge_packages": [], "tools": [], "mcp": [], "templates": []},
        "policies": {"missing_required_capability": "block", "missing_optional_resource": "warn"},
    }


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pf-platform-migration-") as raw:
        root = Path(raw)
        workplace = root / "workplace"
        init_workplace(workplace)
        install = run(
            "platform-contract-install",
            "--workplace",
            str(workplace),
            "--id",
            "example-canonical",
            "--apply",
        )
        canonical = workplace / "platform-contracts" / "platform.example-canonical" / "platform-contract.yaml"
        legacy_install = workplace / "platforms" / "example-canonical" / "platform.yaml"
        if install.returncode != 0 or not canonical.is_file() or legacy_install.exists():
            failures.append("platform-contract-install did not use canonical layout")

        legacy = workplace / "platforms" / "example-legacy" / "platform.yaml"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(yaml.safe_dump(legacy_contract("example-legacy", "Legacy"), sort_keys=False), encoding="utf-8")
        registry_path = workplace / "registries" / "platforms.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        registry["platforms"].append(
            {
                "id": "example-legacy",
                "name": "Legacy",
                "package_id": "platform.example-legacy",
                "path": "platforms/example-legacy/platform.yaml",
                "status": "available",
            }
        )
        registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
        before = fingerprint(workplace)
        rejected = run(
            "platform-contract-install",
            "--workplace",
            str(workplace),
            "--id",
            "example-legacy",
            "--apply",
        )
        if (
            rejected.returncode == 0
            or "unsupported legacy" not in (rejected.stdout + rejected.stderr).lower()
            or fingerprint(workplace) != before
        ):
            failures.append("legacy-only platform state was not rejected without mutation")

        conflict_legacy = workplace / "platforms" / "example-conflict" / "platform.yaml"
        conflict_canonical = workplace / "platform-contracts" / "platform.example-conflict" / "platform-contract.yaml"
        conflict_legacy.parent.mkdir(parents=True)
        conflict_canonical.parent.mkdir(parents=True)
        conflict_legacy.write_text(yaml.safe_dump(legacy_contract("example-conflict", "Legacy Conflict"), sort_keys=False), encoding="utf-8")
        conflict_canonical.write_text(yaml.safe_dump(legacy_contract("example-conflict", "Canonical Conflict"), sort_keys=False), encoding="utf-8")
        before = fingerprint(workplace)
        conflict = run(
            "platform-contract-install",
            "--workplace",
            str(workplace),
            "--id",
            "example-conflict",
            "--apply",
        )
        if (
            conflict.returncode == 0
            or "unsupported legacy" not in (conflict.stdout + conflict.stderr).lower()
            or fingerprint(workplace) != before
        ):
            failures.append("dual legacy/canonical state did not fail without mutation")
    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1
    print("PASS: canonical-only platform layout and legacy rejection smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
