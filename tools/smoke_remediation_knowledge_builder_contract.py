#!/usr/bin/env python3
"""Regression smoke for the knowledge hub package schema contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from evolve_smoke_helpers import init_project, run_pf, write_candidate
from processforge import load_yaml_document, validate_update_instance_against_schema


ROOT = Path(__file__).resolve().parents[1]
PF = ROOT / "bin" / "pf.py"


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pf-remediation-knowledge-builder-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        hub = base / "knowledge-hub"
        init_project(project, workplace)
        candidate = write_candidate(
            project
            / ".pf"
            / "artifacts"
            / "evolve"
            / "knowledge-candidates"
            / "kc-docs-example-rule.yaml"
        )
        run_pf(
            "evolve-candidate-create",
            "--project-root",
            str(project),
            "--workplace",
            str(workplace),
            "--from-file",
            str(candidate),
        )
        bundle = workplace / "learning" / "bundles" / "learning-export-smoke.zip"
        run_pf(
            "evolve-candidate-export",
            "--workplace",
            str(workplace),
            "--target",
            "docs.example",
            "--output",
            str(bundle),
        )
        run_pf("knowledge-hub-init", "--hub", str(hub), "--apply")
        run_pf(
            "knowledge-hub-import",
            "--hub",
            str(hub),
            "--bundle",
            str(bundle),
            "--apply",
        )
        run_pf(
            "knowledge-package-build-from-candidates",
            "--hub",
            str(hub),
            "--package",
            "docs.example",
            "--version",
            "1.1.0",
            "--apply",
        )

        package_path = hub / "packages" / "docs.example" / "package.yaml"
        package = load_yaml_document(package_path)
        schema = json.loads(
            (ROOT / "schemas" / "package-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        schema_errors = validate_update_instance_against_schema(
            package,
            schema,
            schema,
            "$",
        )
        if schema_errors:
            failures.append("built package is schema-invalid: " + "; ".join(schema_errors))
        if package.get("kind") != "mixed":
            failures.append(f"built package kind is not mixed: {package.get('kind')!r}")

        invalid_text = package_path.read_text(encoding="utf-8").replace(
            "kind: mixed",
            "kind: knowledge_package",
        )
        package_path.write_text(invalid_text, encoding="utf-8")
        invalid_bytes = package_path.read_bytes()
        output = hub / "release-output" / "docs.example-1.1.0.zip"
        update_manifest = hub / "updates" / "docs.example.update.json"
        update_index = hub / "updates" / "processforge-update-index.yaml"
        result = subprocess.run(
            [
                sys.executable,
                str(PF),
                "knowledge-package-release",
                "--hub",
                str(hub),
                "--package",
                "docs.example",
                "--version",
                "1.1.0",
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            failures.append("release accepted a schema-invalid package manifest")
        if output.exists() or output.parent.exists():
            failures.append("invalid release created ZIP output state")
        if update_manifest.exists() or update_index.exists():
            failures.append("invalid release created update metadata")
        if package_path.read_bytes() != invalid_bytes:
            failures.append("invalid release mutated package.yaml")

    if failures:
        raise AssertionError("\n".join(failures))
    print("PASS: knowledge builder/release schema contract smoke completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
