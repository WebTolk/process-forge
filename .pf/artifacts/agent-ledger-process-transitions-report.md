# Agent Ledger Process Transitions Report

Status: ready_for_review

## Scope

Implemented the MVP layer for Agent Attendance Ledger, leases/keys, process routes, formal handoff packages, Agent Director tick, continuation capsules, and orchestrator shell-agent plans with subagent policy metadata.

## Schemas Added

- `schemas/agent-registry.schema.json`
- `schemas/agent-session-event.schema.json`
- `schemas/agent-presence.schema.json`
- `schemas/agent-lease.schema.json`
- `schemas/process-route-map.schema.json`
- `schemas/process-transition.schema.json`
- `schemas/process-handoff.schema.json`
- `schemas/handoff-input-manifest.schema.json`
- `schemas/handoff-return-package.schema.json`
- `schemas/agent-director-policy.schema.json`
- `schemas/continuation-capsule.schema.json`
- `schemas/orchestrator-shell-agent-plan.schema.json`

## CLI Commands Added

- Agent ledger: `agent-register`, `agent-list`, `agent-checkin`, `agent-heartbeat`, `agent-checkout`, `agent-status`, `agent-availability`, `agent-ledger-doctor`.
- Agent leases: `agent-lease-grant`, `agent-lease-release`, `agent-lease-revoke`, `agent-lease-list`, `agent-lease-doctor`.
- Process routes and handoffs: `process-route-list`, `process-route-validate`, `process-route-doctor`, `handoff-create`, `handoff-offer`, `handoff-status`, `handoff-accept`, `handoff-start-target-run`, `handoff-return`, `handoff-finalize`, `handoff-doctor`.
- Agent Director: `agent-director-tick`, `agent-director-run`, `agent-director-status`.
- Continuations: `continuation-create`, `continuation-status`, `continuation-resume`, `continuation-doctor`.
- Shell orchestration aliases: `orchestrator-shell-plan-create`, `orchestrator-shell-plan-validate`, `orchestrator-shell-plan-apply`.

## Model

Agent registry lives at `<workplace>/registries/agents.yaml`. Session events are appended to `<workplace>/runtime/agent-ledger/sessions.ndjson`. Current presence is stored under `<workplace>/runtime/agent-presence/`. Leases are key files under `<workplace>/runtime/agent-leases/`.

Process route maps live at `.pf/process-routes.yaml` for project-local routes. Handoff packages live under `.pf/handoffs/<handoff-id>/` and include `handoff.yaml`, `handoff.md`, `input-manifest.yaml`, `expected-output.yaml`, and `return-package.yaml`.

Agent Director tick checks waiting handoffs, reads workplace presence, grants a lease when a required role is online, leaves the handoff waiting when no agent is available, and marks expired active leases as `stale`.

Continuation capsules live under `.pf/continuations/<continuation-id>.yaml`. `continuation-resume` is MVP partial: it verifies expected artifacts and records `resumed` when they exist; it does not automate downstream process execution.

## Shell Agent And Subagent Policy

Orchestrator shell-agent plans reuse the existing orchestrator-plan implementation. Workers receive task assignments, capsules, launch prompts, runtime driver configuration, optional leases when a workplace is supplied, and `subagent_policy`.

The neutral `test-shell-agent` fixture reads the capsule policy. If subagents are allowed and reports are required, it writes simulated child reports under `.pf/artifacts/subagents/<worker-id>/` and declares `simulated_subagents: true` in the worker report. Workers with `allow=false` do not write subagent reports.

`worker-run collect` enforces required outputs and required subagent reports.

## Process Authoring Extension

`schemas/process-authoring-answers.schema.json`, `templates/process-authoring-answers.yaml`, `prompts/process-authoring-agent.md`, and EN/RU process-authoring docs now support process transitions, handoff/agent requirements, continuation ownership, and shell-worker subagent policy questions.

## Tests Run

- `python -m py_compile tools/processforge.py tools/test_agents/pf_shell_agent.py tools/smoke_agent_ledger.py tools/smoke_process_transition_handoff.py tools/smoke_agent_director_tick.py tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `python tools/smoke_agent_ledger.py`
- `python tools/smoke_process_transition_handoff.py`
- `python tools/smoke_agent_director_tick.py`
- `python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `python tools/smoke_first_run.py`
- `python tools/smoke_process_run_task_batch.py`
- `python tools/smoke_runtime_driver_registry.py`
- `python tools/smoke_worker_run_shell.py`
- `python tools/smoke_process_supervisor_tick.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1`
- `python bin/pf.py release-test --root . --public --timeout-scale 1`
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1`
- `git diff --check`

## Public Boundary

The public archive includes neutral file-first commands, schemas, templates, docs, examples, and deterministic smokes. It does not include `.pf/runtime`, `.pf/dogfooding`, `.ps1`, network tests, database requirements, WT AICC/web UI, platform support packs, or built-in real external agent ecosystem drivers.
