# Hooks And Events

ProcessForge записывает события в проектные runtime files. Hooks сопоставляют
события с правилами доставки и могут создавать outbox payloads.

Events:

```text
.pf/runtime/events/events.ndjson
```

Hook configuration:

```text
.pf/hooks.yaml
```

Проверить matching:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

Создать outbox payload:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --outbox
```

File-first runtime ProcessForge пишет локальные файлы. Сетевая доставка не
входит в core runtime.
