# Codex message capture remediation: integration report

## Outcome

Accepted after a failed first review, a bounded remediation pass, and a final release-gate review.

## Delivered behavior

- Native raw ingress remains the first durable operation.
- Lifecycle routing establishes Ledger session presence before conversation capture.
- A user prompt received before `SessionStart` is durably deferred and flushed after start or resume; it is removed only after successful idempotent capture.
- `SessionEnd.last_assistant_message` is a conditional fallback. It does not duplicate an equivalent `Stop` or `SubagentStop` capture, including when `turn_id` is absent; a no-turn fallback without a prior primary capture remains recorded.
- Expected shell-worker reports are again collected as exactly one Ledger-bound assistant transcript message.
- Runtime smoke fixtures use `.pf/tmp` and clean their per-run roots.

## Worker quality gates

1. `codex-capture-remediation-implementation-retry-20260822` implemented the first slice. Its first independent review failed on fallback duplication, non-atomic deferred cleanup, and fixture placement.
2. `codex-capture-remediation-fix-review-20260822` remediated those findings. Real `worker-run-collect` then completed successfully.
3. `codex-capture-remediation-final-review-20260822` returned `pass_with_conditions` for the no-turn collision.
4. `codex-capture-remediation-no-turn-fix-20260822` added both no-turn regression cases.
5. `codex-capture-remediation-release-review-20260822` returned `pass`.

The initial `gpt-5.3-codex-spark` reviewer could not run because its quota was exhausted. It produced no report and was retried independently with `gpt-5.5`.

## Verification performed by the orchestrator

- `python tools/smoke_conversation_completeness.py` — passed after the remediation and again after the no-turn refinement.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` — passed after the remediation and again after the no-turn refinement.
- Real `python tools/processforge.py worker-run-collect` — passed for the remediation, no-turn fix, and release-review reports.
- Task doctor passed for every completed task; run doctor passed.
- `git diff --check` passed.

## Boundaries and residual notes

- The project-local `codex-exec-workspace-write` driver was used only for implementation workers. It grants `workspace-write`, not unrestricted access.
- The standard built-in `codex-exec` profile remains read-only and was used for reviewers.
- No commit or push was requested. Existing unrelated worktree changes were preserved.
