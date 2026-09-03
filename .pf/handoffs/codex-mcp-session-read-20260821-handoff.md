# Handoff: Codex MCP session read layer

Delivered in run `codex-mcp-session-read-20260821`.

- New read-only MCP tools: `pf.session_context`, `pf.session_chat`, and `pf.session_activity`.
- Current Codex session is authorized solely by Agent Ledger; a server-bound session cannot be overridden.
- Codex hook adapter captures user, main final and subagent final transcript messages raw-first and replay repairs missing chat effects.
- Project-local hook installer is opt-in, idempotent, backed up and removable. Actual Codex registration/trust remains operator verification via `/hooks`; MCP presence via `/mcp` or `codex mcp list`.
- Focused smoke suite and event validation pass. `doctor-project` retains pre-existing linked-project onboarding failures only.

Primary evidence: `.pf/artifacts/codex-mcp-session-read-20260821/final-validation.md`.
