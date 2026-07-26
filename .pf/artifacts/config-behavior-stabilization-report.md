# Config Behavior Stabilization Report

Generated: 2026-07-26 12:05 +04:00

## Reproduction

Command requested by the assignment:

```bash
python tools/smoke_orchestrator_shell_agents_with_subagent_policy.py
```

Observed in this checkout before changes:

```text
PASS: orchestrator shell agents with subagent policy smoke
```

The exact failing symptom from the assignment was not reproduced locally. The confirmed root cause was still present in code semantics: overlap allow was treated as a force bypass while raw failing overlap checks could remain in generated assignment/capsule state.

## Root Cause

`allow_write_scope_overlap: true` influenced creation enough to bypass a hard failure, but it did not consistently materialize a resolved allow policy into generated files. The supervisor also used profile concurrency and overlap checks without a plan-level resolved overlap policy.

## Changed Behavior

- `allow_write_scope_overlap: true` now writes non-failing allow overlap policy into generated assignments and capsules.
- Supervisor scheduling respects resolved overlap policy and does not block same-plan workers solely because their write scopes overlap.
- `runtime.max_parallel_workers` is supported in shell-agent plans and used by supervisor scheduling.
- `orchestrator-shell-plan-validate --write-normalized` writes a normalized plan.
- `orchestrator-shell-plan-apply` writes `.pf/runs/<run-id>/orchestrator-shell-plan.normalized.yaml` and `.pf/runs/<run-id>/config-resolution-report.yaml`.
- Unsupported public shell-agent plan fields fail validation unless they use `metadata` or `x_`.
- `worker-run collect` negative behavior is covered for missing required subagent reports.

## Files Changed

- `tools/processforge.py`
- `tools/smoke_config_behavior_contracts.py`
- `tools/smoke_orchestrator_shell_agents_with_subagent_policy.py`
- `schemas/orchestrator-shell-agent-plan.schema.json`
- `templates/orchestrator-shell-agent-plan.yaml`
- `examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml`
- `docs/concepts/shell-agent-subagent-policy.md`
- `docs/ru/concepts/shell-agent-subagent-policy.md`
- `docs/getting-started/agent-ledger-process-transitions.md`
- `docs/ru/getting-started/agent-ledger-process-transitions.md`
- `docs/concepts/multi-agent-orchestration.md`
- `docs/ru/concepts/multi-agent-orchestration.md`
- `.pf/adr/config-driven-behavior-contract.md`
- `.pf/artifacts/config-behavior-audit/inventory.yaml`
- `.pf/artifacts/config-behavior-audit/report.md`

## Verification

Passed before full release closeout:

```bash
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
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root . --only smoke_orchestrator_shell_agents_with_subagent_policy --public --fail-fast --timeout-scale 1
python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1
python bin/pf.py release-test --root . --public --timeout-scale 1
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1
```

Final results:

- All targeted and public smokes passed.
- Full public release-test passed with and without fail-fast.
- Release archive test passed against `dist/processforge.zip`.
- Separate clean extracted archive proof passed targeted config behavior smokes and extracted public release-test; the only warning was `git diff --check skipped: not a git repo` inside the temporary extracted archive.
- Archive hygiene check found 481 entries and 0 forbidden entries.

Elapsed active implementation and validation time: about 1.5 hours.

## Remaining Limitations

- Route `requires_agent.status` and continuation `waiting_for.expected_artifacts` remain partial/declarative MVP surfaces.
