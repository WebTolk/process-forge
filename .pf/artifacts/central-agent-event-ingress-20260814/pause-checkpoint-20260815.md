# Pause checkpoint: Central Agent Event Ingress

**Captured:** 2026-08-15

## Confirmed delivered source slices

- Provider-neutral raw-first ingress kernel is present and wired through Runtime/fallback and the Codex adapter boundary.
- Session-scoped Codex raw replay is present, has failure-path smoke coverage, and is registered as `smoke_central_event_replay` in `release-test`.
- Last accepted checks for the replay registration: `py_compile`, selected `release-test`, `git diff --check`, task-doctor, and `events-validate` all passed.

## Conversation design state

The governing direction is now explicit:

- actual conversation content is a private, ordered transcript stream;
- telemetry (lifecycle, tools, permissions, heartbeat, process status and exit facts) stays in its separate raw/normalized event stream;
- a telemetry fact must never be converted into a fabricated assistant response.

Existing reports retained for resume:

- `chat-capture-slice-design.md`: early prompt-only slice; superseded as insufficient for the complete-conversation requirement.
- `assistant-response-capture-design.md`: proves generic Codex hooks do not currently expose assistant message bodies; PF-owned worker final output is a separate trusted source.
- `conversation-telemetry-boundary-design.md`: defines `derived_conversation_messages[]` separate from `derived_event` telemetry.
- `conversation-completeness-correction.md`: adds PF-owned input/output concept, but is not accepted because it proposed putting the full stdin launch payload into a project transcript.
- `conversation-completeness-security-review.md`: FAIL; confirms the leak risk and the incorrect input-capture boundary.
- `conversation-completeness-security-correction.md`: PASS as a planning correction. It keeps exact launch input only in workplace-private raw ingress, emits a sanitised system summary to the project transcript, captures input at the real `codex_exec_worker.py` boundary, and captures assistant output only after a collectible expected report exists.

## Strict resume gate

Do not create an implementation assignment until an independent review of `conversation-completeness-security-correction.md` passes. The review must prove all of the following:

1. Exact `prompt_payload()` remains only in workplace-private raw storage.
2. Project transcript summary contains no capsule body, workspace-access reference, raw-storage path, or absolute path.
3. The input capture is tied to the payload builder immediately before `codex exec`, with a stable digest shared by the capture and execution path.
4. Assistant content comes only from the PF-owned expected-report/output contract after the collectible boundary, never stdout/stderr or lifecycle telemetry.
5. Conversation and telemetry remain independently routed and idempotent.

After that PASS, create a narrow Spark test contract, then one tightly scoped high-reasoning implementation assignment, followed by independent review and release-test registration/acceptance.

## Paused worker state

The following planning/review workers wrote durable reports but were intentionally stopped for this pause; their assignments remain `open` for explicit resumption rather than being falsely marked accepted:

- `central-ingress-chat-capture-slice-design-20260815`
- `central-ingress-assistant-response-capture-design-20260815`
- `central-ingress-conversation-telemetry-boundary-20260815`
- `central-ingress-conversation-completeness-correction-20260815`
- `central-ingress-conversation-completeness-security-review-20260815`
- `central-ingress-conversation-completeness-security-correction-20260815`

The installed detached-worker supervisor can leave a completed worker shown as `running`; this pause used explicit `worker-run stop` after durable-output inspection. Treat the task artifacts and this checkpoint as authoritative for resumption.

## Delivery boundary

No package/archive was created during this checkpoint. The worktree has pre-existing unrelated changes, so the clean-worktree packaging guard remains intentionally unsatisfied.
