# Config Behavior Audit Report

Generated: 2026-07-26 12:05 +04:00

## Scope

Audited the public config surface for agent ledger, handoffs, process routes, continuation capsules, orchestrator shell-agent plans, worker-run collection, and supervisor scheduling.

Primary files inspected:

- `schemas/orchestrator-shell-agent-plan.schema.json`
- `templates/orchestrator-shell-agent-plan.yaml`
- `examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml`
- `schemas/orchestrator-task-plan.schema.json`
- `schemas/assignment.schema.json`
- `schemas/context-capsule.schema.json`
- `schemas/agent-lease.schema.json`
- `schemas/process-handoff.schema.json`
- `schemas/process-route-map.schema.json`
- `schemas/continuation-capsule.schema.json`
- `tools/processforge.py`

The field inventory is stored in `.pf/artifacts/config-behavior-audit/inventory.yaml`.

## Findings

Confirmed issue:

- `allow_write_scope_overlap: true` was used as a force flag during task/capsule creation, but generated assignment/capsule state could still carry raw `overlap_check.status=fail`.
- This created a contradictory contract: the plan allowed overlap while materialized worker files said overlap failed.

Not reproduced in the current checkout:

- `python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py` passed before changes in this run.
- The smoke was still too weak because it checked report existence but did not assert config resolution, overlap policy materialization, or diagnostic output quality.

Partial or metadata-like surfaces:

- `route.requires_agent.status` is visible in route/handoff contracts but remains mostly declarative in the current MVP.
- `continuation waiting_for.expected_artifacts` is represented and surfaced by doctor/status paths, but no autonomous resume scheduler enforces it yet.

## Decisions

- Public config fields must affect behavior, be explicit metadata, or fail validation.
- Unsupported shell-agent plan fields fail validation unless they use `metadata` or an `x_` extension namespace.
- `allow_write_scope_overlap: true` means workers in the same resolved plan may overlap write scopes. Generated assignments/capsules record `policy: allow_write_scope_overlap`, `overlap_policy: allow`, and non-failing overlap checks.
- `allow_write_scope_overlap: false` or absence keeps deterministic overlap failure/blocking.
- `allow_subagents` and `subagent_policy` are copied into capsules and enforced by `worker-run collect`.
- `runtime.max_parallel_workers` is now a public shell-agent plan field and lets the public minimal example start both independent workers in the same scheduling layer.

## Before And After

Before:

```yaml
allow_write_scope_overlap: true
non_overlap:
  policy: block_on_write_overlap
  overlap_check:
    status: fail
```

After:

```yaml
allow_write_scope_overlap: true
non_overlap:
  policy: allow_write_scope_overlap
  overlap_policy: allow
  overlap_policy_source: plan.allow_write_scope_overlap
  overlap_check:
    status: allowed
    policy: allow
    source: plan.allow_write_scope_overlap
```

Config resolution report:

```yaml
resolved:
  allow_write_scope_overlap:
    value: true
    source: plan.allow_write_scope_overlap
    behavior:
      - assignment.overlap_policy=allow
      - supervisor.write_scope_overlap=allow_for_plan
```

## Commands Run

```bash
python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py
python -m py_compile tools/processforge.py tools/smoke_orchestrator_shell_agents_with_subagent_policy.py tools/smoke_config_behavior_contracts.py
python tools/validate-process-forge-schemas.py --root .
python tools/smoke_config_behavior_contracts.py
python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py
python tools/smoke_agent_ledger.py
python tools/smoke_process_transition_handoff.py
python tools/smoke_agent_director_tick.py
python tools/smoke_first_run.py
python tools/smoke_process_run_task_batch.py
python tools/smoke_runtime_driver_registry.py
python tools/smoke_worker_run_shell.py
python tools/smoke_process_supervisor_tick.py
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --write
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root . --only smoke_orchestrator_shell_agents_with_subagent_policy --public --fail-fast --timeout-scale 1
python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1
python bin/pf.py release-test --root . --public --timeout-scale 1
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1
```

## Final Validation

- Targeted smokes: PASS.
- Existing public smokes: PASS.
- Validators: schema PASS, public cleanliness PASS, checksum PASS after inventory refresh.
- Public release-test targeted shell-agent smoke: PASS.
- Full public release-test with `--fail-fast`: PASS.
- Full public release-test without `--fail-fast`: PASS.
- Release archive test with extracted full public test: PASS.
- Separate clean extracted proof: `smoke_config_behavior_contracts.py` PASS, `smoke_orchestrator_shell_agents_with_subagent_policy.py` PASS, extracted public `release-test --fail-fast` PASS with expected non-git warning.
- Archive hygiene: 481 entries, forbidden entries 0.
- `git diff --check`: PASS; Windows CRLF normalization warnings only.

## Remaining Limitations

- The route `requires_agent.status` field remains documented as partial behavior for this MVP.
- Continuation expected artifacts are represented and checked structurally, but not yet enforced by an autonomous continuation scheduler.
