# Implementation Report

## Status

Completed.

## Changes Implemented

- `tools/pf_runtime/host.py`
  - Preserved raw ingress as the first durable operation.
  - Reordered accepted raw-event handling so normalized lifecycle routing runs before conversation capture.
  - Added deferred conversation capture for non-worker `session_not_authorized` cases caused by missing Ledger presence.
  - Stored pending captures in private Runtime host state so CLI/runtime process boundaries do not lose pre-start prompts.
  - Deduplicated pending captures by raw event id and reused the existing deterministic conversation-message keys.
  - Flushed pending captures after successful `agent.session.started` or `agent.session.resumed` routing.
  - Added a narrow pre-route Ledger snapshot for `agent.session.ended`/`agent.session.stopped` conversation fallback, so checkout can still route before capture while authorizing the final assistant message.
  - Kept worker authorization failures fail-closed and excluded end/stop lifecycle failures from the start/resume pending queue.

- `tools/pf_runtime/codex_hooks.py`
  - Added conditional `SessionEnd` assistant fallback only when `last_assistant_message` is present, non-empty, and a session id is available.
  - Left `Stop` and `SubagentStop` as the primary assistant capture paths.

- `tools/smoke_conversation_completeness.py`
  - Added regression coverage for `UserPromptSubmit` arriving before `SessionStart`, including duplicate delivery and flush on start.
  - Added regression coverage for missing-`Stop` final assistant capture through `SessionEnd.last_assistant_message`.
  - Preserved existing privacy, provenance, worker capture, duplicate, and `events-validate` checks.

- `tools/smoke_runtime_ledger_hooks_mcp.py`
  - Kept behavior assertions unchanged.
  - Switched the fixture root from `tempfile.TemporaryDirectory()` to the repo-local `.tmp` pattern used by the conversation smoke, because the sandboxed Windows subprocess could not create the workplace under the temporary directory ACL.

## Verification

- `python -m py_compile tools/pf_runtime/host.py tools/pf_runtime/codex_hooks.py tools/smoke_conversation_completeness.py tools/smoke_runtime_ledger_hooks_mcp.py` -> passed.
- `python tools/smoke_conversation_completeness.py` -> passed.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` -> passed.
- `git diff --check -- tools/pf_runtime/host.py tools/pf_runtime/codex_hooks.py tools/smoke_conversation_completeness.py tools/smoke_runtime_ledger_hooks_mcp.py` -> passed.

## Notes

- No subagents were used.
- The implementation stayed within the assigned write scope.
- `smoke_runtime_ledger_hooks_mcp.py` initially failed before product logic with Windows `PermissionError` while creating a temporary workplace. After moving that fixture to repo-local `.tmp`, the smoke passed.