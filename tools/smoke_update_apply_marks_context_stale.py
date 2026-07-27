#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from context_lock_smoke_helpers import check_json, make_project, refresh
from update_smoke_helpers import first_candidate_id, make_update_fixture, require_ok, run_pf


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-context-stale-") as raw:
        workplace = Path(raw)
        make_update_fixture(workplace)
        project = make_project(workplace / "projects")
        refresh(project)
        before = check_json(project)
        assert before["status"] == "fresh"
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        candidate_id = first_candidate_id(workplace)
        require_ok(run_pf("update", "stage", "--workplace", str(workplace), "--candidate", candidate_id))
        require_ok(run_pf("update", "verify", "--workplace", str(workplace), "--candidate", candidate_id))
        apply_output = require_ok(run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id, "--confirm"))
        assert "SNAPSHOTS_MARKED_STALE" in apply_output
        stale = check_json(project)
        assert stale["status"] == "stale"
        assert (project / ".pf" / "runtime" / "context" / "project-context.stale.json").is_file()
        old_id = before["snapshot_id"]
        refresh(project)
        after = check_json(project)
        assert after["status"] == "fresh"
        assert after["snapshot_id"] != old_id
    print("PASS: update apply marks context stale smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
