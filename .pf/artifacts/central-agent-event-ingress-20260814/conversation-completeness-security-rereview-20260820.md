# Independent conversation-completeness security re-review

**Assignment:** `central-ingress-conversation-completeness-security-rereview-20260820`
**Verdict:** **FAIL**

`conversation-completeness-security-correction.md` is a sound target design, but the
actual permitted code has not implemented its required capture and transcript path.
Consequently none of the five strict resume gates is proven.  This is an assurance
verdict on the current source, not a rejection of the proposed design.

| Pause-checkpoint gate | Verdict | Exact evidence |
| --- | --- | --- |
| Exact `prompt_payload()` is raw-only | **FAIL** | `tools/codex_exec_worker.py:56-76` constructs the full payload from worker prompt, capsule and workspace-access path; `:150-152` passes a fresh `prompt_payload(...).encode("utf-8")` directly to `subprocess.run`. The file neither imports/calls Runtime Host nor emits `WorkerPromptPayloadSubmitted`; therefore no exact payload is persisted through workplace-private raw ingress. `RawIngressKernel.ingest()` does persist accepted envelopes privately (`tools/pf_runtime/raw_ingress_kernel.py:202-241`), but the worker does not submit this envelope. |
| Project transcript receives only a safe system summary | **FAIL** | No `derived_conversation_messages`, safe-summary builder, or transcript append exists in `codex_exec_worker.py`. `host.ingest_event()` reads only `envelope["derived_event"]` after raw persistence (`tools/pf_runtime/host.py:669-682`), so it has no conversation sink. The required prohibitions (capsule body, workplace-access reference, absolute/raw paths) are not enforced for automatic capture. |
| Canonical pre-exec capture and shared stable digest | **FAIL** | The real execution boundary is indeed `codex_exec_worker.py:150-152`, but payload construction is embedded in the `subprocess.run` argument. There is no named `payload_text`, `sha256` import/calculation, raw-capture call, or failure-closed check before launch (`tools/codex_exec_worker.py:6-11, 150-156`). Thus capture and execution cannot share the required digest. |
| Assistant content is expected-report-only after collectible boundary | **FAIL** | `command_worker_run_collect()` verifies the expected-report file exists (`tools/processforge.py:17837-17872`), then calls `command_task_complete` and emits metadata-only `worker.run.collected` with the report path (`:17873-17875`). It never reads the report content, builds `WorkerExpectedReportCaptured`, or sends an assistant conversation envelope to Host. No stdout/stderr-to-assistant conversion is present, but no required assistant transcript record is created either. |
| Conversation and telemetry are separately routed and idempotent | **FAIL** | Host routes only the optional normalized telemetry `derived_event` (`tools/pf_runtime/host.py:674-688`); there is no independent conversation routing or `chat_message_ids` production beyond the raw receipt default. Existing manual `append_chat_message()` creates a random `msg_<uuid>` (`tools/processforge.py:10526-10548`), so it cannot provide the prescribed deterministic re-run idempotency. Raw ingress itself has duplicate and native-conflict handling (`tools/pf_runtime/raw_ingress_kernel.py:218-221`), but that does not make the absent conversation path idempotent. |

## Required disposition

Do not create the implementation assignment on the strength of this re-review.
First implement and test the correction's bounded input/output envelopes, safe-summary
validation, deterministic transcript/event identities, and separate Host routing; then
repeat this independent review against the changed source.
