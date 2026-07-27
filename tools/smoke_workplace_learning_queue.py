#!/usr/bin/env python3
"""Check durable workplace learning queue layout."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import init_project, load_yaml, run_pf, write_candidate


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-learning-queue-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        candidate = write_candidate(project / ".pf" / "artifacts" / "evolve" / "knowledge-candidates" / "kc-docs-example-rule.yaml")
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(candidate))
        listing = run_pf("evolve-candidate-list", "--workplace", str(workplace)).stdout
        if "kc-docs-example-rule" not in listing:
            raise AssertionError("queued candidate not listed")
        index = load_yaml(workplace / "learning" / "index.yaml")
        assert index["candidates"][0]["path"] == "inbox/kc-docs-example-rule.yaml"
    print("PASS: workplace learning queue smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
