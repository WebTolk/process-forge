#!/usr/bin/env python3
"""Check sanitized candidate export bundle."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from evolve_smoke_helpers import init_project, run_pf, write_candidate


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-candidate-export-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        candidate = write_candidate(project / ".pf" / "artifacts" / "evolve" / "knowledge-candidates" / "kc-docs-example-rule.yaml")
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(candidate))
        bundle = workplace / "learning" / "bundles" / "learning-export-smoke.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example", "--output", str(bundle))
        with zipfile.ZipFile(bundle) as archive:
            names = set(archive.namelist())
        required = {"manifest.yaml", "candidates/kc-docs-example-rule.yaml", "evidence/evidence-digest.md"}
        if required - names:
            raise AssertionError("export bundle missing: " + ", ".join(sorted(required - names)))
    print("PASS: evolve candidate export smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
