#!/usr/bin/env python3
"""Check the evolve sanitizer scans new targeting fields."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import candidate_data, init_project, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-evolve-targeting-sanitize-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        local_path = "D:" + "\\" + "private" + "\\" + "workspace"
        local_file = local_path + "\\" + "evidence.md"
        secret_assignment = "password" + "=" + "supersecretvalue"

        candidate = candidate_data("kc-targeting-private-fields")
        candidate["source_context"]["package_context"]["package_id"] = local_path + "\\" + "package"
        candidate["target"]["target_path"] = local_path + "\\" + "target.md"
        candidate["applicability"]["conditions"] = ["Observed in " + local_path]
        candidate["statement"]["details"] = "token=supersecretvalue"
        candidate["evidence"] = {"files": [local_file]}
        candidate["suggested_change"]["proposed_text"] = secret_assignment
        path = project / "private.yaml"
        write_yaml(path, candidate)

        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(path), expect=1)
        run_pf("evolve-candidate-sanitize", "--file", str(path))
        sanitized = path.with_name("private.sanitized.yaml")
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(sanitized))

    print("PASS: evolve targeting privacy sanitizer smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
