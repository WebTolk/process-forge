# Hooks And Events

ProcessForge separates native agent observations from ProcessForge events and from project-visible chat records.

```text
native agent hook/event
  -> provider adapter
  -> project private raw ingress
  -> normalization and project-scope validation
  -> project event, conversation record, Ledger effect, or no derived effect
```

## Terms and storage boundary

- A **raw native event** is the provider payload. Its receipt and optional private history live in `.pf/runtime/agent-events/hooks.sqlite3` in the validated project.
- A **normalized PF event** is a provider-neutral derived fact.
- A **project event** is a private project record in `.pf/runtime/events/events.sqlite3`; it is not the complete hook journal.
- A **chat message** is a private transcript record. Its accompanying `chat.message.recorded` event is metadata-only by default.
- A **delivery attempt** is outbox work. An **operator log** is a separate process artifact, not an event substitute.

Raw storage uses transactional SQLite receipts, optional payload rows, quarantine
and pending recovery state. Replay checkpoints also remain project-local. It may
contain sensitive provider payloads and is excluded from the release archive.
The two inherited PFConfig logging flags control raw and normalized history
independently. See [SQLite journals and migration](hook-journal-sqlite.md).

## Codex adapter and registration

The Codex adapter maps supported lifecycle, compaction and tool events. With
collection enabled and a valid binding, `UserPromptSubmit` can record a user
message. `Stop`, `SessionEnd` and `SubagentStop` can record a supplied final
message. Payload history follows `logging.raw_hooks`. Conversation coverage
depends on the fields delivered by the host.

On a workplace with an `organized` default, project initialization prepares
eight handlers in `.codex/hooks.json`. In Garage an operator can merge them
with `tools/pf_runtime/codex_integration.py`. Check `/hooks` in the target
Codex client for activation. [Hook setup](../guides/forge-init-hooks.md) ·
[Session reads](session-reads.md)

## Project hooks

The dispatcher selects enabled `.pf/hooks.yaml` targets by event type or
wildcard. A dry-run lists matches without writing delivery payloads. In outbox
mode a matching webhook can produce a local file, and a command target is
reported as skipped. [Project hook dispatch](hooks-and-webhooks.md)

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

The file-first runtime does not require a daemon or network delivery. Optional
PF Runtime service startup and Windows autostart are separate from project
outbox routing.
