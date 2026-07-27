#!/usr/bin/env python3
"""Smoke-test tool update policy and custom-command block."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from update_smoke_helpers import first_candidate_id, make_update_fixture, require_ok, run_pf


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-tool-update-") as raw:
        workplace = Path(raw)
        make_update_fixture(workplace, subject_id="local-linter", tool=True)
        require_ok(run_pf("update", "candidates", "refresh", "--workplace", str(workplace)))
        candidate_id = first_candidate_id(workplace)
        require_ok(run_pf("update", "stage", "--workplace", str(workplace), "--candidate", candidate_id))
        require_ok(run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id, "--confirm"))
        assert "new tool" in (workplace / "tools" / "local-linter.py").read_text(encoding="utf-8")
        data = json.loads((workplace / "runtime" / "update" / "candidates.json").read_text(encoding="utf-8"))
        data["candidates"][0]["update_policy"] = {"mode": "custom_command_requires_confirmation", "command": "echo should-not-run"}
        (workplace / "runtime" / "update" / "candidates.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        blocked = run_pf("update", "apply", "--workplace", str(workplace), "--candidate", candidate_id, "--confirm")
        if blocked.returncode == 0 or "custom command" not in blocked.stdout:
            raise AssertionError(blocked.stdout)
    print("PASS: tool update policy smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
