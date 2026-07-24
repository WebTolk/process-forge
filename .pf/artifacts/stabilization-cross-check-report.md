# Stabilization Cross-Check Report

## Subagent Findings Cross-Check

- Runtime observe path: confirmed by runtime auditor and fixed. Evidence:
  `tools/smoke_full_shell_agents_supervisor.py` PASS and full
  `release-test --public --fail-fast` PASS.
- Blocking supervisor tick: confirmed by runtime auditor and fixed by
  supervisor detached scheduling plus observe/collect ticks.
- `public-gate` selection mismatch: confirmed by release auditor and fixed.
  Evidence: `release-test --only py_compile --only public-gate --public`
  PASS.
- Extracted archive public gate: confirmed by release auditor and fixed in CLI.
  Final evidence: `release-archive-test --extracted-test full` PASS with
  extracted `release-test --public` PASS.
- Ambiguous docs wording: confirmed by docs auditor and fixed in
  `docs/known-limitations.md`, supervisor docs, quickstarts, and agent runbook.
- Native subagent distinction: fixed in docs and preserved operationally. Native
  subagents were launched externally with ProcessForge assignment/capsule scope
  only.

## Residual Boundaries

- ProcessForge still does not implement a daemon, web UI, database scheduler, or
  built-in real Claude/Codex/Gemini/Cursor/OpenCode runtime drivers.
- Static plan validation still rejects overlapping writer scopes. Runtime
  supervisor overlap handling is for active scheduling of prepared/forced
  handoff cases, not for weakening default authoring validation.
