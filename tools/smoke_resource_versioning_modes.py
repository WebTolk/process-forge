#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from context_lock_smoke_helpers import check_json, make_project, refresh, write_package


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-context-versioning-") as raw:
        project = make_project(Path(raw))
        refresh(project)
        write_package(project, core_versions=["5.4.5", "6.1.2"], articles_generation="A")
        fresh_updates = check_json(project)
        assert fresh_updates["status"] == "fresh_with_updates", fresh_updates
        assert fresh_updates["updates_available"][0]["snapshot_stale"] is False
        write_package(project, core_versions=["5.4.5", "6.1.2"], articles_generation="B")
        stale = check_json(project)
        assert stale["status"] == "stale", stale
        write_package(project, core_versions=["6.1.2"], articles_generation="B")
        broken = check_json(project)
        assert broken["status"] == "broken", broken
    print("PASS: resource versioning modes smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
