# Remediation Plan

## Scope and objective
Design a minimal, runtime-safe fix for Codex conversation capture ordering in `mcp-core-codex-capture-verification-20260822`, preserving durable raw event ingress and avoiding behavior changes outside `pf.session_chat` capture sequencing.

## Confirmed failure surface
- `live-capture-verification.md` and `ordering-audit.md` confirm:
  - Raw Codex ingress (`SessionStart`, `UserPromptSubmit`, `SessionEnd`) is accepted.
  - Ledger lifecycle (`pf.session_context`, `pf.session_activity`) is populated.
  - `pf.session_chat` is empty (user prompt and final assistant message missing).
- `host.py` captures derived conversation messages **before** derived-event routing in `ingest_event`.
- `_conversation_messages` requires active ledger session for `ledger_session(session_id)` authorization.
- `SessionStart`-style authorization is established only when derived session lifecycle event is ingested.
- `codex_hooks.py` contract supports assistant capture on `Stop/SubagentStop`, but the analyzed run did not emit `Stop`, so final assistant capture branch did not execute.

## Minimal remediation strategy

### 1) Reorder capture flow in `tools/pf_runtime/host.py` (`ingest_event`)
- Change ordering so derived-event routing is attempted **before** conversation capture.
- Why minimal: preserves raw durability first, keeps existing semantics, and aligns capture authorization for ordered deliveries.

### 2) Add deferred conversation capture for missing-session race
- Add a small per-session in-memory pending queue for conversation envelopes that fail only due session authorization.
- Keep raw event accepted and deduplicated behavior unchanged.
- Flush queue when `agent.session.started`/`agent.session.resumed`/`agent.session.started`-equivalent lifecycle events are successfully routed.
- Keep dedup keys unchanged for idempotency and duplicate-safe replays.

### 3) Add final-assistant fallback path in Codex adapter contract handling
- In `tools/pf_runtime/codex_hooks.py`, support fallback assistant capture on `SessionEnd` if `last_assistant_message` is present.
- Retain `Stop/SubagentStop` handling as primary; fallback is only for runs that do not emit `Stop`.
- This prevents permanent final-message gaps in mixed Codex implementations while keeping strict trust boundaries.

### 4) Add minimal regression coverage (planned, no code changes in this assignment)
- Extend `smoke_conversation_completeness.py` with:
  - Out-of-order scenario: `UserPromptSubmit` before `SessionStart` then subsequent `SessionStart` should still result in user message capture after flush.
  - Missing-`Stop` scenario: session end provides final assistant text and chat includes assistant message.
  - Existing idempotency assertions preserved (duplicate delivery produces same `chat_message_ids`).
- Keep existing `smoke_runtime_ledger_hooks_mcp.py` and `events-validate` assertions unchanged.

## Rollout sequence
1. Implement `host.py` ordering + pending-queue logic.
2. Implement `codex_hooks.py` fallback on `SessionEnd` final text.
3. Update conversation smoke tests and run `smoke_conversation_completeness.py`, `smoke_runtime_ledger_hooks_mcp.py`, `events-validate`.
4. Execute target live capture replay and assert:
   - raw raw_event acceptance unchanged,
   - `pf.session_activity` remains valid,
   - `pf.session_chat` includes both user + final assistant messages.
5. Require gate: any run with `pf.session_chat==0` for valid `UserPromptSubmit`/final assistant signals is blocked.