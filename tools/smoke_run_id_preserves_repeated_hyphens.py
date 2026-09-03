#!/usr/bin/env python3
"""Smoke test that run readers preserve generated collision-suffixed ids."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from processforge import load_run, run_root


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-run-id-") as raw:
        project = Path(raw)
        run_id = "generated-review--2"
        path = project / ".pf" / "runs" / run_id / "run.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(yaml.safe_dump({"id": run_id, "status": "completed"}, sort_keys=False), encoding="utf-8")
        assert run_root(project, run_id) == path.parent
        assert load_run(project, run_id)["id"] == run_id
    print("PASS: run ids preserve repeated hyphens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
