# Test report

Qualified source: detached local commit
`99f19b0c32776cd2452f5698b5748751c6587dba`, parent
`7a4021788643e5df325f5ac1e1df1ab70ed02ac6`. The five sealed
source/test/docs/inventory hashes remained unchanged throughout the final run.

| Gate | Result | Exit |
| --- | --- | --- |
| Focused actual-monitor regression cases | 36 passed | 0 |
| PF Python QA `test -- tests -q -rs` | 142 passed, 42 subtests passed, 1 skipped | 0 |
| PF `release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes` | 274/274 checks passed; 3/3 public checks passed | 0 |
| PF `dev-test --root . --suite supervisor-stress --fail-fast --timeout-scale 1` | 6/6 scenarios passed | 0 |
| PF Python Ruff lint/format | owning monitor module and new test passed | 0 |
| PF Python mypy changed typed area / new docstring | four exact changed functions / new formatter passed | 0 |

The full public source run finished at `2026-10-20T19:30:15Z`, native elapsed
1611.532 seconds. Supervisor-stress finished at `2026-10-20T19:32:54Z`, wrapper
elapsed 159.406 seconds. The existing `smoke_runtime_monitor` passed.

The pytest skip is the launcher test requiring interpreter symlink creation:
Windows returned `WinError 1314` because the current token lacks that privilege.
No elevation or infrastructure repair was performed. Whole-owner mypy retains
the same nine pre-existing diagnostics as its fair original-source baseline;
no new errors were introduced. It is not reported as owner-wide type-clean.

The first full attempt stopped on two inventory-only release metadata rows;
the scoped inventory correction and full rerun are documented in
[checksum resolution](checksum-assurance-resolution.md). The second stopped
because release provenance requires a clean source commit; see
[qualification resolution](candidate-qualification-resolution.md). Both failed
attempts are retained, and neither is counted as passed. The exact provenance
smoke passed after qualification, then the entire third run passed.

Portable receipts and raw-log hashes are under `checks/`. Raw execution logs,
preimages, exact typed-area extraction, failed attempts, and the isolated
candidate remain task-private evidence. Tests generated the current version's
ZIP and manifest under the candidate's `dist/`; they are untracked build outputs.
Tracked source is unchanged. No final ZIP content inspection or installed
Runtime/MCP acceptance is claimed by this source-only slice.
