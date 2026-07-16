# First-Run Processes Review

## Reviewed Object

ProcessForge first-run processes MVP.

## Result

pass_with_conditions

## Findings

- PASS: Workplace initialization and project onboarding are separate process definitions and separate CLI surfaces.
- PASS: Project onboarding creates `START_AGENT_HERE.md`, first assignment, snapshot, report, review, and handoff.
- PASS: First-run smoke test verifies workplace init, project onboarding, agent prompt, doctors, and events.
- PASS: Public cleanliness and checksum gates passed after inventory refresh.
- WARN: `--interactive` is accepted but not interactive yet; this is documented as file-only MVP behavior.
- WARN: Doctor Project may still warn about missing project knowledge resource index for minimal projects.

## Evidence

- `tools/smoke_first_run.py`
- `processes/project-onboarding.yaml`
- `prompts/workplace-initialization-agent.md`
- `prompts/project-onboarding-agent.md`
- `QUICKSTART.md`
- `docs/getting-started/first-run.md`

## Recommendation

Accept this MVP with the documented non-interactive `--interactive` limitation.
