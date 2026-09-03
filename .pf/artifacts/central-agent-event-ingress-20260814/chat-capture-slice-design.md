# Chat Capture Slice Design

## Цель

Минимальный срез: автоматическая запись **только подтверждённого Codex user prompt content** в существующий private transcript, без новой публичной сущности и без нового CLI.

Граница среза: `Codex UserPromptSubmit -> raw-v1 append -> provider-owned chat mapping -> append_chat_message(...) -> chat.message.recorded`.

Не входит в срез:
- assistant message capture;
- tool output capture as chat body;
- Claude/Gemini adapters;
- chat replay;
- публичная команда `pf chat-capture`;
- перенос Codex mapping в Host/Core.

## Опора в текущей модели

Использовать уже существующие контракты:

- raw-first storage: `tools/pf_runtime/raw_ingress_kernel.py`
  - `NativeAgentEvent`
  - `RawIngressKernel.ingest()`
  - `raw_event_id()`
  - `deterministic_derived_key()`
- Runtime ingress: `tools/pf_runtime/host.py`
  - `ingest_event()`
  - `_ingest_derived_event()`
  - `resolve_project()`
  - `ledger_session()`
  - `state_lock()`
- Codex adapter boundary: `tools/pf_runtime/codex_hooks.py`
  - `native_envelope()`
  - `normalized_event()`
  - `dispatch()`
- chat semantics: `tools/processforge.py`
  - `append_chat_message()`
  - `chat_transcript_path()`
  - `chat.message.recorded`
  - `events-validate`

## Proposed Internal Slice

### `tools/pf_runtime/codex_hooks.py`

Add a private adapter-level function, for example:

```python
def chat_message(payload: dict[str, Any]) -> dict[str, Any] | None:
    ...
```

It must return a normalized provider-neutral chat directive only when all conditions are true:

- `hook_event_name == "UserPromptSubmit"`;
- `cwd` is present;
- `session_id` is present;
- provider payload contains a non-empty string prompt field, proposed key: `prompt`;
- content role is provider-proven as user input.

Returned directive shape:

```json
{
  "kind": "chat-message",
  "provider": "codex",
  "adapter": "codex-hooks",
  "native_event_type": "UserPromptSubmit",
  "session_id": "<session_id>",
  "participant_id": "user",
  "participant_role": "operator",
  "participant_type": "human",
  "message_role": "user",
  "content": "<prompt>",
  "turn_id": "<turn_id if provider supplies it, else raw_event_id later>",
  "source_kind": "codex_hook"
}
```

`native_envelope()` attaches this as `derived_chat_message`. Existing `derived_event` behavior remains unchanged.

If the prompt field is absent, empty, or not a string, the hook still goes through raw ingress, but no chat transcript write is attempted.

### `tools/pf_runtime/host.py`

Add a private derived-chat path inside `ingest_event()` after successful `RawIngressKernel.ingest(native)`:

1. Persist raw first.
2. If raw is not accepted, return the raw receipt unchanged.
3. Route `derived_event` exactly as today.
4. Route optional `derived_chat_message` through a new private helper, for example `_ingest_derived_chat_message(...)`.
5. Add produced `message_id` to `chat_message_ids` in the response.

Host remains provider-neutral: it receives a normalized chat directive and does not inspect Codex-specific payload fields.

### `tools/processforge.py`

Keep the public `chat-record` CLI unchanged.

For durable idempotency, extend `append_chat_message()` with backward-compatible optional keyword arguments:

```python
message_id: str | None = None
event_id: str | None = None
```

Default behavior stays UUID-based. Automatic chat capture passes deterministic IDs.

If a supplied `message_id` already exists in the session transcript, `append_chat_message()` must not append a duplicate transcript line. It should reuse the existing transcript record and emit/ensure the deterministic `chat.message.recorded` event with the supplied `event_id`; `append_process_event()` already deduplicates by event id.

## Durable Identity

Use the raw receipt as the durable source identity.

For Codex user prompt chat capture:

```text
derived_key = deterministic_derived_key(
  raw_event_id,
  "chat_message",
  "processforge.chat-capture.codex-user-prompt",
  "1",
  {
    "provider": "codex",
    "adapter": "codex-hooks",
    "native_event_type": "UserPromptSubmit",
    "source_session_id": session_id,
    "message_role": "user"
  }
)
```

Then derive:

- `message_id = "msg_" + derived_key[:32]`
- `event_id = "evt_" + sha256("chat.message.recorded:" + message_id)[:32]`

This gives stable retry behavior without adding a public entity.

## Authorization

Before transcript write:

- `source_project_ref` from the raw envelope must resolve through `resolve_project()`.
- A `derived_chat_message` project/cwd, if present, must resolve to the same project.
- `session_id` is required.
- `ledger_session(session_id, workplace_root, core)` must exist and its `project_id` must match the resolved project.
- If the session is missing or bound to another project, raw remains accepted, chat capture is denied, and no transcript write occurs.

No active assignment/process/stage should be inferred for this minimal slice. Fill `process_id`, `stage_id`, and `assignment_id_value` only if a later provider contract proves those fields.

## Privacy And Retention

- Raw payload remains private under workplace runtime raw-v1 storage.
- Transcript content is private under `.pf/runtime/chat/transcripts/<session-id>.ndjson`.
- `append_chat_message()` applies existing redaction before storage.
- `chat.message.recorded` must stay `metadata_only` for automatic capture: include `content_hash`, `redaction`, and `content_ref`, not message content.
- No network send is added. Existing hook outbox receives only the existing metadata event behavior.
- Retention follows existing `.pf/runtime` private-state policy; this slice adds no public artifact containing prompt text.

## Replay Relation

Current `tools/pf_runtime/session_replay.py` repairs normalized project events only and explicitly does not replay chat messages. This slice must not change that.

A later chat replay slice can use the raw records where:

- `provider == "codex"`;
- `adapter == "codex-hooks"`;
- `native_event_type == "UserPromptSubmit"`;
- `source_session_id == session_id`.

Until then, a raw-accepted/chat-denied or raw-accepted/chat-failed case is intentionally recoverable from raw storage but not automatically repaired by session replay.

## Failure And Fallback

- Non-PF project: hook returns ignored, as today.
- Runtime unavailable: `codex_hooks.dispatch()` keeps existing fallback to `host.ingest_event()`.
- Unsupported Codex hook or missing prompt: raw accepted, no chat derived effect.
- Session/project authorization failure: raw accepted, chat denied, no transcript write.
- Duplicate raw event: deterministic `message_id` prevents duplicate transcript lines.
- Transcript/event write failure after raw append: report diagnostics in the returned receipt; raw remains the audit source.
- Hook process must still return success to Codex; observation must not break the user session.

## Focused Smoke Acceptance

1. `UserPromptSubmit` with `prompt`, `cwd`, and routed `session_id` writes one raw record, one transcript line, and one `chat.message.recorded`.
2. The emitted event is `metadata_only` and contains `content_hash`, `redaction`, and `content_ref`, not raw content.
3. Re-sending the same native payload does not append a second transcript line.
4. Missing or non-string `prompt` persists raw only and leaves `chat_message_ids` empty.
5. Session bound to another project persists raw only and denies chat capture.
6. Runtime transport failure still succeeds through the existing ledger fallback path.
7. Static smoke confirms no new argparse subcommand and no public Runtime API route.
8. Existing `events-validate` passes for the generated event and transcript.
