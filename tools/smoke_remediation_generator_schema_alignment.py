#!/usr/bin/env python3
"""Regression smoke for PF-AUD-005 generator/schema postconditions."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(PF), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expected}: {' '.join(args)}\n"
            + "stdout:" + "\n" + result.stdout
            + "stderr:" + "\n" + result.stderr
        )
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_if_exists(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-remediation-generator-") as tmp:
        workplace = Path(tmp) / "workplace"
        run("workplace-init", "--workplace", str(workplace), "--apply")
        empty_selection = run(
            "release-test",
            "--root",
            str(ROOT),
            "--only",
            "public-gate",
            "--skip",
            "public-gate",
            expected=1,
        )
        assert "no runnable checks" in empty_selection.stdout
        assert "\nRUN " not in empty_selection.stdout

        template_id = "report.audit.basic"
        run(
            "template-create",
            "--workplace",
            str(workplace),
            "--id",
            template_id,
            "--title",
            "Audit Report",
            "--kind",
            "document",
            "--apply",
        )
        template_registry = yaml.safe_load(
            (workplace / "registries" / "templates.yaml").read_text(encoding="utf-8")
        )
        template_entry = next(
            item for item in template_registry["templates"] if item["id"] == template_id
        )
        template_manifest = workplace / template_entry["path"]
        template = yaml.safe_load(template_manifest.read_text(encoding="utf-8"))
        assert template["schema_version"] == 1, template
        assert template["type"] == "reusable_template", template
        workplace_events = workplace / "runtime" / "events" / "events.ndjson"
        events_before = bytes_if_exists(workplace_events)
        run("template-doctor", "--workplace", str(workplace), "--template", template_id)
        assert bytes_if_exists(workplace_events) == events_before

        run(
            "platform-create",
            "--workplace",
            str(workplace),
            "--id",
            "audit",
            "--title",
            "Audit Platform",
            "--apply",
        )
        registry_path = workplace / "registries" / "platforms.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        entry = next(item for item in registry["platforms"] if item["id"] == "audit")
        assert entry == {
            "id": "audit",
            "name": "Audit Platform",
            "package_id": "platform.audit",
            "path": "platform-contracts/platform.audit/platform-contract.yaml",
            "status": "available",
        }, entry

        snapshot = (
            workplace
            / "platform-contracts"
            / "platform.audit"
            / "artifacts"
            / "platform-stack.snapshot.yaml"
        )
        if snapshot.exists():
            snapshot.unlink()
        before_registry = sha256(registry_path)
        events_before = bytes_if_exists(workplace_events)
        run(
            "platform-contract-doctor",
            "--workplace",
            str(workplace),
            "--platform",
            "audit",
        )
        assert not snapshot.exists(), "platform doctor must not write a stack snapshot"
        assert sha256(registry_path) == before_registry, "platform doctor mutated registry"
        assert bytes_if_exists(workplace_events) == events_before

    print("PASS: generator/schema alignment regression smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
