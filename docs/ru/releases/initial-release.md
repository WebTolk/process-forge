# Initial release notes

Эти заметки описывают первую file-first release line без указания номера релиза
в переиспользуемой документации.

## Добавлено

- First-run flow для workplace/project через `workplace-init`,
  `project-onboard` и `agent-start-prompt`.
- Python-first CLI launchers: `bin/pf.py` для distribution root и
  `.pf/runtime/bin/pf.py` для linked projects.
- Resource authoring commands для reusable templates, knowledge packages и
  platform contracts.
- Path constants и authoritative package roots для переносимых resource records.
- Project context snapshot refresh/check и assignment capsule generation.
- Runtime driver registry, worker-run lifecycle commands и file-first process
  supervisor для ограниченного shell worker execution.
- Events/hooks/outbox MVP для file-only observational delivery.
- Release, smoke, examples, cleanup, package и archive validation commands.

## Изменено

- Public user commands используют Python launchers.
- `START_AGENT_HERE` в linked projects использует локальный project launcher.
- Release hygiene checks отклоняют generated cache files, private paths,
  unsupported script wrappers, runtime payloads, local transcripts и stale
  example data.
- Doctor commands содержат fix hints для основных first-run и
  resource-resolution failures.

## Ограничения

- Нет claim или lease system для распределенной coordination.
- Hooks observational и outbox-only.
- Нет daemon, GUI, marketplace, remote sync или publish service.
- Нет live command hook execution или network webhook send.

См. [ограничения](../known-limitations.md).
