# Director / Ledger / Execution Inspector Boundary Report

Date: 2026-07-26

## Delivered

- Clarified ProcessForge role semantics:
  - Agent Ledger records check-in/check-out, presence/stale state, and lease/key lifecycle.
  - Agent Director coordinates routes, handoffs, leases, returns, finalization, and continuations.
  - Process Supervisor is now documented as the Process Execution Inspector, a runtime checker for assigned worker tasks.
  - Worker Agent performs the assigned capsule task and writes requested outputs/runtime proof.
- Kept `supervisor` and `supervisor-*` as backward-compatible technical commands.
- Added thin semantic aliases:
  - `execution-inspector-tick`
  - `execution-inspector-run`
  - `execution-inspector-status`
  - `execution-inspector-stop`
- Updated CLI help, process definitions, prompts, schemas/templates, EN/RU docs, release checklist, and checksum inventory.
- Added central boundary docs:
  - `docs/concepts/director-ledger-inspector-boundary.md`
  - `docs/ru/concepts/director-ledger-inspector-boundary.md`
- Added public smoke:
  - `tools/smoke_director_inspector_boundary.py`
- Added audit/decision artifacts:
  - `.pf/artifacts/director-inspector-boundary-audit/inventory.yaml`
  - `.pf/artifacts/director-inspector-boundary-audit/report.md`
  - `.pf/adr/director-ledger-inspector-boundary.md`

## Behavioral Boundary Verified

The new smoke verifies:

- Director leaves a handoff `waiting_for_agent` when the required worker role is offline.
- Director grants a lease and marks handoff `ready` when a worker is checked in.
- Director does not create `.pf/runtime/agent-runs/` worker runtime files.
- Execution Inspector starts/observes/collects worker runtime state through `execution-inspector-run`.
- Inspector writes `status.json`, `command.json`, `process.json`, `heartbeat.json`, `exit.json`, stdout/stderr logs, and the expected report.
- Inspector does not change workplace ledger events, workplace leases, or handoff state.

## Validation

Passed:

- `python -m py_compile tools\processforge.py tools\smoke_director_inspector_boundary.py`
- `python tools\validate-process-forge-schemas.py --root .`
- `python tools\validate-public-cleanliness.py --root .`
- `python tools\validate-process-forge-checksums.py --root . --write`
- `python tools\validate-process-forge-checksums.py --root . --check`
- `python tools\smoke_director_inspector_boundary.py`
- `python tools\smoke_agent_ledger.py`
- `python tools\smoke_agent_director_tick.py`
- `python tools\smoke_process_transition_handoff.py`
- `python tools\smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `python tools\smoke_process_supervisor_tick.py`
- `python tools\smoke_config_behavior_contracts.py`
- `python tools\smoke_first_run.py`
- `python tools\smoke_process_run_task_batch.py`
- `python tools\smoke_runtime_driver_registry.py`
- `python tools\smoke_worker_run_shell.py`
- `python bin\pf.py release-test --root . --only smoke_director_inspector_boundary --public --fail-fast --timeout-scale 1`
- `python bin\pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin\pf.py release-test --root . --public --timeout-scale 1`
- `python bin\pf.py release-pack --root . --output dist\processforge.zip`
- `python bin\pf.py release-archive-test --archive dist\processforge.zip --root . --extracted-test full`
- Extracted archive smoke: `python <extracted>\tools\smoke_director_inspector_boundary.py`
- Extracted archive release-test: `python <extracted>\bin\pf.py release-test --root <extracted> --public --fail-fast --timeout-scale 1`

Extracted archive release-test result was `PASS with warnings` because `git diff --check` is skipped in the temporary extracted archive, which is not a Git repository.

## Remaining Limits

- The compatibility term `supervisor` remains in CLI/file ids, schemas, runtime paths, and some docs where it names the stable technical contract.
- No daemon, web UI, database, network worker control, WT AICC surface, or real external agent built-ins were added.
