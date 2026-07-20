# Process Events

ProcessForge events are private runtime records by default. They describe flow
facts that processes, hooks, review gates, and future managed consumers can
observe without making a backend mandatory.

Canonical stream:

```text
.pf/runtime/events/events.ndjson
```

Each line is a JSON event envelope with:

- `event_id`
- `event_type`
- `source`
- `subject`
- `time`
- `correlation_id`
- `causation_id`
- `project`
- `process`
- `assignment`
- `actor`
- `data`

The schema is `schemas/event-envelope.schema.json`. The process taxonomy is
described by `schemas/process-event.schema.json`.

Common event categories include:

- `session.started`
- `session.ended`
- `session.message.recorded`
- `chat.message.recorded`
- `process.started`
- `process.completed`
- `stage.started`
- `stage.completed`
- `assignment.created`
- `assignment.started`
- `assignment.completed`
- `artifact.created`
- `artifact.updated`
- `review.requested`
- `review.completed`
- `gate.passed`
- `gate.failed`
- `tool.invoked`
- `tool.failed`
- `mcp.invoked`
- `mcp.failed`
- `hook.dispatched`
- `hook.failed`
- `context.snapshot.refreshed`
- `context.snapshot.stale`
- `capability.missing`

This is a readable core subset, not the complete enum. The code-level source of
truth for the current accepted event types is `REQUIRED_PROCESSFORGE_EVENT_TYPES`
in `tools/processforge.py`; event envelope structure is validated by
`schemas/event-envelope.schema.json`.

Process definitions declare the events they require or subscribe to. Runtime hook
delivery is configured separately in `.pf/hooks.yaml`.

Events must not contain raw secrets. Chat events are metadata-only by default and
carry `content_hash` plus a local `content_ref` unless content capture is
explicitly enabled.
