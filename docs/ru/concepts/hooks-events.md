# Hooks и события

ProcessForge разделяет native agent observations, ProcessForge events и
project-visible chat records.

```text
native agent hook/event
  -> provider adapter
  -> workplace private raw ingress
  -> normalization and project-scope validation
  -> project event, conversation record, Ledger effect, or no derived effect
```

## Terms and storage boundary

- **Raw native event** — provider payload. Raw Event Journal является private
  workplace-scoped storage в `<workplace>/runtime/agent-events/`.
- **Normalized PF event** — provider-neutral derived fact.
- **Project event** — private project record в `.pf/runtime/events/events.ndjson`;
  это не полный hook journal.
- **Chat message** — private transcript record. Сопутствующий
  `chat.message.recorded` event по умолчанию содержит только metadata.
- **Delivery attempt** — outbox work. **Operator log** — отдельный process
  artifact, а не замена event.

Raw storage использует hourly shards, deduplication indexes, quarantine records
и replay checkpoints. Он может содержать sensitive provider payloads и исключен
из release archive.

## Codex adapter and registration

`tools/pf_runtime/codex_hooks.py` — тонкий adapter. Normalized mappings включают
session lifecycle, compaction и tool facts. Каждый зарегистрированный event
принимается raw-first. `UserPromptSubmit` записывает user prompt, `Stop`
записывает `last_assistant_message`, а `SubagentStop` записывает subagent final
message, когда их Ledger session и project binding валидны.

Эта возможность не доказывает, что все Codex hooks зарегистрированы в
environment. Distribution не устанавливает host `.codex/hooks.json`. Adapter
acceptance, normalized mapping, conversation mapping и фактическая host
registration являются разными фактами. Unknown native events могут остаться
raw-only.

Generic interactive Codex assistant responses и host subagent responses
captured only where Codex предоставляет `last_assistant_message`; interim
streaming output и unavailable provider fields остаются raw-only или absent.

Используйте `tools/pf_runtime/codex_integration.py` только как explicit opt-in
для merge project-local registration. Он не доказывает, что Codex реально
загрузил или trusted hooks; проверяйте `/hooks` в целевом Codex client. См.
[Codex Session Read Layer](../../concepts/codex-session-read.md).

## Project hooks

Project outbox routing настраивается в `.pf/hooks.yaml`; это отдельно от
host-native hook registration. Проверить matching project hooks из linked
project:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

File-first runtime не требует daemon или network delivery. Optional PF Runtime
service startup и Windows autostart отделены от project outbox routing.
