# MCP security review

Pass with residual operational condition.

- Authorization is Ledger-first; transcript/event reading occurs after project binding verification.
- New session read calls use a pure Core Ledger lookup and do not update stale presence.
- `project_root` cannot switch projects, including on new methods.
- A configured `--session` cannot be overridden by a tool argument; a differing
  argument returns `session_mismatch`.
- Chat reads only the already redacted PF transcript, never raw Codex payloads.
- Activity returns selected normalized fields; no raw `data` object or raw journal location is returned.
- Bounded limits cap MCP response expansion.
- Stable error objects avoid stack traces, absolute paths and authorization internals.
- Hook installer is opt-in, project-local, idempotent and reversible with a backup; trust/loading remains an operator check.
