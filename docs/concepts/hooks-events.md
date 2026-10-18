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

`tools/pf_runtime/codex_hooks.py` is a thin adapter. Its normalized mappings include session lifecycle, compaction and tool facts. Every registered event is accepted raw-first. `UserPromptSubmit` records the user prompt, `Stop` and `SessionEnd` record a supplied `last_assistant_message`, and `SubagentStop` records the supplied subagent final message when their Ledger session and project binding are valid.

This capability is not proof that every Codex hook is registered in an environment. The distribution does not install a host `.codex/hooks.json`. Adapter acceptance, normalized mapping, conversation mapping and actual host registration are separate facts. Unknown native events can remain raw-only.

Generic interactive Codex assistant responses and host subagent responses are captured only where Codex provides `last_assistant_message`; interim streaming output and unavailable provider fields remain raw-only or absent.

Use `tools/pf_runtime/codex_integration.py` only as an explicit opt-in to merge
project-local registration. It does not prove Codex actually loaded or trusted
the hooks; inspect `/hooks` in the target Codex client. See
[Codex Session Read Layer](codex-session-read.md).

## Project hooks

Project outbox routing is configured in `.pf/hooks.yaml`; it is distinct from host-native hook registration. Test project hook matching from a linked project:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

The file-first runtime does not require a daemon or network delivery. Optional
PF Runtime service startup and Windows autostart are separate from project
outbox routing.
