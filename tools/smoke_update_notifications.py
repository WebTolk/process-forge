#!/usr/bin/env python3
"""Smoke-test update notification create/list/acknowledge."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from update_smoke_helpers import make_update_fixture, require_ok, run_pf


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-update-notifications-") as raw:
        workplace = Path(raw)
        (workplace / "director" / "inbox").mkdir(parents=True)
        make_update_fixture(workplace)
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        require_ok(run_pf("update", "notifications", "create", "--workplace", str(workplace)))
        listed = require_ok(run_pf("update", "notifications", "list", "--workplace", str(workplace), "--json"))
        data = json.loads(listed)
        notification = data["notifications"][0]
        assert notification["candidate_id"]
        assert notification["status"] == "notified"
        assert list((workplace / "director" / "inbox").glob("*.json"))
        require_ok(run_pf("update", "notifications", "acknowledge", "--workplace", str(workplace), "--notification", notification["id"]))
        updated = json.loads((workplace / "runtime" / "update" / "notifications.json").read_text(encoding="utf-8"))
        assert updated["notifications"][0]["status"] == "acknowledged"
    print("PASS: update notifications smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
