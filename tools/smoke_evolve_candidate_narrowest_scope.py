#!/usr/bin/env python3
"""Check child observations stay narrow unless generalization is explicit."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import candidate_data, init_project, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-evolve-narrowest-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)

        child = candidate_data("kc-child-narrow-observation")
        child["source_context"]["platform_stack"] = ["platform.example-parent", "platform.example-child"]
        child["target"]["id"] = "docs.example-child"
        child["routing"]["recommended_destination"]["id"] = "docs.example-child"
        child["applicability"]["scope"] = "platform"
        child["applicability"]["applies_to"]["platforms"] = ["platform.example-child"]
        child_path = project / "child.yaml"
        write_yaml(child_path, child)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(child_path))

        unsafe_parent = candidate_data("kc-parent-without-generalization")
        unsafe_parent["target"]["id"] = "docs.example-parent"
        unsafe_parent["routing"]["recommended_destination"]["id"] = "docs.example-parent"
        unsafe_parent["applicability"]["scope"] = "parent_platform"
        unsafe_parent["generalization"]["level"] = "narrow_observation"
        unsafe_path = project / "unsafe-parent.yaml"
        write_yaml(unsafe_path, unsafe_parent)
        result = run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(unsafe_path), expect=1)
        if "generalization" not in result.stdout:
            raise AssertionError(result.stdout)

    print("PASS: evolve candidate narrowest scope smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
