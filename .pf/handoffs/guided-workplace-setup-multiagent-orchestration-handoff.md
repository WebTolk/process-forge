# Handoff: guided setup and orchestration MVP

Objective:
Deliver out-of-box guided workplace setup and multi-agent orchestration MVP.

Current status:
Implemented and release-validated.

Input artifacts:
- `задания/processforge_guided_workplace_setup_multiagent_orchestration_mvp_master_prompt.md`
- `.pf/artifacts/guided-workplace-setup-multiagent-orchestration-report.md`
- `.pf/reviews/guided-workplace-setup-multiagent-orchestration-review.md`

Files changed:
- `tools/processforge.py`
- `tools/validate-process-forge-schemas.py`
- `.pf/process-forge.yaml`
- `processes/guided-workplace-setup.yaml`
- `processes/multi-agent-task-orchestration.yaml`
- `prompts/`
- `schemas/`
- `templates/`
- `docs/`
- `examples/`
- `tools/smoke_guided_workplace_setup.py`
- `tools/smoke_multiagent_orchestration_process.py`
- `dist/processforge-v1.0.0.zip`
- `dist/processforge-v1.0.0.manifest.json`
- `.pf/artifacts/checksum-inventory.sha256`
- `.pf/authoring/backfill/processes/guided-workplace-setup/`
- `.pf/authoring/backfill/processes/multi-agent-task-orchestration/`
- `.pf/artifacts/parity/processes/`
- `.pf/reviews/parity/processes/`

Files not to touch:
- `.pf/runtime/`
- private machine-local notes
- real platform support packs unless explicitly requested

Known issues:
- None blocking.

Required checks:
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip`
- `git diff --check`

Next recommended action:
Use `workplace-setup` for new machine setup and `orchestrator-plan` for bounded worker assignment flows.
