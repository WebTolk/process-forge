# Implementation Report

## Status

Blocked: implementation was not applied because the active filesystem permission profile is read-only, while this assignment requires edits to `tools/pf_runtime/host.py`, `tools/pf_runtime/codex_hooks.py`, smoke tests, and the expected report artifact.

## Scope Observed

Read scope was kept to the assignment capsule and allowed read files. No forbidden files were read or edited. No subagents were invoked.

## Confirmed Remediation Target

The accepted remediation plan requires:

- Preserve raw ingress first in `tools/pf_runtime/host.py`.
- Route derived lifecycle events before conversation capture when a native envelope includes both.
- Add deferred conversation capture for messages denied only because Ledger session presence is not established yet.
- Flush deferred messages after successful `agent.session.started` / `agent.session.resumed` routing.
- Add Codex `SessionEnd` fallback assistant capture when `last_assistant_message` is present.
- Extend smoke coverage for:
  - `UserPromptSubmit` before `SessionStart`.
  - `SessionEnd` assistant fallback.
  - idempotent duplicate delivery.

## Current Code Evidence

`tools/pf_runtime/host.py` currently calls `_conversation_messages(...)` before routing `derived_event` in `ingest_event`. This means `UserPromptSubmit` conversation capture can be denied as `session_not_authorized` before `SessionStart` has materialized Ledger presence.

`tools/pf_runtime/codex_hooks.py` currently captures assistant messages only for `Stop` and `SubagentStop`. `SessionEnd` maps to `agent.session.ended`, but does not add `derived_conversation_messages` when `last_assistant_message` is present.

`tools/smoke_conversation_completeness.py` currently covers normal ordered `SessionStart` before `UserPromptSubmit`, `Stop`, `SubagentStop`, idempotency, and worker capture. It does not yet cover out-of-order prompt/start or `SessionEnd` assistant fallback.

## Changes Not Applied

No files were modified due to read-only workspace access.

## Required Follow-Up

Rerun this assignment with repository write access. The implementation should be limited to the allowed files:

- `tools/pf_runtime/host.py`
- `tools/pf_runtime/codex_hooks.py`
- `tools/smoke_conversation_completeness.py`
- `tools/smoke_runtime_ledger_hooks_mcp.py`
- `.pf/artifacts/codex-message-capture-remediation-implementation-20260822/implementation-report.md`

Minimum verification after write access is available:

- `python tools/smoke_conversation_completeness.py`
- `python tools/smoke_runtime_ledger_hooks_mcp.py`
- `python tools/processforge.py events-validate --project-root <fixture-project>` where applicable in the smoke flow.