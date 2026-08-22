# Codex Capture Ordering Audit

**Run objective:** verify ordering between raw ingess, ledger routing, and conversation capture for Codex lifecycle events.

## Result

- **Overall status:** **FAIL** (partial ordering regression)
- **Passed checks:** raw ingress durability, Ledger session routing, and MCP `pf.session_*` read-model binding.
- **Failed check:** conversation transcript capture ordering (missing user message in `pf.session_chat`).

## Findings

- **Ordering issue confirmed:** conversation capture can be rejected while raw event is accepted.
  - `tools/pf_runtime/codex_integration.py` installs Codex handlers as async for all events except `SessionEnd`, including `SessionStart` and `UserPromptSubmit`.
  - In `tools/pf_runtime/host.py`, `_conversation_messages` requires an active Ledger presence (`ledger_session`) before appending derived conversation messages.
  - In `tools/pf_runtime/host.py:ingest_event`, raw ingressed receipt is produced first, then conversation capture is attempted, then derived event routing occurs.
  - Live capture artifact (`.pf/artifacts/mcp-core-codex-capture-verification-20260822/live-capture-verification.md`) shows accepted raw events: `SessionStart`, `UserPromptSubmit`, `SessionEnd`, but `pf.session_chat` is empty.
  - Impact: `SessionStart` can be accepted in raw form but `UserPromptSubmit` processed before session presence is materialized in Ledger, so user prompt is dropped as `session_not_authorized`.

- **Verified pass for session identity/lifecycle:** `events-validate` is PASS, and MCP `pf.session_context`/`pf.session_activity` return the expected session/project identity and lifecycle facts.

## Recommendation

- Add ordering protection so `UserPromptSubmit`/final assistant captures are either:
  - delayed until session presence exists, or
  - queued and replayed after successful `agent.session.started`/`agent.session.resumed` handling.
- Keep async hook delivery if needed for latency, but enforce ordering on capture side.

## Supporting artifact status

- Evidence file reviewed and aligns with code path behavior: conversation capture misses in real Codex execution, while ledger and MCP reads remain consistent.