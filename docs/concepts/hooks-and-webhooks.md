# Hooks And Webhooks

Hooks deliver ProcessForge events without requiring a backend or network send.
The process definition declares which events matter; `.pf/hooks.yaml` declares
where matching events are delivered.

Default config:

```text
.pf/hooks.yaml
```

The schema is `schemas/hooks.schema.json`.

## Target Types

- `outbox`: writes a delivery payload under `.pf/runtime/hooks/outbox/`.
- `webhook`: reserved for future network delivery and disabled by default.
- `command`: declared for future local command execution and disabled unless a
  runner explicitly supports it.

Inline credentials are not allowed in hook config. Webhooks use `url_ref` and
`secret_ref` only.

## Runtime Files

WTAICC-bound outbox payloads are written to:

```text
.pf/runtime/hooks/outbox/wtaicc/
```

Hook delivery results are written to:

```text
.pf/runtime/hooks/results/
```

Both paths are private runtime state and ignored by git.

## Dry Run And Outbox

Use dry-run to see which targets would match:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Use outbox mode to write payloads without network send:

```bash
python tools/processforge.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

`--send` is reserved for a future transport and fails in the MVP.
