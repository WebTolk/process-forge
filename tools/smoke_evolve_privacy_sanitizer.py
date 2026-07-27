#!/usr/bin/env python3
"""Check evolve export blocks raw private data and sanitizer redacts it."""

from __future__ import annotations

import tempfile
from pathlib import Path

from evolve_smoke_helpers import candidate_data, init_project, load_yaml, run_pf, write_yaml


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-evolve-privacy-") as raw:
        base = Path(raw)
        project = base / "project"
        workplace = base / "workplace"
        init_project(project, workplace)
        data = candidate_data("kc-private-path")
        data["summary"] = "token=abcdefghijklmnop"
        data["evidence"] = ["D:" + chr(92) + "private" + chr(92) + "repo" + chr(92) + "file.md"]
        raw_candidate = project / ".pf" / "artifacts" / "evolve" / "knowledge-candidates" / "kc-private-path.yaml"
        write_yaml(raw_candidate, data)
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(raw_candidate), expect=1)
        run_pf("evolve-candidate-sanitize", "--file", str(raw_candidate))
        sanitized = raw_candidate.with_name("kc-private-path.sanitized.yaml")
        sanitized_data = load_yaml(sanitized)
        if "redacted" not in str(sanitized_data):
            raise AssertionError("sanitizer did not redact private data")
        run_pf("evolve-candidate-create", "--project-root", str(project), "--workplace", str(workplace), "--from-file", str(sanitized))
    print("PASS: evolve privacy sanitizer smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
