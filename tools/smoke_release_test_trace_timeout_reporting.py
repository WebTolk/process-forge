#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from processforge import ReleaseCommandResult, run_release_command, write_release_test_report


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pf-release-trace-") as raw:
        root = Path(raw)
        result = run_release_command("fake-timeout-smoke", [sys.executable, "-c", "import time; time.sleep(2)"], root, timeout=1)
        assert result.status == "FAIL", result
        assert result.code == 124, result
        assert "timeout after 1s" in result.output, result.output
        write_release_test_report(
            root,
            [
                ReleaseCommandResult(
                    "fake-timeout-smoke",
                    "FAIL",
                    124,
                    result.output,
                    result.started_at,
                    result.finished_at,
                    result.elapsed_seconds,
                    1,
                    result.command,
                )
            ],
            [],
            public=True,
            started_at=result.started_at,
            finished_at=result.finished_at,
            elapsed_seconds=result.elapsed_seconds,
            trace_smokes=True,
        )
        trace = (root / ".pf" / "runtime" / "release-test" / "latest-trace.ndjson").read_text(encoding="utf-8")
        assert "fake-timeout-smoke" in trace, trace
        assert '"timeout_reason": "timeout"' in trace, trace
    print("PASS: release-test trace timeout reporting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
