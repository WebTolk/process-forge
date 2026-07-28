# Заметки к первому релизу

Эти заметки описывают первую файловую линию релиза без указания номера релиза в
переиспользуемой документации.

## Добавлено

- First-run flow для workplace/project через `workplace-init`,
  `project-onboard` и `agent-start-prompt`.
- Python-first CLI launchers: `bin/pf.py` для корня дистрибутива и
  `.pf/runtime/bin/pf.py` для подключённых проектов.
- Команды создания ресурсов для reusable templates, knowledge packages и
  platform contracts.
- Path constants и authoritative package roots для переносимых resource records.
- Обновление и проверка project context snapshot, а также создание assignment
  capsule.
- Runtime driver registry, команды жизненного цикла worker-run и файловый
  process supervisor для ограниченного shell worker execution.
- Events/hooks/outbox MVP для наблюдаемой файловой delivery.
- Команды проверки release, smoke, examples, cleanup, package и archive.

## Изменено

- Публичные пользовательские команды используют Python launchers.
- `START_AGENT_HERE` в подключённых проектах использует локальный project launcher.
- Release hygiene checks отклоняют generated cache files, private paths,
  unsupported script wrappers, runtime payloads, local transcripts и stale
  example data.
- Doctor commands содержат fix hints для основных first-run и
  resource-resolution failures.

## Ограничения

- Нет claim или lease system для распределенной coordination.
- Hooks работают как наблюдение и outbox-only.
- Нет daemon, GUI, marketplace, remote sync или publish service.
- Нет live command hook execution или network webhook send.

См. [ограничения](../known-limitations.md).
