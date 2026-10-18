# Chat Relay

Chat relay records session conversation content in private runtime files and can
prepare metadata-only outbox payloads for future managed consumers.

Canonical transcript path:

```text
.pf/runtime/chat/transcripts/session-<identity-digest>.ndjson
```

New filenames use an opaque session identity digest; readers also accept legacy
session-named files and verify each record's exact session. This NDJSON stream
is independent of the [SQLite project journals](hook-journal-sqlite.md).

Each line is one `schemas/chat-message.schema.json` object. Participants can be
human operators, orchestrator agents, regular agents, subagents, or tools.

## Recording

```bash
python bin/pf.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start"
```

`chat-record` writes the transcript line and emits `chat.message.recorded`.

Automatic capture is deliberately narrower than the generic transcript model:
the current Codex adapter records `UserPromptSubmit` user prompts and the
`last_assistant_message` supplied by `Stop`, `SubagentStop` or `SessionEnd`,
subject to valid project/session binding and enabled hook collection. PF-owned
codex-exec worker input summaries and collectible expected reports use explicit
provenance checks. Host hook registration and available provider fields limit
capture: interim streaming output and a complete conversation are not guaranteed.
See [hooks and events](hooks-events.md).

By default, the emitted event contains:

- message id
- participant metadata
- role
- `content_hash`
- redaction state
- local `content_ref`

It does not include full content unless `--include-content` is passed.

## Export

```bash
python bin/pf.py chat-export --project-root <project-root> --session-id session-demo --target wtaicc --outbox
```

`chat-export` writes a file-only payload under:

```text
.pf/runtime/hooks/outbox/wtaicc/
```

Default export mode is `metadata_only`. Full redacted content requires
`--include-content`.

## Privacy

Chat relay redacts secret-like values, stores runtime transcripts under ignored
`.pf/runtime/`, and keeps network delivery disabled in the MVP.

Raw provider payloads are stored separately in the private project Raw Hook
Journal. A project event/outbox payload must not contain a full raw body.

Recommended assignment-level options:

```yaml
chat_capture:
  enabled: false
  include_content: false
  max_message_chars: 20000
  redact_patterns:
    - secret_like
    - api_key_like
    - password_like
  allow_private_paths: false
  send_to_outbox: true
```
