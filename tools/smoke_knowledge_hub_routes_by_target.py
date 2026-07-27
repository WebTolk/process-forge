#!/usr/bin/env python3
"""Check hub export/import/build routes candidates by destination target."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from evolve_smoke_helpers import candidate_data, init_project, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-hub-target-routing-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        hub = base / "hub"
        init_project(project, workplace)

        child = candidate_data("kc-route-child")
        child["target"]["id"] = "docs.example-child"
        child["routing"]["recommended_destination"]["id"] = "docs.example-child"
        child_path = project / "child.yaml"
        write_yaml(child_path, child)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(child_path))

        sibling = candidate_data("kc-route-sibling")
        sibling["target"]["id"] = "docs.example-sibling"
        sibling["routing"]["recommended_destination"]["id"] = "docs.example-sibling"
        sibling_path = project / "sibling.yaml"
        write_yaml(sibling_path, sibling)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(sibling_path))

        bundle = base / "child-export.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example-child", "--output", str(bundle))
        with zipfile.ZipFile(bundle) as archive:
            names = [name for name in archive.namelist() if name.startswith("candidates/") and name.endswith(".yaml")]
        if names != ["candidates/kc-route-child.yaml"]:
            raise AssertionError(f"unexpected exported candidates: {names}")

        run_pf("knowledge-hub-init", "--hub", str(hub), "--apply")
        run_pf("knowledge-hub-import", "--hub", str(hub), "--bundle", str(bundle), "--apply")
        run_pf("knowledge-package-build-from-candidates", "--hub", str(hub), "--package", "docs.example-child", "--version", "1.1.0", "--apply")
        notes = (hub / "packages" / "docs.example-child" / "resources" / "candidate-notes.md").read_text(encoding="utf-8")
        if "kc-route-child" not in notes or "kc-route-sibling" in notes:
            raise AssertionError(notes)

    print("PASS: knowledge hub routes by target smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
