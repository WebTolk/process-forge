# Hooks and events

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
# Адаптер Codex Runtime

`tools/pf_runtime/codex_hooks.py` принимает только подтверждённые факты
`SessionStart`, `SessionEnd` и `PostToolUse`, нормализует их и передаёт в
существующий путь Runtime/Core. Он не исполняет команды из payload, не создаёт
task и не принимает решений по стадиям. Hook вне ProcessForge-проекта спокойно
игнорируется, поэтому наблюдение не становится точкой отказа Codex.
