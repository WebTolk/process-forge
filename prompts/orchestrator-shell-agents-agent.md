# Orchestrator Shell Agents Agent

You are executing the ProcessForge `orchestrator-shell-agents-supervision` process.

Create an orchestrator shell-agent plan, validate it, apply it, and let ProcessForge runtime drivers launch shell workers when `start_policy=supervisor`. Each worker must receive a task assignment, assignment capsule, lease/key when a workplace is supplied, bounded read/write scope, required outputs, and a subagent policy.

This is not the default single-agent mode. It is for external runtime workers,
where each launched worker represents a bounded execution session that may need
Supervisor / Execution Inspector observation.

Subagents are invoked inside the shell-agent harness only when the capsule policy allows it. Public tests must use neutral deterministic fixtures, not real external agent ecosystems.
