# Hooks And Webhooks

The project dispatcher reads enabled targets from `.pf/hooks.yaml` and matches
their `event_types` against the event name or `*`. The Codex handlers in
`.codex/hooks.json` feed observations into PF. Each configuration has its own
handler or target count. [Native hook setup](../guides/forge-init-hooks.md)

Default config:

```text
.pf/hooks.yaml
```

The schema is `schemas/hooks.schema.json`.

## Target Types

- `outbox` writes a local payload and a delivery result.
- An enabled `webhook` target can also produce a local payload in outbox mode.
  The project dispatcher has no network sender.
- An enabled `command` target produces a skipped result during dispatch.
  Dry-run lists matching targets of each type.

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

Each event and exact target ID has its own delivery key. The CLI prints the
payload and receipt paths. The receipt records the target, event ID and
`payload_sha256` of the published file. A retry uses the first complete
payload, including its timestamp. If receipt publication was interrupted,
journal replay finishes the receipt from those same bytes. Admission stores
the selected targets and their routes with the pending event. Changing a route
or disabling a target affects subsequent events. The pending event finishes
its original deliveries before acknowledgement. For an older event-only
pending row, restore its hook configuration before the first replay.
Runtime tick reports deliveries it could not finish in the project's
`dispatch_failures`, with the event ID and reason. These events stay pending.
The tick processes the rest of its batch, and successive ticks revisit
pending events in bounded batches.

Older ordinary deliveries can retain their paths when the original envelope
identifies the event and exact target. If publication stopped before the old
receipt was written, replay completes that receipt from the original file.
If the old receipt is truncated or belongs to a different target with the
same normalized name, the exact target gets its own receipt for the original
bytes. Its `payload_delivery_id` identifies the historical envelope and
`payload_sha256` verifies the file at `outbox`. Historical WTAICC envelopes
contain only the shared integration name. Replay preserves those files and
writes a separately identified delivery for the configured target.

## Dry Run And Outbox

Use dry-run to see which targets would match:

```bash
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type session.ended --dry-run
```

Use outbox mode to write payloads without network send:

```bash
python bin/pf.py hooks-dispatch --project-root <project-root> --event-type assignment.completed --outbox
```

`--send` is reserved for a future transport and fails in the MVP.
