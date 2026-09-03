# Spark review remediation

Accepted and corrected:

- Initialization status now reports all four resource groups in the required aggregate shape and validates supplied workplace paths as `missing`, `unreachable`, `reachable` or `auto`.
- A conflicting non-session MCP `project_root` now returns stable `session_project_mismatch`, rather than generic `read_failed`.

Evidence: `py_compile` passed; `project-init-status` against a nonexistent workplace returned `workplace: missing`; FTS5 smoke and `git diff --check` passed.

Deferred explicitly: a metadata-first snapshot producer, the complete `empty/current/stale/unavailable` search lifecycle, and a Ledger-backed stdio handshake/mismatch smoke. These remain required before release acceptance.
