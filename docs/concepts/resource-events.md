# Resource Events

Resource Management emits events to:

```text
runtime/events/events.ndjson
```

for workplace operations, or `.pf/runtime/events/events.ndjson` for project-scoped operations.

The MVP event record includes:

- `event_id`
- `event_type`
- `occurred_at`
- `scope`
- `source.command`
- `source.actor_type`
- `target`
- `result.status`
- `result.message`

Events support future snapshot invalidation and WTAICC routing without making a runner or webhook sender mandatory.
