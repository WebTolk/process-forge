# No-Turn Remediation Report

## Status

Completed.

## Changes

- Updated `tools/pf_runtime/host.py` so `SessionEnd` assistant fallback duplicate suppression no longer depends on a non-empty `turn_id`.
- For `SessionEnd` fallback messages, Host now suppresses capture when the same session already has an assistant message with matching content from the primary Codex participant or a subagent participant.
- Preserved the fallback path when there is no existing primary assistant capture: a no-turn `SessionEnd.last_assistant_message` still appends the final assistant message.
- Added focused regressions in `tools/smoke_conversation_completeness.py` for:
  - no-turn `Stop` followed by no-turn `SessionEnd` with equivalent content, expecting no duplicate chat row;
  - no-turn `SessionEnd` without a prior primary capture, expecting one assistant chat row.

## Verification

- `python -m py_compile tools/pf_runtime/host.py tools/smoke_conversation_completeness.py` -> passed.
- `python tools/smoke_conversation_completeness.py` -> passed.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` -> passed.
- `git diff --check -- tools/pf_runtime/host.py tools/smoke_conversation_completeness.py` -> passed.

## Scope Notes

- Edited only allowed files:
  - `tools/pf_runtime/host.py`
  - `tools/smoke_conversation_completeness.py`
  - `.pf/artifacts/codex-message-capture-remediation-execution-20260822/no-turn-remediation-report.md`
- Did not edit forbidden files.
- Did not invoke subagents.
- The working tree already contained earlier remediation changes in the same allowed files; this pass was limited to the final-review no-turn condition and its regression coverage.