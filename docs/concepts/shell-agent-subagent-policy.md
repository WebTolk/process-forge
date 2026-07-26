# Shell Agent Subagent Policy

Shell agents are OS processes launched through ProcessForge runtime drivers and supervised by the bounded file-first supervisor.

Each worker receives only its task assignment, assignment capsule, allowed write scope, allowed read scope, forbidden scope, required outputs, and `subagent_policy`. A shell worker may invoke native subagents only when the capsule policy allows it.

Shell-agent config fields are behavioral, not suggestions. `allow_subagents` and `subagent_policy` are copied into the generated assignment capsule. `worker-run collect` enforces required worker outputs, the expected report artifact, and subagent reports only when `subagent_policy.allow=true` and `subagent_policy.require_reports=true`.

When reports are required, the shell worker must write them under `.pf/artifacts/subagents/<worker-id>/`. Workers with `allow_subagents=false` are not required to create subagent reports. Public smoke tests use neutral simulated reports and must not depend on real Claude, Codex, Gemini, Cursor, or OpenCode CLIs.

`orchestrator-shell-plan-apply` writes `.pf/runs/<run-id>/config-resolution-report.yaml` so operators can see which config values were applied to assignments, capsules, supervisor scheduling, and collection checks.
