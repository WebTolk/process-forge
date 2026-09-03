# Process Events

ProcessForge project events are private runtime records. They are derived facts for processes, hooks and review gates; they are not a full journal of all agent-hook activity.

Canonical project stream:

```text
.pf/runtime/events/events.ndjson
```

The envelope is defined by `schemas/event-envelope.schema.json`. A record has an event id/type, source, subject, time, correlation/causation ids, project, process, assignment, actor and data. `chat.message.recorded` contains message metadata and a content hash/reference by default, never the full raw body.

Native agent payloads first enter the private workplace Raw Event Journal at `<workplace>/runtime/agent-events/`. Provider adapters may derive normalized facts from them only after project-scope validation. The project stream can therefore be incomplete by design: a raw event may be unsupported, denied, quarantined or have no project-side effect.

See [Hooks And Events](hooks-events.md) for raw storage, provider mappings, privacy and registration limits.
