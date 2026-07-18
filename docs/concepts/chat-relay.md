# Chat Relay

Chat relay records session conversation content in private runtime files and can
prepare metadata-only outbox payloads for future managed consumers.

Canonical transcript path:

```text
.pf/runtime/chat/transcripts/<session-id>.ndjson
```

Each line is one `schemas/chat-message.schema.json` object. Participants can be
human operators, orchestrator agents, regular agents, subagents, or tools.

## Recording

```bash
python bin/pf.py chat-record --project-root <project-root> --session-id session-demo --participant operator --role user --content "Start"
```

`chat-record` writes the transcript line and emits `chat.message.recorded`.

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
