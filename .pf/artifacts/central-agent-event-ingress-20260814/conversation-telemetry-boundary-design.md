# Conversation Telemetry Boundary Design

## Статус

Плановый дизайн без изменений исходного кода.

Граница требования: все реально доступные conversation messages должны проходить через hook/central ingress и становиться durable private transcript records. Operational telemetry должна сохраняться и маршрутизироваться отдельно; она не должна превращаться в chat message.

## Локально подтверждённая текущая модель

Подтверждено по разрешённым источникам:

- `tools/pf_runtime/codex_hooks.py` сейчас строит Codex native envelope и нормализует только `SessionStart`, `SessionEnd`, `PostToolUse`.
- `codex_hooks.dispatch()` доставляет envelope в Runtime `/event`, а при недоступности Runtime использует `host.ingest_event()` fallback.
- `tools/pf_runtime/host.py` уже реализует raw-first путь: native envelope -> `NativeAgentEvent` -> `RawIngressKernel.ingest(...)` -> optional `derived_event`.
- `RawIngressKernel` пишет private raw records в workplace runtime storage, выдаёт `raw_event_id`, поддерживает dedup, stable native identity conflict detection и quarantine.
- `host._raw_receipt_payload(...)` уже имеет поля `normalized_event_ids` и `chat_message_ids`, хотя derived chat sink пока не реализован.
- `tools/processforge.py` уже имеет private transcript: `.pf/runtime/chat/transcripts/<session-id>.ndjson`, `append_chat_message(...)`, `chat.message.recorded`, metadata-only export/event mode и `events-validate`.
- `append_process_event(...)` дедуплицирует durable events по `event_id`.
- `tools/codex_exec_worker.py` запускает PF-owned worker через `codex exec -o <output> -`; prompt contract прямо говорит, что final response captured verbatim as expected report artifact. Heartbeat, exit code и process status являются lifecycle facts, не assistant content.

## Доказанная Codex граница и gaps

Текущий PF Codex adapter:

- implemented: `SessionStart`, `SessionEnd`, `PostToolUse`;
- not implemented locally: `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `PreToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `Stop`;
- chat capture отсутствует;
- assistant response capture через generic Codex hooks не подтверждён.

По ранее зафиксированной матрице provider contract у Codex есть `UserPromptSubmit`, поэтому user prompt capture можно проектировать только если hook payload содержит реальное prompt поле. Generic Codex assistant response capture остаётся `unsupported`, пока нет provider-proven assistant message body. PF-owned `codex_exec_worker` является отдельным источником: assistant answer можно брать из expected report/output file после completed worker run, потому что этот output создаётся самим PF worker contract.

## Provider-Neutral Envelope Contract

Central ingress принимает provider-neutral native envelope:

```json
{
  "schema_version": 1,
  "provider": "codex|processforge|claude|gemini|...",
  "adapter": "<adapter-id>",
  "native_event_type": "<provider event type>",
  "native_event_id": "<stable provider id or null>",
  "native_id_scope": "provider|adapter|session|project",
  "native_event_id_stable": true,
  "source_session_id": "<session id or null>",
  "source_project_ref": "<project ref>",
  "payload_version": "<adapter payload version>",
  "raw_payload": {},
  "derived_event": {},
  "derived_conversation_messages": []
}
```

Routing rule:

- `raw_payload` is always persisted first by `RawIngressKernel`.
- `derived_event` is operational telemetry and goes only to normalized event routing.
- `derived_conversation_messages[]` is conversation content and goes only to private transcript routing.
- A lifecycle/status/tool/permission/heartbeat/exit event must never be represented as a chat message unless provider/PF supplies actual conversation text and role provenance.

## Conversation Message Contract

Each item in `derived_conversation_messages[]` is provider-neutral:

```json
{
  "schema_version": 1,
  "message_role": "user|assistant|system|tool|subagent",
  "participant": {
    "id": "<stable participant id>",
    "type": "human|agent|subagent|tool|system",
    "role": "operator|assistant|worker|tool|system"
  },
  "session_id": "<session id>",
  "turn_id": "<provider turn id or derived id>",
  "parent_message_id": "<optional>",
  "content": "<provider/PF proven text>",
  "content_source": {
    "kind": "codex_hook|pf_codex_exec_output|provider_message_event",
    "provider": "<provider>",
    "adapter": "<adapter>",
    "native_event_type": "<native event type>",
    "content_provenance": "provider_payload|pf_owned_output_file"
  },
  "delivery": {
    "state": "complete|partial",
    "sequence": 0,
    "final": true
  }
}
```

Required message acceptance:

- `content` must be a non-empty string after adapter validation.
- `message_role` must be proven by provider/PF contract, not inferred from telemetry event type.
- `session_id` is required.
- `source_project_ref` must resolve to the project.
- `ledger_session(session_id, workplace_root, core)` must exist and match project id, except first session-start telemetry, which is not chat anyway.
- Optional project/cwd inside message content source must resolve to the same project as the raw envelope.

Denied conversation message routing must not reject raw ingress. It returns diagnostics and leaves `chat_message_ids` empty for the denied item.

## Operational Telemetry Contract

Operational telemetry remains in normalized event routing:

- session lifecycle: `agent.session.started|resumed|compacted|ended`;
- tool lifecycle: `agent.command.completed|agent.tool.completed`;
- worker lifecycle: heartbeat, exit contract, process started/completed;
- permission/status/compact/subagent lifecycle where supported later.

