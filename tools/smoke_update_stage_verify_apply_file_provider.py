#!/usr/bin/env python3
"""Smoke-test stage, verify, apply, and rollback for local file provider packages."""

from __future__ import annotations

import tempfile
from pathlib import Path

from update_smoke_helpers import first_candidate_id, make_update_fixture, require_ok, run_pf


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-stage-") as raw:
        workplace = Path(raw)
        make_update_fixture(workplace)
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        candidate_id = first_candidate_id(workplace)
        require_ok(run_pf("update", "stage", "--workplace", str(workplace), "--candidate", candidate_id))
        require_ok(run_pf("update", "verify", "--workplace", str(workplace), "--candidate", candidate_id))
        blocked = run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id)
        if blocked.returncode == 0 or "--confirm" not in blocked.stdout:
            raise AssertionError(blocked.stdout)
        require_ok(run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id, "--confirm"))
        installed = (workplace / "registries" / "installed-subjects.yaml").read_text(encoding="utf-8")
        assert "version: 1.1.0" in installed
        assert "content: updated" in (workplace / "packages" / "acme.software-processes" / "package.yaml").read_text(encoding="utf-8")
        require_ok(run_pf("update", "rollback", "--workplace", str(workplace), "--candidate", candidate_id))
        restored = (workplace / "packages" / "acme.software-processes" / "package.yaml").read_text(encoding="utf-8")
        assert "version: 1.0.0" in restored
    print("PASS: update stage/verify/apply/rollback file provider smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
