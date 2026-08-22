# Final Review Report

Result: pass_with_conditions

## Scope

Reviewed only the assigned files. No code or artifact files were edited. Tests were not rerun in this read-only worker context; verification below is based on static review plus the remediation report's recorded test results.

## Findings

1. Pass with condition: `SessionEnd.last_assistant_message` is fallback-only for the covered same-turn collision path.

Evidence: `codex_hooks.py` still derives assistant messages for `Stop`, `SubagentStop`, and `SessionEnd` from `last_assistant_message` (`tools/pf_runtime/codex_hooks.py:117-138`), but Host now suppresses a `SessionEnd` assistant row when an existing `codex` assistant message has the same session, turn, and content (`tools/pf_runtime/host.py:863-883`) before append (`tools/pf_runtime/host.py:922-925`). The smoke now covers `Stop` followed by `SessionEnd` with identical content and asserts no second chat row (`tools/smoke_conversation_completeness.py:351-367`).

Condition: this suppression depends on a non-empty `turn_id` (`tools/pf_runtime/host.py:869-872`). `codex_hooks.py` allows `turn_id` to become `None` when absent (`tools/pf_runtime/codex_hooks.py:127`), and append falls back to `raw_event_id` as the turn id (`tools/pf_runtime/host.py:936`, `tools/pf_runtime/host.py:952`). Since raw identity includes native event type and payload hash (`tools/pf_runtime/raw_ingress_kernel.py:340-354`), a `Stop` and `SessionEnd` pair without `turn_id` can still produce distinct chat IDs. Full approval should either prove native `Stop`/`SessionEnd` always carry `turn_id` or add no-turn duplicate suppression and regression coverage.

2. Pass: pending conversation replay no longer deletes durable state before capture.

Evidence: `_flush_deferred_conversation` now reads memory and durable pending state without popping it first (`tools/pf_runtime/host.py:700-711`), processes queued captures through `_conversation_messages` (`tools/pf_runtime/host.py:717-724`), and only removes memory/durable entries in the `succeeded` cleanup block (`tools/pf_runtime/host.py:725-744`). If capture reports a denial reason, the raw id is not added to `succeeded` (`tools/pf_runtime/host.py:720-724`).

3. Pass: smoke fixture roots comply with `.pf/tmp` policy.

Evidence: `.pf/AGENTS.md` requires repository-local temporary directories under `.pf/tmp` (`.pf/AGENTS.md:32-33`). Both reviewed smoke scripts now create run roots under `ROOT / ".pf" / "tmp"` and remove them in `finally` blocks (`tools/smoke_conversation_completeness.py:493-502`, `tools/smoke_runtime_ledger_hooks_mcp.py:44-48`, `tools/smoke_runtime_ledger_hooks_mcp.py:137-138`).

4. Pass: worker-run report capture is represented and guarded in Host and smoke coverage.

Evidence: Host accepts `WorkerExpectedReportCaptured` only with `pf_owned_output_file` provenance, a native event id derived from the report hash, and matching report content (`tools/pf_runtime/host.py:824-830`). Authorization also requires the expected report file to exist and match `raw_payload.report_content` (`tools/pf_runtime/host.py:856-859`). The conversation completeness smoke writes the expected report, calls `worker-run collect`, and asserts exactly one assistant chat message with the exact report content (`tools/smoke_conversation_completeness.py:472-485`).

## Decision

The original remediation failures are addressed for the tested nominal paths. I would not mark this as full `pass` until the no-`turn_id` primary/fallback collision is either ruled out by contract or covered in code and tests.