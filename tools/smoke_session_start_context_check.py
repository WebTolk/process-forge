#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from context_lock_smoke_helpers import make_project, refresh, require_ok, run_pf, write_package


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-session-context-") as raw:
        project = make_project(Path(raw))
        refresh(project)
        fresh = require_ok(run_pf("session-start", "--project-root", str(project), "--mode", "resume"))
        assert "PROJECT_CONTEXT_CHECK: fresh" in fresh
        write_package(project, core_versions=["5.4.5"], articles_generation="B")
        stale = require_ok(run_pf("session-start", "--project-root", str(project), "--mode", "resume"))
        assert "PROJECT_CONTEXT_CHECK: stale policy_action=ask_operator" in stale
    print("PASS: session-start context check smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
