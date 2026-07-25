# Shell Agent Subagent Policy

Shell agents are OS processes launched through ProcessForge runtime drivers and supervised by the bounded file-first supervisor.

Each worker receives only its task assignment, assignment capsule, allowed write scope, allowed read scope, forbidden scope, required outputs, and `subagent_policy`. A shell worker may invoke native subagents only when the capsule policy allows it.

When reports are required, the shell worker must write them under `.pf/artifacts/subagents/<worker-id>/`. Public smoke tests use neutral simulated reports and must not depend on real Claude, Codex, Gemini, Cursor, or OpenCode CLIs.
