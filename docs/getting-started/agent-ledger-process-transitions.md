# Agent Ledger and Process Transitions

Agent Ledger is CLI-managed attendance/session state, not a separate agent.
For the default single-agent `1-1-1-1` flow, use session aliases and do not
grant an explicit lease to yourself:

```bash
python bin/pf.py session-start --workplace <workplace> --project-root . --agent primary-agent --process task-batch-execution
python bin/pf.py session-heartbeat --project-root .
python bin/pf.py session-status --project-root . --json
python bin/pf.py session-end --project-root .
```

Create a workplace, register agents, and check availability:

```bash
python bin/pf.py workplace-init --workplace <workplace> --apply
python bin/pf.py agent-register --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-checkin --workplace <workplace> --agent director-local --role director --role orchestrator
python bin/pf.py agent-availability --workplace <workplace> --role director --json
```

Create route and handoff packages in a project:

```bash
python bin/pf.py process-route-list --project-root .
python bin/pf.py handoff-create --project-root . --route <route-id> --from-run <run-id> --id <handoff-id> --apply
python bin/pf.py handoff-status --project-root . --handoff <handoff-id> --workplace <workplace> --json
python bin/pf.py agent-director-tick --workplace <workplace> --project-root .
```

For shell workers:

```bash
python bin/pf.py orchestrator-shell-plan-create --project-root . --run orchestrated-work --title "Orchestrated work" --answers examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml --apply
python bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --model <model> --apply
```

Shell-agent plan fields are behavioral. `allow_write_scope_overlap: true` changes generated assignment and capsule overlap policy and supervisor scheduling for that plan. Subagent policy is copied into the capsule and enforced by `worker-run collect`.

`--model` is optional. When present, it applies to all shell workers in the
plan and is exposed through assignment/capsule metadata, `PF_AGENT_MODEL`, and
shell command model arguments.

After apply, inspect `.pf/runs/<run-id>/config-resolution-report.yaml` to see the resolved driver, model, overlap, start, output, and subagent-report behavior.

Boundary rule: Agent Ledger records check-in/check-out, presence, and leases;
Agent Director uses those records to coordinate routes, handoffs, leases, and
continuations; the Process Execution Inspector (`execution-inspector-*` or
compatible `supervisor-*`) checks assigned worker runtime state and required
outputs; Worker Agent performs the capsule task. `agent-director-tick` must not
create `.pf/runtime/agent-runs/` process state, and inspector ticks must not
write workplace ledger or lease files.
