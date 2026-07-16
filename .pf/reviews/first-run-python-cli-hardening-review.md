# First-Run Python CLI Hardening Review

## Reviewed Object

First-run Python CLI hardening.

## Result

pass_with_conditions

## Findings

- PASS: `START_AGENT_HERE` uses `pf` and `.pf/runtime/bin/pf.py`, not a project-local `tools/processforge.py`.
- PASS: Project onboarding creates the runtime Python launcher.
- PASS: First-run smoke executes the runtime launcher from project root.
- PASS: Negative smoke verifies a broken distribution reference produces a clear FAIL.
- PASS: Smoke and canonical docs use Python launchers.
- WARN: `pf` command availability still depends on PATH; `.pf/runtime/bin/pf.py` is the documented fallback.

## Evidence

- `tools/smoke_first_run.py`
- `tools/processforge.py`
- `bin/pf.py`
- `docs/getting-started/project-onboarding.md`

## Recommendation

Accept with the documented PATH limitation.
