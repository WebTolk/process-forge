#!/usr/bin/env python3
"""Run local evolve learning loop through existing update pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import copy_package_to_workplace, init_project, read_json, run_pf, write_candidate, write_installed_subject


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-evolve-e2e-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        hub = base / "knowledge-hub"
        init_project(project, workplace)
        candidate = write_candidate(project / ".pf" / "artifacts" / "evolve" / "knowledge-candidates" / "kc-docs-example-rule.yaml")
        run_pf("evolve-run", "--project-root", str(project), "--workplace", str(workplace), "--process", "process-authoring", "--run", "run-evolve-smoke", "--candidate-file", str(candidate))
        bundle = workplace / "learning" / "bundles" / "learning-export-smoke.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example", "--output", str(bundle))
        run_pf("knowledge-hub-init", "--hub", str(hub), "--apply")
        run_pf("knowledge-hub-import", "--hub", str(hub), "--bundle", str(bundle), "--apply")
        run_pf("knowledge-package-build-from-candidates", "--hub", str(hub), "--package", "docs.example", "--version", "1.1.0", "--apply")
        release = hub / "packages" / "docs.example" / "releases" / "1.1.0" / "docs.example-1.1.0.zip"
        run_pf("knowledge-package-release", "--hub", str(hub), "--package", "docs.example", "--version", "1.1.0", "--output", str(release))
        copy_package_to_workplace(hub, workplace, "docs.example")
        write_installed_subject(workplace, "docs.example", "packages/docs.example")
        run_pf("update", "candidates", "refresh", "--workplace", str(workplace))
        candidates = read_json(workplace / "runtime" / "update" / "candidates.json")["candidates"]
        if not candidates:
            raise AssertionError("update candidate discovery found no package update")
        candidate_id = candidates[0]["id"]
        run_pf("update", "stage", "--workplace", str(workplace), "--candidate", candidate_id)
        run_pf("update", "verify", "--workplace", str(workplace), "--candidate", candidate_id)
        run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id, "--confirm")
        installed = (workplace / "packages" / "docs.example" / "package.yaml").read_text(encoding="utf-8")
        if "version: 1.1.0" not in installed:
            raise AssertionError("updated package version was not applied")
    print("PASS: evolve learning loop end-to-end smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
