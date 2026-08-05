# Shell Agent Subagent Policy

Shell agents are OS processes launched through ProcessForge runtime drivers and supervised by the bounded file-first supervisor.

This policy is for external runtime workers. It is not required for the default
single-agent session flow, where the primary agent owns execution and uses CLI
checks/gates as inspection. In `single_agent_with_subagents`, native subagents
remain helpers inside the primary session unless they explicitly register and
check in as separate workplace agents.

Each worker receives only its task assignment, assignment capsule, allowed write scope, allowed read scope, forbidden scope, required outputs, and `subagent_policy`. A shell worker may invoke native subagents only when the capsule policy allows it.

Shell-agent config fields are behavioral, not suggestions. `allow_subagents` and `subagent_policy` are copied into the generated assignment capsule. `worker-run collect` enforces required worker outputs, the expected report artifact, and subagent reports only when `subagent_policy.allow=true` and `subagent_policy.require_reports=true`.

`orchestrator-shell-plan-apply --model <model>` applies an optional model to
all shell workers in that multi-agent plan. The model is written into the
generated assignments, capsules, worker command state, `PF_AGENT_MODEL`, and
the shell command model arguments.

Reasoning effort is selected independently. A plan may set
`runtime.reasoning_effort`, and a worker may override it with
`reasoning_effort` or `agent_reasoning_effort`. Generated assignments and
capsules store the resolved value as `agent_reasoning_effort`; worker runtime
state exposes it as `PF_AGENT_REASONING_EFFORT`. The `codex-exec` driver maps
that value to `PF_CODEX_REASONING_EFFORT`, and its wrapper passes
`model_reasoning_effort="<value>"` to Codex only when the value is non-empty.

When reports are required, the shell worker must write them under `.pf/artifacts/subagents/<worker-id>/`. Workers with `allow_subagents=false` are not required to create subagent reports. Public smoke tests use neutral simulated reports and must not depend on real Claude, Codex, Gemini, Cursor, or OpenCode CLIs.

`orchestrator-shell-plan-apply` writes `.pf/runs/<run-id>/config-resolution-report.yaml` so operators can see which config values were applied to assignments, capsules, supervisor scheduling, and collection checks.
