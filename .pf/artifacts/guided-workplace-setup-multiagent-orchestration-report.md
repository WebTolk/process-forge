# Guided Workplace Setup & Multi-Agent Orchestration Report

## Result

implemented

## Guided Workplace Setup

Added out-of-box process `guided-workplace-setup` with:

- `processes/guided-workplace-setup.yaml`
- `prompts/guided-workplace-setup-agent.md`
- `schemas/guided-workplace-setup-answers.schema.json`
- `schemas/guided-workplace-setup-proposal.schema.json`
- `templates/guided-workplace-setup.answers.yaml`
- `templates/guided-workplace-setup.proposal.yaml`
- EN/RU getting-started docs
- neutral minimal example
- `tools/smoke_guided_workplace_setup.py`

## Guided CLI

Added nested CLI commands:

- `workplace-setup start`
- `workplace-setup review`
- `workplace-setup apply`
- `workplace-setup status`

The flow writes session artifacts under `<workplace>/.pf-workplace/setup-sessions/<session-id>/`: `answers.yaml`, `proposal.yaml`, `proposal.md`, `review.md`, `apply-report.md`, `agent-instructions.md`, and `next-steps.md`.

`workplace-setup apply --apply` delegates to existing `workplace-init` mechanics, then records doctor output and writes an agent instruction snippet.

## Dialogue Flow

The prompt instructs the setup agent to ask in blocks, not all at once:

- machine layout
- operator/agent environment
- privacy and safety
- resources
- platform contracts
- first project

Proposal artifacts are generated before apply and are intended for operator review.

## Multi-Agent Orchestration

Added out-of-box process `multi-agent-task-orchestration` with:

- `processes/multi-agent-task-orchestration.yaml`
- `prompts/multi-agent-task-orchestration-agent.md`
- `prompts/multi-agent-worker-agent.md`
- `schemas/orchestrator-task-plan.schema.json`
- `schemas/worker-launch-prompt.schema.json`
- `templates/orchestrator-task-plan.yaml`
- `templates/worker-launch-prompt.md`
- EN/RU concept and getting-started docs
- neutral minimal example
- `tools/smoke_multiagent_orchestration_process.py`

## Orchestration CLI

Added nested commands and flat aliases:

- `orchestrator-plan create`
- `orchestrator-plan validate`
- `orchestrator-plan apply`
- `orchestrator-plan status`
- `worker-launch-prompt create`
- `orchestrator-plan-create`
- `orchestrator-plan-validate`
- `orchestrator-plan-apply`
- `orchestrator-plan-status`
- `worker-launch-prompt-create`

`orchestrator-plan apply --apply` creates or updates the run plan, creates worker tasks, refreshes project context, generates assignment capsules, writes worker launch prompts, writes task/orchestration indexes, writes an initial orchestrator handoff, and runs `task-doctor`/`run-doctor`.

## Worker Boundary

Worker launch prompts state that the worker:

- is not the orchestrator
- uses only the assigned task and assignment capsule
- does not rebuild full project context unless explicitly allowed
- does not edit outside `allowed_files`
- does not read outside `allowed_read_files` unless explicitly allowed
- respects `forbidden_files`
- produces `required_outputs`
- writes `expected_report`
- stops and reports if scope is insufficient

Assignment capsules preserve `worker_may_rebuild_context: false` by default.

## Scope Checks

`orchestrator-plan validate` checks:

- unique worker ids
- writer workers have explicit `allowed_files`
- bounded read/context scope is present
- `forbidden_files` do not overlap `allowed_files`
- required outputs have paths
- required outputs are inside allowed scope or project artifact area
- `worker_may_rebuild_context` is false by default
- parallel write scopes do not overlap unless explicitly allowed
- integration output is declared

## Docs And Examples

Updated README, quickstarts, docs indexes, first-run docs, agent prompt runbooks, multi-agent file flow, and context capsule docs. Added neutral examples under:

- `examples/guided-workplace-setup/minimal/`
- `examples/multi-agent-orchestration/minimal/`

Examples use neutral ids such as `example-docs-worker`, `example-test-worker`, and `example-integration`.

## Verification

Passed:

- `python -m py_compile tools/processforge.py tools/smoke_guided_workplace_setup.py tools/smoke_multiagent_orchestration_process.py`
- `python tools/smoke_guided_workplace_setup.py`
- `python tools/smoke_multiagent_orchestration_process.py`
- `python tools/smoke_multiagent_assignment_contract.py`
- `python tools/smoke_manifest_driven_platforms.py`
- `python tools/smoke_platform_inheritance.py`
- `python tools/smoke_update_framework_readonly.py`
- `python tools/smoke_update_framework_validation.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/validate-process-forge-checksums.py --root . --check`
- `python bin/pf.py release-test --root .`
- `python bin/pf.py release-pack --root . --output dist/processforge-v1.0.0.zip`
- `python bin/pf.py release-archive-test --archive dist/processforge-v1.0.0.zip`
- archive forbidden entry inspection: 415 files, 0 forbidden entries
- `git diff --check`

Checksum inventory was refreshed with `python tools/validate-process-forge-checksums.py --root . --write` after adding public files.
`release-test` also refreshed authoring parity/backfill artifacts for the two new process definitions.

## MVP Limitations

- Guided setup is an agent-guided file workflow, not a terminal interactive wizard.
- Resource creation during guided apply is limited to existing workplace-init registry/bootstrap mechanics and the setup session artifacts.
- Orchestrator apply creates tasks, capsules, prompts, indexes, summary, and handoff; worker execution and final integration remain human/agent-run steps.
- Required output existence after worker execution is a process gate and prompt contract; the MVP validates required output declarations before launch.
