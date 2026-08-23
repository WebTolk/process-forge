# Context Readiness Model

Дата: 2026-08-23

## Public Shape

The snapshot/check/read-model now separates:

```yaml
readiness:
  context:
    status: fresh
  resources:
    status: fresh
  execution:
    status: blocked
    missing_capabilities: []
    blockers: []
```

Compatibility fields remain:

- `status`: `fresh`, `fresh_with_updates`, `stale`, or `broken`;
- `fresh`, `stale`, `broken`;
- `broken_refs`;
- `health.status`.

`health.status` may still be `blocked` for legacy consumers that need a compact
overall health signal. Read tools must use structured readiness fields when
they need to distinguish resource validity from execution blockers.

## MCP Tool Prerequisites

`pf.search` requires:

- valid Ledger session;
- matching project binding;
- fresh context/resource resolution;
- fresh search index;
- authorized resources.

It does not require unrelated execution capabilities such as
`filesystem.write`, browser automation, deployment, or CI.

`pf.session_context` works with execution blockers and exposes them.

`pf.resolve` resolves selected project-context resources while respecting the
Ledger project boundary.
