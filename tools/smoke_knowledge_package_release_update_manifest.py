#!/usr/bin/env python3
"""Check package release writes update manifest."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from evolve_smoke_helpers import init_project, run_pf, write_candidate


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-package-release-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        hub = base / "knowledge-hub"
        init_project(project, workplace)
        candidate = write_candidate(project / ".pf" / "artifacts" / "evolve" / "knowledge-candidates" / "kc-docs-example-rule.yaml")
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(candidate))
        bundle = workplace / "learning" / "bundles" / "learning-export-smoke.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example", "--output", str(bundle))
        run_pf("knowledge-hub-init", "--hub", str(hub), "--apply")
        run_pf("knowledge-hub-import", "--hub", str(hub), "--bundle", str(bundle), "--apply")
        run_pf("knowledge-package-build-from-candidates", "--hub", str(hub), "--package", "docs.example", "--version", "1.1.0", "--apply")
        output = hub / "packages" / "docs.example" / "releases" / "1.1.0" / "docs.example-1.1.0.zip"
        run_pf("knowledge-package-release", "--hub", str(hub), "--package", "docs.example", "--version", "1.1.0", "--output", str(output))
        manifest = json.loads((hub / "updates" / "docs.example.update.json").read_text(encoding="utf-8"))
        assert manifest["subject"]["id"] == "docs.example"
        assert manifest["channels"]["stable"]["latest"] == "1.1.0"
        assert output.is_file()
        assert (hub / "updates" / "processforge-update-index.yaml").is_file()
    print("PASS: knowledge package release update manifest smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
