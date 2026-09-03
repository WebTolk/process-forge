# Conversation Completeness Correction

## Статус

Плановая корректировка двух существующих дизайнов без изменения исходного кода.

Корректировка требования: всё фактическое correspondence-содержимое, которое PF или provider технически получает или отправляет как часть agent conversation, должно проходить через central ingress и становиться ordered durable private conversation records. Operational telemetry остаётся отдельным потоком и не превращается в conversation message.

## Главная правка

Существующие дизайны правильно запрещают фабрикацию assistant body из lifecycle/telemetry, но неполно закрывают PF-owned input side перед запуском `codex_exec_worker`.

Для PF-owned Codex worker нужно фиксировать не только assistant output из expected report после завершения, но и входное сообщение до запуска worker process. При этом полный generated launch payload нельзя классифицировать как human `user` message.

Правильная классификация:

- `pf_codex_exec_input` -> `message_role: system`, participant `processforge-runtime`, `participant.type: system`, `participant.role: worker_launcher`;
- `pf_codex_exec_output` -> `message_role: assistant`, participant текущего worker/agent, `participant.type: agent`, `participant.role: worker`;
- generic Codex `UserPromptSubmit` -> `message_role: user` только когда provider contract доказывает, что payload field является реальным user prompt;
- lifecycle/status/tool/heartbeat/exit/session events -> telemetry only.

## Canonical Message Sources

### 1. Generic Codex Hook User Input

Canonical source: Codex hook `UserPromptSubmit`.

Accept as conversation message only if:

- `hook_event_name == "UserPromptSubmit"`;
- `cwd` / project ref resolves to the project;
- `session_id` is present and routed to the same project;
- payload contains a non-empty string prompt field;
- provider contract proves the field is user input.

Role: `user`.

If prompt is missing, non-string, or role provenance is not proven: raw ingress accepted, no transcript write, diagnostic `conversation_unsupported_or_missing_content`.

### 2. Generic Codex Assistant Response

Unsupported for now.

Do not derive assistant text from:

- `SessionStart`;
- `SessionEnd`;
- `PostToolUse`;
- `Stop`;
- heartbeat;
- exit contract;
- task status;
- stdout/stderr;
- tool output metadata.

Generic Codex assistant capture becomes supported only when a provider-stable event/payload supplies actual assistant message body with role provenance.

### 3. PF-Owned Codex Worker Input

Canonical source: `tools/codex_exec_worker.py` launch input created by PF from `prompt_payload(worker_prompt, capsule, workspace_access)` and sent to `codex exec ... -`.

This must be captured before worker process execution through central ingress as:

- `provider: processforge`;
- `adapter: pf-codex-exec-worker`;
- `native_event_type: WorkerPromptPayloadSubmitted`;
- `message_role: system`;
- `content_source.kind: pf_codex_exec_input`;
- `content_source.content_provenance: pf_owned_stdin_payload`.

This record represents PF runtime instructions to a worker, not the human user’s message. The full generated capsule/system/assignment instructions must not be labeled `user`.

### 4. PF-Owned Codex Worker Output

Canonical source: expected report/output file after completed worker run.

Capture only when:

- worker run status is completed/collectible;
- expected report artifact exists;
- content is read from the expected report/output file;
- source is PF-owned output contract, not process logs.

Role: `assistant`.

Use:

- `provider: processforge`;
- `adapter: pf-codex-exec-worker`;
- `native_event_type: WorkerExpectedReportCaptured`;
- `content_source.kind: pf_codex_exec_output`;
- `content_source.content_provenance: pf_owned_output_file`.

## Corrected Envelope

Central ingress should accept this provider-neutral shape:

```json
{
  "schema_version": 1,
  "provider": "codex|processforge|...",
  "adapter": "<adapter-id>",
  "native_event_type": "<native event type>",
  "native_event_id": "<stable id or null>",
  "native_id_scope": "provider|adapter|session|project",
  "native_event_id_stable": true,
  "source_session_id": "<conversation/session id>",
  "source_project_ref": "<project ref>",
  "payload_version": "1",
  "raw_payload": {},
  "derived_event": {},
  "derived_conversation_messages": []
}
```

Rules:

- `raw_payload` is always private and persisted first by `RawIngressKernel`.
- `derived_event` is telemetry and routes only to normalized events.
- `derived_conversation_messages[]` is conversation content and routes only to private transcript.
- A telemetry event may reference message ids after transcript write, but must not carry message body by default.

## Conversation Message Contract

