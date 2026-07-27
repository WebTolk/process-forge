#!/usr/bin/env python3
"""Check knowledge hub imports learning bundles."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import init_project, load_yaml, run_pf, write_candidate


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-hub-import-") as raw:
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
        index = load_yaml(hub / "candidates" / "index.yaml")
        if index["candidates"][0]["id"] != "kc-docs-example-rule":
            raise AssertionError("hub candidate index not updated")
    print("PASS: knowledge hub import smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
