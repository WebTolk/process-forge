# Heartbeat Contract Fix Handoff

- handoff_at: `2026-07-25T14:36:25+04:00`
- status: `implementation and release validation complete`
- owner: `codex`

## What Changed

The shell-launched worker heartbeat proof contract is explicit and mandatory.
`worker-run` injects canonical runtime env, resolves the heartbeat artifact path
from the driver spec, and the test shell agent writes atomic heartbeat JSON with
run/task identity, pid, status, timestamp, and sequence.

## Key Paths

- Runtime heartbeat: `.pf/runtime/agent-runs/<run-id>/<task-id>/heartbeat.json`
- Targeted smoke: `tools/smoke_shell_agent_heartbeat_contract.py`
- Existing supervisor proof smoke: `tools/smoke_shell_launched_agents_supervisor_fix.py`
- Report: `.pf/artifacts/heartbeat-contract-fix-report.md`
- Review: `.pf/reviews/heartbeat-contract-fix-review.md`

## Final Evidence

- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`: PASS
- `python bin/pf.py release-test --root . --public --timeout-scale 1`: PASS
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`: PASS, `FILES: 457`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`: PASS
- clean extracted targeted smokes and `release-test --public --fail-fast`: PASS with expected non-git warning

## Next Steps

1. Use `.pf/artifacts/heartbeat-contract-fix-report.md` as the evidence index for this slice.
2. Re-run archive hygiene after any further release-facing file changes.