```json
{
  "schema_version": 1,
  "message_role": "user|assistant|system|tool|subagent",
  "participant": {
    "id": "<stable participant id>",
    "type": "human|agent|subagent|tool|system",
    "role": "<operator|assistant|worker|tool|system|worker_launcher>"
  },
  "session_id": "<session/conversation id>",
  "turn_id": "<turn id>",
  "parent_message_id": "<optional>",
  "content": "<provider/PF proven text>",
  "content_source": {
    "kind": "codex_hook|pf_codex_exec_input|pf_codex_exec_output|provider_message_event",
    "provider": "<provider>",
    "adapter": "<adapter>",
    "native_event_type": "<native event type>",
    "content_provenance": "provider_payload|pf_owned_stdin_payload|pf_owned_output_file"
  },
  "delivery": {
    "state": "complete|partial",
    "sequence": 0,
    "final": true
  }
}
```

## Pairing, Ordering, And Identity

For PF-owned Codex worker, use a deterministic private conversation id:

```text
session_id = pf-worker:<run_id>:<task_id>:attempt:<attempt>
turn_id = worker-turn:<run_id>:<task_id>:attempt:<attempt>
```

Ordering:

- input record: `delivery.sequence = 0`, `message_role = system`, before subprocess start;
- output record: `delivery.sequence = 1`, `message_role = assistant`, after expected report exists;
- output `parent_message_id` points to input `message_id`;
- telemetry events remain separately ordered in event journal.

Dedup identity:

```text
derived_key = deterministic_derived_key(
  raw_event_id,
  "conversation_message",
  "processforge.conversation-capture.<adapter>",
  "1",
  {
    "session_id": session_id,
    "turn_id": turn_id,
    "message_role": message_role,
    "delivery_sequence": sequence,
    "content_hash": content_hash
  }
)

message_id = "msg_" + derived_key[:32]
event_id = "evt_" + sha256("chat.message.recorded:" + message_id)[:32]
```

Duplicate delivery must not append a second transcript line when `message_id` already exists. `append_process_event()` can continue deduplicating `chat.message.recorded` by deterministic `event_id`.

## Privacy Boundary

- Raw provider/PF payload stays private in workplace runtime raw ingress storage.
- Conversation body stays private in `.pf/runtime/chat/transcripts/<session-id>.ndjson`.
- Automatic `chat.message.recorded` remains metadata-only: `content_hash`, `redaction`, `content_ref`, `content_mode=metadata_only`, participant, session, message id.
- Public artifacts, assignment capsules, reports, and hook outbox payloads must not receive raw provider payload or private workplace paths.
- `workspace_access_file` contents and private absolute paths must not leak into public project artifacts.
- No new network send is introduced.

## Revised First Implementation Slice

1. Extend `append_chat_message()` with optional deterministic `message_id`, `event_id`, richer `source`, and duplicate lookup by `message_id`. Preserve current UUID behavior for manual `chat-record`.

2. Add Host/Core conversation sink for `derived_conversation_messages[]` after raw ingress succeeds. Host must stay provider-neutral: validate project/session/content contract, call transcript append, return `chat_message_ids` and diagnostics.

3. Add PF-owned worker input capture before `subprocess.Popen` in worker run start path. It must create a `WorkerPromptPayloadSubmitted` native envelope and route it through central ingress as `message_role: system`.

4. Add PF-owned worker output capture during successful collect path after expected report existence is confirmed. It must create a `WorkerExpectedReportCaptured` native envelope and route it through central ingress as `message_role: assistant`.

5. Add Codex `UserPromptSubmit` adapter mapping only for provider-proven prompt text. Keep generic assistant response marked unsupported.

## Focused Acceptance

1. PF-owned Codex worker start creates one private system transcript record for the exact PF-owned stdin prompt payload before execution.

2. That input record is not labeled `user` and is not treated as human-authored content.

3. Completed PF-owned Codex worker collect creates one assistant transcript record from expected report/output file.

4. Re-running the same capture does not duplicate transcript lines or `chat.message.recorded` events.

5. `SessionStart`, `SessionEnd`, `PostToolUse`, heartbeat, exit contract, task status, stdout, and stderr never create assistant messages.

6. Codex `UserPromptSubmit` with valid prompt, cwd, and routed session creates raw record, user transcript record, and metadata-only `chat.message.recorded`.

7. Missing/non-string prompt creates raw record only and returns empty `chat_message_ids`.

8. Session bound to another project creates raw record only, denies transcript write, and reports diagnostics.

9. Automatic `chat.message.recorded` contains no message body unless an explicit manual/export opt-in already allows it.

10. `events-validate` passes for generated raw-derived events and transcript records.
