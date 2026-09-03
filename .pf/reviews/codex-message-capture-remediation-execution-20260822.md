# Review Report

Result: fail

## Findings

1. Fail: `SessionEnd` fallback is not actually fallback-only and can duplicate the final assistant message.

The remediation plan requires `Stop/SubagentStop` to remain primary and `SessionEnd.last_assistant_message` to be used only for runs that do not emit `Stop` (`.pf/artifacts/mcp-core-codex-capture-verification-20260822/remediation-plan.md:28-31`). The implementation attaches an assistant conversation message for every `SessionEnd` that has `last_assistant_message` (`tools/pf_runtime/codex_hooks.py:117-118`) and explicitly trusts that provenance in Host (`tools/pf_runtime/host.py:784-789`).

Idempotency does not collapse a `Stop` message and a `SessionEnd` message with the same session, turn, and content, because the chat key includes `raw_event_id` (`tools/pf_runtime/host.py:880-895`), and raw identity includes native event type plus payload hash (`tools/pf_runtime/raw_ingress_kernel.py:340-355`). So if both hooks carry the same final assistant text, two separate chat messages are recorded.

Coverage misses this case: the smoke captures `Stop` for one session and `SessionEnd` fallback for a different session, but does not test `Stop` plus `SessionEnd.last_assistant_message` for the same session/turn/content (`tools/smoke_conversation_completeness.py:319-349`).

2. Fail: deferred pending captures are removed from durable state before successful replay.

`_flush_deferred_conversation` pops the durable pending queue and saves state before any queued message is appended (`tools/pf_runtime/host.py:700-706`), then processes the queued items afterward (`tools/pf_runtime/host.py:716-725`). If capture fails or the process exits between those points, the pending prompt is no longer pending and there is no recovery scan from raw ingress. This weakens the persistence guarantee claimed in the implementation report (`.pf/artifacts/codex-message-capture-remediation-execution-20260822/implementation-report.md:12-15`).

3. Warn: test fixtures violate ProcessForge temporary-directory policy.

`.pf/AGENTS.md` requires repository-local temporary directories under `.pf/tmp/` and forbids root scratch directories (`.pf/AGENTS.md:32-33`). Both smoke scripts create root-level `.tmp` fixture trees (`tools/smoke_conversation_completeness.py:475-478`, `tools/smoke_runtime_ledger_hooks_mcp.py:45-48`). The implementation report explicitly describes this as the chosen fixture root (`.pf/artifacts/codex-message-capture-remediation-execution-20260822/implementation-report.md:28-30`), so this is a ProcessForge policy compliance issue.

## Test Adequacy

The reported checks cover the main happy path and some duplicate delivery (`.pf/artifacts/codex-message-capture-remediation-execution-20260822/implementation-report.md:32-37`), but they do not cover the primary/fallback collision above. The remediation plan also calls for a target live capture replay asserting raw acceptance, activity validity, and user plus final assistant chat capture (`.pf/artifacts/mcp-core-codex-capture-verification-20260822/remediation-plan.md:40-47`); that replay is not listed in the verification report.

## Recommendation

Do not approve as-is. Gate remediation on:

- making `SessionEnd.last_assistant_message` fallback suppress or dedupe against prior `Stop/SubagentStop` final assistant capture for the same session/turn/content;
- removing pending captures only after successful idempotent append, or leaving them durable and harmless to replay;
- moving repo-local smoke fixtures under `.pf/tmp/`;
- adding regression coverage for `Stop` followed by `SessionEnd.last_assistant_message` with identical final assistant content.