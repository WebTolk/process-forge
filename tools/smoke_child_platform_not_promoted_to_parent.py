#!/usr/bin/env python3
"""Check child-platform observations are not curated into parent packages."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import candidate_data, init_project, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-child-parent-promotion-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        hub = base / "hub"
        init_project(project, workplace)
        run_pf("knowledge-hub-init", "--hub", str(hub), "--apply")

        child = candidate_data("kc-child-only")
        child["source_context"]["platform_stack"] = ["platform.example-parent", "platform.example-child"]
        child["target"]["id"] = "docs.example-child"
        child["routing"]["recommended_destination"]["id"] = "docs.example-child"
        child_path = project / "child.yaml"
        write_yaml(child_path, child)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(child_path))
        child_bundle = base / "child.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example-child", "--output", str(child_bundle))
        run_pf("knowledge-hub-import", "--hub", str(hub), "--bundle", str(child_bundle), "--apply")
        run_pf("knowledge-package-build-from-candidates", "--hub", str(hub), "--package", "docs.example-parent", "--version", "1.1.0", "--apply", expect=1)

        parent = candidate_data("kc-parent-proposed")
        parent["target"]["id"] = "docs.example-parent"
        parent["routing"]["recommended_destination"]["id"] = "docs.example-parent"
        parent["applicability"]["scope"] = "parent_platform"
        parent["generalization"]["level"] = "parent_platform_candidate"
        parent["promotion"] = {
            "status": "proposed",
            "target": {"type": "knowledge_package", "id": "docs.example-parent"},
            "blockers": ["Needs broader evidence."],
        }
        parent_path = project / "parent.yaml"
        write_yaml(parent_path, parent)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(parent_path))
        parent_bundle = base / "parent.zip"
        run_pf("evolve-candidate-export", "--workplace", str(workplace), "--target", "docs.example-parent", "--output", str(parent_bundle))
        run_pf("knowledge-hub-import", "--hub", str(hub), "--bundle", str(parent_bundle), "--apply")
        run_pf("knowledge-package-build-from-candidates", "--hub", str(hub), "--package", "docs.example-parent", "--version", "1.1.0", "--apply")

        notes = (hub / "packages" / "docs.example-parent" / "resources" / "candidate-notes.md").read_text(encoding="utf-8")
        incoming = (hub / "packages" / "docs.example-parent" / "resources" / "incoming-learnings.md").read_text(encoding="utf-8")
        if "kc-parent-proposed" in notes or "kc-parent-proposed" not in incoming or "Unreviewed parent-platform candidates" not in incoming:
            raise AssertionError(notes + "\n---\n" + incoming)

    print("PASS: child platform not promoted to parent smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