Telemetry can reference message ids after transcript write, but it must not contain chat body. Automatic `chat.message.recorded` must remain metadata-only: `content_hash`, `redaction`, `content_ref`, `content_mode`, participant, session, message id.

## Source-Specific Routing

### Codex `UserPromptSubmit`

Adapter may emit one user message only when:

- `hook_event_name == "UserPromptSubmit"`;
- `cwd` and `session_id` are present;
- payload contains a non-empty string prompt field;
- provider contract proves the field is user input.

Missing/non-string prompt: raw accepted, no transcript write, diagnostic `chat_unsupported_or_missing_content`.

### Generic Codex assistant response

Unsupported for now. `SessionEnd`, `PostToolUse`, tool output, exit code, heartbeat, or task status must not be used to fabricate assistant text.

### PF-owned Codex worker output

After worker completion and expected report/output file existence, PF may create a `provider: processforge`, `adapter: pf-codex-exec-worker`, `native_event_type: WorkerExpectedReportCaptured` envelope. The derived assistant message content comes from the expected report/output file. Stdout/stderr remain process logs, not semantic assistant body by default.

### Tool, system, subagent messages

Capture only when provider/PF supplies actual conversation text with role provenance. Tool execution metadata, subagent lifecycle, permission checks, and compact events stay telemetry. If a provider later exposes tool/subagent conversation text, it uses the same `derived_conversation_messages[]` contract.

## Identity, Ordering, and Retries

Raw identity remains the durable source identity:

- use `RawIngressKernel.raw_event_id`;
- use stable native identity only for conflict detection when provider supplies stable ids;
- unstable providers use raw payload hash plus session/project scope as currently implemented.

Derived message id:

```text
derived_key = deterministic_derived_key(
  raw_event_id,
  "conversation_message",
  "processforge.conversation-capture.<adapter>",
  "1",
  {
    "provider": provider,
    "adapter": adapter,
    "native_event_type": native_event_type,
    "source_session_id": session_id,
    "message_role": message_role,
    "turn_id": turn_id,
    "delivery_sequence": sequence
  }
)

message_id = "msg_" + derived_key[:32]
event_id = "evt_" + sha256("chat.message.recorded:" + message_id)[:32]
```

For PF-owned worker expected report, identity may be based on run/task/output fingerprint when no raw provider event exists yet:

```text
sha256({
  "contract": "processforge.worker-output-chat-message.v1",
  "run_id": run_id,
  "task_id": task_id,
  "expected_report_path": expected_report_path,
  "expected_report_sha256": file_sha256,
  "message_role": "assistant"
})
```

Ordering:

- transcript records keep `timestamp`, `turn_id`, provider sequence if available, and raw receipt location.
- if provider ordering is absent, ingestion order is the only ordering guarantee.
- duplicate delivery must not append a second transcript line when deterministic `message_id` already exists.
- partial chunks are recorded as conversation content only when provider marks them as message content; final complete message should use stable identity semantics so replay/retry does not duplicate.

## Privacy

- Raw provider payload stays private under workplace runtime raw storage.
- Transcript body stays private under `.pf/runtime/chat/transcripts/`.
- Public artifacts, assignment capsules, and reports must not receive raw provider payload or private workplace paths.
- `chat.message.recorded` for automatic capture is metadata-only by default.
- No new network send is introduced.
- Existing outbox behavior receives metadata events only unless a later explicit opt-in export requests content.

## Migration Compatibility

Implementation should be additive:

- keep current `derived_event` behavior unchanged;
- add optional `derived_conversation_messages[]`; support legacy single `derived_chat_message` only as an internal compatibility alias if needed;
- extend `append_chat_message()` with optional `message_id` and `event_id`, preserving UUID defaults for manual `chat-record`;
- existing manual transcript records remain valid;
- no new public CLI is required;
- no provider-specific parsing moves into Host/Core;
- `events-validate` remains the validation gate for runtime events and transcripts.

## Failure Semantics

- Non-PF project: hook ignored as today.
- Runtime unavailable: adapter fallback to `host.ingest_event()` remains.
- Raw accepted, derived event fails: raw receipt remains audit source; diagnostics should expose routing failure.
- Raw accepted, message denied: no transcript line; diagnostics explain authorization/content reason.
- Native id payload conflict or raw hash collision: quarantine, no derived routing.
- Hook process still exits success; observation must not break the user session.

## Focused Acceptance

1. `SessionStart`, `SessionEnd`, `PostToolUse` continue to create only telemetry events, not chat messages.
2. Codex `UserPromptSubmit` with prompt, cwd, and routed session writes one raw record, one transcript line, and one metadata-only `chat.message.recorded`.
3. Re-delivering the same native payload does not create a second transcript line.
4. Missing or non-string prompt writes raw only and returns empty `chat_message_ids`.
5. Session bound to another project writes raw only and denies transcript routing.
6. Generic Codex assistant response remains unsupported unless real assistant body is present in provider payload.
7. PF-owned Codex worker completed expected report can create one assistant transcript record from the output file, not from heartbeat/exit/status/stdout.
8. Tool/subagent/system records are captured only when actual conversation text is available and role-proven.
9. `chat.message.recorded` automatic event contains `content_hash`, `redaction`, `content_ref`, `content_mode=metadata_only`, and no message body.
10. Static check confirms no new public chat capture CLI and no provider-specific Codex fields in Host/Core.
11. `events-validate` passes for generated runtime events and transcripts.
