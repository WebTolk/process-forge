# Release Review Report

Result: pass

## Scope

Reviewed only the assignment-granted files. No files were edited. Tests were not rerun in this read-only worker context; test substantiation is based on the recorded no-turn remediation report plus static review of the relevant code and smoke regressions.

## Findings

No release-blocking findings found.

1. Pass: no-turn `SessionEnd.last_assistant_message` primary/fallback collision is handled.

Evidence: `codex_hooks.py` still allows missing `turn_id` to become `None` for `Stop`, `SubagentStop`, and `SessionEnd` assistant messages (`tools/pf_runtime/codex_hooks.py:117-138`). Host now suppresses only `SessionEnd` assistant fallback rows when the same session already has an assistant message from the primary Codex participant or a subagent participant with matching content; when the fallback item has no `turn_id`, the check intentionally matches any existing turn in that session (`tools/pf_runtime/host.py:863-883`). The suppression runs before appending the chat row (`tools/pf_runtime/host.py:923-926`), so a `Stop` and `SessionEnd` with distinct raw identities cannot create duplicate final assistant transcript rows.

Regression coverage exists for the exact no-turn collision: no-turn `Stop` captures one assistant row, then no-turn `SessionEnd` with equivalent content returns no chat ids and leaves one transcript row (`tools/smoke_conversation_completeness.py:370-387`).

2. Pass: no-turn `SessionEnd` fallback remains usable when there is no prior primary capture.

Evidence: the fallback-only regression starts a separate session, sends no primary `Stop`/`SubagentStop`, then sends no-turn `SessionEnd.last_assistant_message` and asserts exactly one assistant transcript row (`tools/smoke_conversation_completeness.py:389-401`). This directly covers the prior condition that fallback must not be suppressed merely because `turn_id` is absent.

3. Pass: previous same-turn primary/fallback collision coverage remains present.

Evidence: the same-turn `Stop` then `SessionEnd` collision still asserts the `SessionEnd` fallback returns no chat ids and does not duplicate the already captured primary assistant message (`tools/smoke_conversation_completeness.py:351-368`).

4. Pass: prior durable pending replay finding remains fixed.

Evidence: deferred conversation flush now reads memory and durable pending state without removing entries first (`tools/pf_runtime/host.py:700-711`), processes queued captures (`tools/pf_runtime/host.py:717-724`), and removes memory/durable pending entries only after successful capture (`tools/pf_runtime/host.py:725-744`).

5. Pass: prior fixture policy finding remains fixed.

Evidence: `.pf/AGENTS.md` requires repository-local temporary directories under `.pf/tmp` (`.pf/AGENTS.md:32-33`). Both reviewed smoke scripts now create fixture roots under `.pf/tmp` and clean them in `finally` blocks (`tools/smoke_conversation_completeness.py:526-535`, `tools/smoke_runtime_ledger_hooks_mcp.py:44-48`, `tools/smoke_runtime_ledger_hooks_mcp.py:136-138`).

## Verification Evidence

Recorded in `.pf/artifacts/codex-message-capture-remediation-execution-20260822/no-turn-remediation-report.md`:

- `python -m py_compile tools/pf_runtime/host.py tools/smoke_conversation_completeness.py` -> passed.
- `python tools/smoke_conversation_completeness.py` -> passed.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` -> passed.
- `git diff --check -- tools/pf_runtime/host.py tools/smoke_conversation_completeness.py` -> passed.

## Decision

Approve release gate. The no-turn collision condition from the prior review is covered in both implementation and focused regression tests, and the fallback-without-primary path is explicitly preserved.