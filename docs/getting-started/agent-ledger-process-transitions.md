# Agent Ledger and Process Transitions

Agent Ledger records attendance and sessions through the CLI; it is not a
separate agent. It is optional for ordinary sessionless Garage work. Use these
operator examples only when explicit session tracking or Director coordination
is selected; a single-agent `1-1-1-1` session does not need a lease to itself.
The commands below assume an onboarded project and an existing workplace:

```bash
python .pf/runtime/bin/pf.py session-start --workplace <workplace> --project-root . --agent primary-agent --process task-batch-execution
python .pf/runtime/bin/pf.py session-heartbeat --project-root .
python .pf/runtime/bin/pf.py session-status --project-root . --json
python .pf/runtime/bin/pf.py session-end --project-root .
```

When the workplace is already initialized, register agents and check availability:

```bash
python .pf/runtime/bin/pf.py agent-register --workplace <workplace> --agent director-local --role director --role orchestrator
python .pf/runtime/bin/pf.py agent-checkin --workplace <workplace> --agent director-local --role director --role orchestrator
python .pf/runtime/bin/pf.py agent-availability --workplace <workplace> --role director --json
```

Create route and handoff packages in a project:

```bash
python .pf/runtime/bin/pf.py process-route-list --project-root .
python .pf/runtime/bin/pf.py handoff-create --project-root . --route <route-id> --from-run <run-id> --id <handoff-id> --apply
python .pf/runtime/bin/pf.py handoff-status --project-root . --handoff <handoff-id> --workplace <workplace> --json
python .pf/runtime/bin/pf.py agent-director-tick --workplace <workplace> --project-root .
```

For shell workers, prepare an answers file from the distribution example
`examples/orchestrator-shell-agents/minimal/orchestrator-shell-agent-plan.yaml`.
Pass its actual path; that example is not automatically copied into the project:

```bash
python .pf/runtime/bin/pf.py orchestrator-shell-plan-create --project-root . --run orchestrated-work --title "Orchestrated work" --answers <answers-file> --apply
python .pf/runtime/bin/pf.py orchestrator-shell-plan-apply --project-root . --run orchestrated-work --workplace <workplace> --model <model> --apply
```

Shell-agent plan fields affect execution. `allow_write_scope_overlap: true`
changes generated assignment/capsule overlap policy and inspector scheduling.
Keep it disabled for ordinary independent writers. Subagent policy is copied
into the capsule and enforced by `worker-run collect`.

`--model` is optional. When present, it applies to all shell workers in the
plan and is exposed through assignment/capsule metadata, `PF_AGENT_MODEL`, and
shell command model arguments.

Reasoning effort is not a CLI flag on `orchestrator-shell-plan-apply`. Set it
in the plan with `runtime.reasoning_effort` or per worker with
`reasoning_effort`; `worker-run prepare/start` can also override it with
`--reasoning-effort`.

After apply, inspect `.pf/runs/<run-id>/config-resolution-report.yaml` to see the resolved driver, model, reasoning effort, overlap, start, output, and subagent-report behavior.

Boundary rule: Agent Ledger records check-in/check-out, presence, and leases;
Agent Director uses those records to coordinate routes, handoffs, leases, and
continuations; the Process Execution Inspector (`execution-inspector-*` or
compatible `supervisor-*`) checks assigned worker runtime state and required
outputs; Worker Agent performs the capsule task. `agent-director-tick` must not
create `.pf/runtime/agent-runs/` process state, and inspector ticks must not
write workplace ledger or lease files.
