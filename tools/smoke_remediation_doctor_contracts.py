#!/usr/bin/env python3
"""Regression smoke for authoritative, observational PF-AUD-006 doctors."""

from __future__ import annotations

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


def require_success(*args: str) -> None:
    result = run(*args)
    assert result.returncode == 0, result.stdout + result.stderr


def require_failure(*args: str) -> None:
    result = run(*args)
    assert result.returncode != 0, (
        f"doctor accepted invalid state: {' '.join(args)}\n"
        + "stdout:" + "\n" + result.stdout
        + "stderr:" + "\n" + result.stderr
    )


def write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def bytes_if_exists(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-remediation-doctors-") as tmp:
        root = Path(tmp)
        workplace = root / "workplace"
        project = root / "project"
        require_success("workplace-init", "--workplace", str(workplace), "--apply")
        require_success(
            "project-init",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--type",
            "generic",
            "--apply",
        )

        # Missing mandatory registry must block the workplace doctor.
        process_packs = workplace / "registries" / "process-packs.yaml"
        process_packs.rename(process_packs.with_suffix(".missing"))
        require_failure("doctor-workplace", "--root", str(workplace))
        process_packs.with_suffix(".missing").rename(process_packs)

        require_success(
            "knowledge-package-create",
            "--workplace",
            str(workplace),
            "--id",
            "docs.audit",
            "--title",
            "Audit Docs",
            "--package-root",
            "global",
            "--apply",
        )
        workplace_events = workplace / "runtime" / "events" / "events.ndjson"
        events_before = bytes_if_exists(workplace_events)
        require_success(
            "knowledge-package-doctor",
            "--workplace",
            str(workplace),
            "--package",
            "docs.audit",
            "--package-root",
            "global",
        )
        assert bytes_if_exists(workplace_events) == events_before
        package_manifest = workplace / "packages" / "docs.audit" / "package.yaml"
        package_manifest.write_text("id: [unterminated\n", encoding="utf-8")
        require_failure(
            "knowledge-package-doctor",
            "--workplace",
            str(workplace),
            "--package",
            "docs.audit",
            "--package-root",
            "global",
        )

        require_success(
            "template-create",
            "--workplace",
            str(workplace),
            "--id",
            "report.audit",
            "--title",
            "Audit Report",
            "--apply",
        )
        template_registry = yaml.safe_load(
            (workplace / "registries" / "templates.yaml").read_text(encoding="utf-8")
        )
        template_entry = next(
            item
            for item in template_registry["templates"]
            if item["id"] == "report.audit"
        )
        template_manifest = workplace / template_entry["path"]
        template = yaml.safe_load(template_manifest.read_text(encoding="utf-8"))
        template.pop("files")
        write_yaml(template_manifest, template)
        require_failure(
            "template-doctor",
            "--workplace",
            str(workplace),
            "--template",
            "report.audit",
        )

        require_success(
            "platform-create",
            "--workplace",
            str(workplace),
            "--id",
            "audit",
            "--title",
            "Audit Platform",
            "--apply",
        )
        platform_manifest = (
            workplace
            / "platform-contracts"
            / "platform.audit"
            / "platform-contract.yaml"
        )
        contract = yaml.safe_load(platform_manifest.read_text(encoding="utf-8"))
        contract.pop("type")
        write_yaml(platform_manifest, contract)
        require_failure(
            "platform-contract-doctor",
            "--workplace",
            str(workplace),
            "--platform",
            "audit",
        )

        require_success(
            "specialization-create",
            "--workplace",
            str(workplace),
            "--id",
            "audit",
            "--apply",
        )
        events_before = bytes_if_exists(workplace_events)
        require_success(
            "specialization-doctor",
            "--workplace",
            str(workplace),
            "--id",
            "audit",
        )
        assert bytes_if_exists(workplace_events) == events_before
        specialization_manifest = workplace / "specializations" / "specialization.audit.yaml"
        specialization = yaml.safe_load(
            specialization_manifest.read_text(encoding="utf-8")
        )
        specialization.pop("scope")
        specialization["workflow"] = []
        write_yaml(specialization_manifest, specialization)
        require_failure(
            "specialization-doctor",
            "--workplace",
            str(workplace),
            "--id",
            "audit",
        )

        require_success(
            "process-create",
            "--project-root",
            str(project),
            "--id",
            "audit-process",
            "--title",
            "Audit Process",
            "--apply",
        )
        project_events = project / ".pf" / "runtime" / "events" / "events.ndjson"
        events_before = bytes_if_exists(project_events)
        require_success(
            "process-doctor",
            "--project-root",
            str(project),
            "--process",
            "audit-process",
        )
        assert bytes_if_exists(project_events) == events_before
        process_manifest = project / "processes" / "user" / "audit-process.yaml"
        process = yaml.safe_load(process_manifest.read_text(encoding="utf-8"))
        process.pop("stages")
        write_yaml(process_manifest, process)
        require_failure(
            "process-doctor",
            "--project-root",
            str(project),
            "--process",
            "audit-process",
        )

        project_manifest = project / ".pf" / "process-forge.yaml"
        project_manifest.write_text("project: [unterminated\n", encoding="utf-8")
        require_failure("doctor-project", "--project-root", str(project))

        workplace_manifest = workplace / "workplace.yaml"
        workplace_manifest.write_text("registries: [unterminated\n", encoding="utf-8")
        require_failure("doctor-workplace", "--root", str(workplace))

    print("PASS: doctor contract regression smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
