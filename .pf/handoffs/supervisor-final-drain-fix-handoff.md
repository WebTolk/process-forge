# Supervisor Final Drain Fix Handoff

- objective: stabilize `supervisor run` so detached workers that finish near the max-tick boundary are observed and collected before the command returns
- implementation: `command_supervisor_run()` now performs a bounded final drain by calling `command_supervisor_tick(..., start_allowed=False)` until no running/completed-uncollected workers remain or the drain timeout expires
- new CLI option: `supervisor run --final-drain-timeout <seconds>`
- new smoke: `tools/smoke_supervisor_final_drain.py`
- release integration: `smoke_supervisor_final_drain` added to `release-test`
- docs updated: `docs/concepts/process-supervisor.md`, `docs/getting-started/runtime-driver-supervisor.md`, `docs/release-checklist.md`
- evidence report: `.pf/artifacts/supervisor-final-drain-fix-report.md`
- review: `.pf/reviews/supervisor-final-drain-fix-review.md`
- validation passed: `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` in 227.19s
- validation passed: `python bin/pf.py release-test --root . --public --timeout-scale 1` in 223.87s
- validation passed: `python bin/pf.py release-pack --root . --output dist/processforge.zip` with 458 files
- validation passed: `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`; extracted archive release-test passed in 225.99s
- remaining delivery step: none
