# File Flow Contract Fix Report

- date: `2026-07-25`
- run: `file-flow-contract-fix-20260725`
- source audit: `.pf/artifacts/file-flow-audit-report.md`
- fix plan: `.pf/artifacts/file-flow-fix-plan.md`

## Implemented

- Aligned assignment schema with executable task records:
  - required executable fields now include `schema_version`, `run_id`, `iterations`, and `result`
  - task status enum now matches the CLI doctor lifecycle
  - object-form `required_outputs` now requires `path`
  - expected report artifact paths reject absolute/private traversal forms
- Added schema validation for `.pf/runs/*/run.yaml`.
- Made `task-complete` enforce required outputs and expected report artifacts.
- Added explicit `--waive-required-output <id>:<reason>` support, persisted in task result waivers.
- Extended `task-doctor` to report required output and expected report state.
- Made `run-complete` write summary and handoff before returning a completed run.
- Split durable `run-doctor` from private runtime event checks with `--runtime-events`.
- Protected ProcessForge-owned worker environment variables from runtime driver overrides.
- Removed new-run creation of deprecated `.pf/runs/<run>/artifacts` and `.pf/runs/<run>/reviews`.
- Added assignment checksum and immutable marker to newly generated assignment capsules.
- Made automated worker prepare/start reject stale capsules instead of silently overwriting them.
- Added `.pf/registries/tools.yaml` provider for `local_process_execution`, closing the required context capability gap.
- Documented the canonical file-flow contract in `.pf/adr/file-flow-canonical-contract.md`.
- Updated capsule/ECP docs and hooks limitations.

## Shell-Agent Evidence

Shell agents launched and collected through ProcessForge:

- `schema-contract-agent`: `.pf/artifacts/file-flow-agents/schema-contract-agent-report.md`
- `cli-lifecycle-agent`: `.pf/artifacts/file-flow-agents/cli-lifecycle-agent-report.md`
- `context-capsule-agent`: `.pf/artifacts/file-flow-agents/context-capsule-agent-report.md`
- `runtime-hooks-agent`: `.pf/artifacts/file-flow-agents/runtime-hooks-agent-report.md`

All four worker tasks were completed through `worker-run collect`.

## Compatibility Migrations

- Legacy `.pf/assignments/*` records with required output ids but no paths were given explicit durable report paths where matching artifacts already existed.
- Public assignment text that contained local `D:\.agents` paths was rewritten to neutral shared-installation wording.
- One stale required handoff path was updated to the existing run handoff artifact.

## Verification

- `python -m py_compile tools/processforge.py tools/validate-process-forge-schemas.py tools/smoke_process_run_task_batch.py tools/smoke_runtime_driver_registry.py tools/smoke_worker_run_shell.py tools/smoke_full_shell_agents_supervisor.py tools/smoke_shell_agent_heartbeat_contract.py`
- `python tools/validate-process-forge-schemas.py`
- `python tools/validate-public-cleanliness.py`
- `python tools/processforge.py doctor-context --project-root .`
- `python tools/smoke_process_run_task_batch.py`
- `python tools/smoke_runtime_driver_registry.py`
- `python tools/smoke_worker_run_shell.py`
- `python tools/smoke_shell_agent_heartbeat_contract.py`
- `python tools/smoke_full_shell_agents_supervisor.py`
- `python tools/processforge.py release-test --root . --fail-fast`

All commands above passed. Full release-test completed in `213.51s` with `RESULT: PASS`.

## Residual Notes

- `process-doctor --process task-batch-execution` still reports missing companion docs/examples for that process. This is an authoring backfill gap outside the file-flow contract repair.
- Snapshot health remains `warn` because optional providers are unresolved; `doctor-context` passes.
