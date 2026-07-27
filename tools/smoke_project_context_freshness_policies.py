#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from context_lock_smoke_helpers import check_json, make_project, refresh, write_package


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-context-policy-") as raw:
        simple = make_project(Path(raw) / "simple")
        refresh(simple)
        write_package(simple, core_versions=["5.4.5"], articles_generation="B")
        simple_result = check_json(simple)
        assert simple_result["status"] == "stale"
        assert simple_result["policy_action"] == "ask_operator"
        organized = make_project(Path(raw) / "organized", organized=True)
        refresh(organized)
        write_package(organized, core_versions=["5.4.5"], articles_generation="B")
        organized_result = check_json(organized)
        assert organized_result["status"] == "stale"
        assert organized_result["policy_action"] == "notify_director"
        write_package(organized, core_versions=[], articles_generation="B")
        broken = check_json(organized)
        assert broken["status"] == "broken"
        assert broken["policy_action"] == "block"
    print("PASS: project context freshness policies smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
